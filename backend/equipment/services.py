from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from core.audit import record_audit
from core.exceptions import ConflictError

from .models import Equipment, EquipmentStatus

TRACKED_FIELDS = (
    "equipment_code",
    "name",
    "description",
    "category_id",
    "manufacturer",
    "model_number",
    "serial_number",
    "location",
    "purchase_date",
    "installation_date",
    "status",
)

DUPLICATE_CODE_ERROR = {"equipment_code": ["An equipment item with this code already exists."]}


def _json_safe(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)  # UUID dan date menjadi string


def _snapshot(equipment):
    return {field: _json_safe(getattr(equipment, field)) for field in TRACKED_FIELDS}


def create_equipment(*, organization, actor, data):
    try:
        with transaction.atomic():
            equipment = Equipment.objects.create(organization=organization, **data)
            record_audit(
                organization=organization,
                actor=actor,
                action="equipment.created",
                entity=equipment,
                metadata={"equipment_code": equipment.equipment_code, "name": equipment.name},
            )
    except IntegrityError:
        # Dua request bersamaan dengan kode yang sama: constraint database yang menang
        raise ValidationError(DUPLICATE_CODE_ERROR)
    return equipment


def update_equipment(*, equipment, actor, data):
    try:
        with transaction.atomic():
            locked = Equipment.objects.select_for_update().get(pk=equipment.pk)
            if locked.is_retired:
                raise ConflictError("Retired equipment cannot be modified.")

            before = _snapshot(locked)
            for field, value in data.items():
                setattr(locked, field, value)
            locked.save()
            after = _snapshot(locked)

            changes = {
                field: {"from": before[field], "to": after[field]}
                for field in TRACKED_FIELDS
                if before[field] != after[field]
            }
            if changes:
                record_audit(
                    organization=locked.organization,
                    actor=actor,
                    action="equipment.updated",
                    entity=locked,
                    metadata={"changes": changes},
                )
    except IntegrityError:
        raise ValidationError(DUPLICATE_CODE_ERROR)
    return locked


def retire_equipment(*, equipment, actor):
    with transaction.atomic():
        locked = Equipment.objects.select_for_update().get(pk=equipment.pk)
        if locked.is_retired:
            raise ConflictError("Equipment is already retired.")

        previous_status = locked.status
        locked.status = EquipmentStatus.RETIRED
        locked.retired_at = timezone.now()
        locked.save(update_fields=["status", "retired_at", "updated_at"])
        record_audit(
            organization=locked.organization,
            actor=actor,
            action="equipment.retired",
            entity=locked,
            metadata={"from_status": previous_status},
        )
    return locked