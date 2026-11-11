import uuid

from django.conf import settings
from django.db import models


class WorkOrderType(models.TextChoices):
    CORRECTIVE = "CORRECTIVE", "Corrective"
    PREVENTIVE = "PREVENTIVE", "Preventive"


class WorkOrderPriority(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    CRITICAL = "CRITICAL", "Critical"


class WorkOrderStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    ASSIGNED = "ASSIGNED", "Assigned"
    IN_PROGRESS = "IN_PROGRESS", "In progress"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


class WorkOrder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.PROTECT, related_name="work_orders"
    )
    work_order_number = models.CharField(max_length=40)
    equipment = models.ForeignKey(
        "equipment.Equipment", on_delete=models.PROTECT, related_name="work_orders"
    )
    maintenance_plan = models.ForeignKey(
        "maintenance.MaintenancePlan",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="work_orders",
    )
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    work_order_type = models.CharField(max_length=20, choices=WorkOrderType.choices)
    priority = models.CharField(
        max_length=16, choices=WorkOrderPriority.choices, default=WorkOrderPriority.MEDIUM
    )
    status = models.CharField(
        max_length=20, choices=WorkOrderStatus.choices, default=WorkOrderStatus.OPEN
    )
    assigned_technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="assigned_work_orders",
    )
    # NULL = dibuat oleh sistem (work order preventif hasil penjadwalan)
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reported_work_orders",
    )
    due_date = models.DateField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completion_notes = models.TextField(blank=True)
    actual_labor_minutes = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "work_order_number"],
                name="uniq_work_order_number_per_organization",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "assigned_technician", "status"]),
            models.Index(fields=["organization", "created_at"]),
        ]

    def __str__(self):
        return f"{self.work_order_number} - {self.title}"


class WorkOrderHistory(models.Model):
    """Timeline kejadian sebuah work order (dibuat, ditugaskan, dimulai, selesai, ...)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.PROTECT, related_name="work_order_history"
    )
    work_order = models.ForeignKey(
        WorkOrder, on_delete=models.PROTECT, related_name="history"
    )
    # NULL = kejadian oleh sistem (misalnya task Celery)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="work_order_events",
    )
    event_type = models.CharField(max_length=40)
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20, blank=True)
    note = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name_plural = "work order history"
        indexes = [models.Index(fields=["work_order", "created_at"])]

    def __str__(self):
        return f"{self.work_order_id} {self.event_type}"