from .models import AuditLog

def record_audit(*, organization, actor, action, entity, metadata=None):
    """Catat satu kejadian audit. Panggil di dalam transaction.atomic() yang sama dengan perubahannya."""
    return AuditLog.objects.create(
        organization=organization,
        actor=actor,
        action=action,
        entity_type=entity._meta.model_name,
        entity_id=str(entity.pk),
        metadata=metadata or {},
    )