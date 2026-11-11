from django.db import transaction
from rest_framework.exceptions import ValidationError

from accounts.models import Organization
from core.roles import Role

from .models import (
    WorkOrder,
    WorkOrderHistory,
    WorkOrderPriority,
    WorkOrderStatus,
)


def next_work_order_number(organization) -> str:
    """
    Nomor berikutnya untuk organisasi: WO-00001, WO-00002, ...

    WAJIB dipanggil di dalam transaction.atomic(). Baris organisasi dikunci
    (select_for_update), sehingga dua proses bersamaan tidak pernah mendapat
    nomor yang sama. Jika transaksi dibatalkan, kenaikan nomor ikut dibatalkan
    sehingga tidak ada nomor yang 'bolong'.
    """
    locked = Organization.objects.select_for_update().get(pk=organization.pk)
    locked.work_order_sequence += 1
    locked.save(update_fields=["work_order_sequence"])
    return f"WO-{locked.work_order_sequence:05d}"


def create_work_order(
    *,
    organization,
    actor,
    equipment,
    title,
    work_order_type,
    description="",
    priority=WorkOrderPriority.MEDIUM,
    due_date=None,
    assigned_technician=None,
    maintenance_plan=None,
    metadata=None,
):
    """
    Satu-satunya jalur pembuatan work order (dipakai API di Phase 4 dan penjadwal).
    `actor=None` berarti dibuat oleh sistem.
    """
    if equipment.organization_id != organization.pk:
        raise ValidationError({"equipment": ["Equipment does not belong to this organization."]})
    if equipment.is_retired:
        raise ValidationError({"equipment": ["Retired equipment cannot receive new work orders."]})
    if maintenance_plan is not None and maintenance_plan.organization_id != organization.pk:
        raise ValidationError({"maintenance_plan": ["Plan does not belong to this organization."]})
    if assigned_technician is not None and not (
        assigned_technician.organization_id == organization.pk
        and assigned_technician.is_active
        and assigned_technician.role == Role.TECHNICIAN
    ):
        raise ValidationError(
            {"assigned_technician": ["Must be an active technician in this organization."]}
        )

    status = WorkOrderStatus.ASSIGNED if assigned_technician else WorkOrderStatus.OPEN

    with transaction.atomic():
        work_order = WorkOrder.objects.create(
            organization=organization,
            work_order_number=next_work_order_number(organization),
            equipment=equipment,
            maintenance_plan=maintenance_plan,
            title=title,
            description=description,
            work_order_type=work_order_type,
            priority=priority,
            status=status,
            assigned_technician=assigned_technician,
            reported_by=actor,
            due_date=due_date,
        )
        WorkOrderHistory.objects.create(
            organization=organization,
            work_order=work_order,
            actor=actor,
            event_type="CREATED",
            to_status=status,
            metadata=metadata or {},
        )
    return work_order