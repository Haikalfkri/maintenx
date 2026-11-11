import logging
from dataclasses import dataclass
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from core.audit import record_audit
from core.dates import organization_today
from core.exceptions import ConflictError
from equipment.models import EquipmentStatus
from workorders.models import WorkOrderPriority, WorkOrderType
from workorders.services import create_work_order

from .models import MaintenanceOccurrence, MaintenancePlan
from .recurrence import first_due_date, next_due_date_after

logger = logging.getLogger(__name__)

# Field yang boleh diubah setelah plan dibuat. Equipment dan start_date sengaja tidak
# ada: start_date adalah anchor jadwal, dan equipment tidak boleh berpindah.
UPDATABLE_FIELDS = (
    "title",
    "description",
    "frequency",
    "interval_value",
    "estimated_duration_minutes",
    "default_technician",
)


def _check_equipment_usable(organization, equipment):
    if equipment.organization_id != organization.pk:
        raise ValidationError({"equipment": ["Equipment does not belong to this organization."]})
    if equipment.is_retired:
        raise ValidationError({"equipment": ["Retired equipment cannot have maintenance plans."]})


# --------------------------------------------------------------------------- plan CRUD

def create_plan(*, organization, actor, data):
    _check_equipment_usable(organization, data["equipment"])
    today = organization_today(organization)
    next_due = first_due_date(
        data["start_date"], data["frequency"], data.get("interval_value", 1), today
    )
    with transaction.atomic():
        plan = MaintenancePlan.objects.create(
            organization=organization, next_due_date=next_due, **data
        )
        record_audit(
            organization=organization,
            actor=actor,
            action="maintenance_plan.created",
            entity=plan,
            metadata={
                "title": plan.title,
                "equipment_code": plan.equipment.equipment_code,
                "frequency": plan.frequency,
                "next_due_date": str(plan.next_due_date),
            },
        )
    return plan


def update_plan(*, plan, actor, data):
    data = {field: value for field, value in data.items() if field in UPDATABLE_FIELDS}
    with transaction.atomic():
        locked = MaintenancePlan.objects.select_for_update().get(pk=plan.pk)
        before = {f: _plain(getattr(locked, f)) for f in UPDATABLE_FIELDS}
        for field, value in data.items():
            setattr(locked, field, value)
        locked.save()
        after = {f: _plain(getattr(locked, f)) for f in UPDATABLE_FIELDS}
        changes = {
            f: {"from": before[f], "to": after[f]} for f in UPDATABLE_FIELDS if before[f] != after[f]
        }
        if changes:
            record_audit(
                organization=locked.organization,
                actor=actor,
                action="maintenance_plan.updated",
                entity=locked,
                metadata={"changes": changes},
            )
    return locked


def _plain(value):
    """Nilai yang aman disimpan di JSON audit (objek relasi menjadi ID-nya)."""
    return str(value.pk) if hasattr(value, "pk") else (value if value is None or isinstance(value, (str, int, float, bool)) else str(value))


def deactivate_plan(*, plan, actor):
    with transaction.atomic():
        locked = MaintenancePlan.objects.select_for_update().get(pk=plan.pk)
        if not locked.is_active:
            raise ConflictError("Plan is already inactive.")
        locked.is_active = False
        locked.save(update_fields=["is_active", "updated_at"])
        record_audit(
            organization=locked.organization,
            actor=actor,
            action="maintenance_plan.deactivated",
            entity=locked,
        )
    return locked


def activate_plan(*, plan, actor):
    """Aktifkan kembali. Jatuh tempo yang sudah lewat tidak dikejar: dihitung ulang ke depan."""
    with transaction.atomic():
        locked = MaintenancePlan.objects.select_for_update().select_related("organization").get(pk=plan.pk)
        if locked.is_active:
            raise ConflictError("Plan is already active.")
        _check_equipment_usable(locked.organization, locked.equipment)
        today = organization_today(locked.organization)
        if locked.next_due_date < today:
            locked.next_due_date = first_due_date(
                locked.start_date, locked.frequency, locked.interval_value, today
            )
        locked.is_active = True
        locked.save(update_fields=["is_active", "next_due_date", "updated_at"])
        record_audit(
            organization=locked.organization,
            actor=actor,
            action="maintenance_plan.activated",
            entity=locked,
            metadata={"next_due_date": str(locked.next_due_date)},
        )
    return locked


def advance_plan_after_completion(*, plan, scheduled_due_date, today=None) -> bool:
    """
    Majukan next_due_date setelah work order preventif SELESAI (atau DIBATALKAN).
    Akan dipanggil oleh WorkOrderService di Phase 4.

    Aman dipanggil berulang (idempotent): jika next_due_date plan sudah bukan
    `scheduled_due_date`, berarti jadwal itu sudah dimajukan, dan tidak ada yang berubah.
    """
    with transaction.atomic():
        locked = (
            MaintenancePlan.objects.select_for_update(of=("self",))
            .select_related("organization")
            .get(pk=plan.pk)
        )
        if locked.next_due_date != scheduled_due_date:
            return False
        today = today or organization_today(locked.organization)
        locked.next_due_date = next_due_date_after(
            locked.start_date, locked.frequency, locked.interval_value, scheduled_due_date, today
        )
        locked.save(update_fields=["next_due_date", "updated_at"])
        return True


# ------------------------------------------------------------------------ penjadwal

@dataclass
class GenerationResult:
    created: int = 0  # work order baru dibuat
    already_generated: int = 0  # jadwal ini sudah punya work order (idempotent)
    skipped: int = 0  # belum jatuh tempo / nonaktif / sedang dikunci proses lain
    failed: int = 0  # error tak terduga pada satu plan (plan lain tetap diproses)


def _occurrence_exists(plan, due_date) -> bool:
    return MaintenanceOccurrence.objects.filter(
        maintenance_plan=plan, scheduled_due_date=due_date
    ).exists()


def _generate_for_plan(plan_id, now) -> str:
    """Proses satu plan dalam transaksinya sendiri. Mengembalikan 'created', 'exists', atau 'skipped'."""
    with transaction.atomic():
        # Kunci baris plan. Jika proses lain sedang memprosesnya, lewati (skip_locked).
        plan = (
            MaintenancePlan.objects.select_for_update(skip_locked=True, of=("self",))
            .select_related("organization", "equipment", "default_technician")
            .filter(pk=plan_id, is_active=True, organization__is_active=True)
            .exclude(equipment__status=EquipmentStatus.RETIRED)
            .first()
        )
        if plan is None:
            return "skipped"

        today = organization_today(plan.organization, now)
        due_date = plan.next_due_date
        if due_date > today:
            return "skipped"

        if _occurrence_exists(plan, due_date):
            return "exists"

        technician = plan.default_technician
        if technician is not None and not technician.is_active:
            technician = None  # teknisi default sudah nonaktif: work order dibuat tanpa penugasan

        try:
            # Savepoint: jika constraint unik menolak, work order dan kenaikan nomornya ikut batal
            with transaction.atomic():
                work_order = create_work_order(
                    organization=plan.organization,
                    actor=None,  # dibuat oleh sistem
                    equipment=plan.equipment,
                    title=plan.title,
                    description=plan.description,
                    work_order_type=WorkOrderType.PREVENTIVE,
                    priority=WorkOrderPriority.MEDIUM,
                    due_date=due_date,
                    assigned_technician=technician,
                    maintenance_plan=plan,
                    metadata={
                        "source": "maintenance_plan",
                        "maintenance_plan_id": str(plan.pk),
                        "scheduled_due_date": str(due_date),
                    },
                )
                MaintenanceOccurrence.objects.create(
                    organization=plan.organization,
                    maintenance_plan=plan,
                    scheduled_due_date=due_date,
                    generated_work_order=work_order,
                )
        except IntegrityError:
            return "exists"

        record_audit(
            organization=plan.organization,
            actor=None,
            action="maintenance_plan.work_order_generated",
            entity=plan,
            metadata={
                "work_order_id": str(work_order.pk),
                "work_order_number": work_order.work_order_number,
                "scheduled_due_date": str(due_date),
            },
        )
        return "created"


def generate_due_work_orders(now=None) -> GenerationResult:
    """
    Buat work order preventif untuk semua plan yang sudah jatuh tempo.

    Aman dijalankan berulang dan bersamaan (idempotent):
      1. Tiap plan dikunci saat diproses.
      2. Jadwal yang sudah punya work order dilewati.
      3. Constraint unik di database menjadi jaring pengaman terakhir.
    Plan yang terlambat hanya menghasilkan SATU work order (untuk jatuh tempo saat ini),
    bukan satu per tanggal yang terlewat.
    """
    now = now or timezone.now()
    result = GenerationResult()

    # Saring kasar di database. Tanggal lokal organisasi bisa sehari lebih maju dari
    # tanggal UTC, jadi pakai batas +1 hari; pengecekan tepat dilakukan per plan.
    candidate_ids = list(
        MaintenancePlan.objects.filter(
            is_active=True,
            organization__is_active=True,
            next_due_date__lte=now.date() + timedelta(days=1),
        )
        .exclude(equipment__status=EquipmentStatus.RETIRED)
        .values_list("pk", flat=True)
    )

    for plan_id in candidate_ids:
        try:
            outcome = _generate_for_plan(plan_id, now)
        except Exception:  # satu plan bermasalah tidak boleh menghentikan yang lain
            logger.exception("Failed to generate work order for plan %s", plan_id)
            result.failed += 1
            continue

        if outcome == "created":
            result.created += 1
        elif outcome == "exists":
            result.already_generated += 1
        else:
            result.skipped += 1

    logger.info("Maintenance scheduling finished: %s", result)
    return result