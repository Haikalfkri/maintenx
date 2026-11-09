import uuid

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Catatan kejadian penting: siapa melakukan apa pada entitas mana."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.PROTECT, related_name="audit_logs"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,  # kosong untuk kejadian sistem (misalnya task Celery)
        related_name="audit_logs",
    )
    action = models.CharField(max_length=60)  # contoh: "equipment.retired"
    entity_type = models.CharField(max_length=80)
    entity_id = models.CharField(max_length=64)
    metadata = models.JSONField(default=dict, blank=True)  # jangan isi password/token
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "entity_type", "entity_id", "-created_at"]),
            models.Index(fields=["organization", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.action} {self.entity_type}:{self.entity_id}"