import uuid

from django.conf import settings
from django.db import models
from django.db.models import F, Q


class Frequency(models.TextChoices):
    DAILY = "DAILY", "Daily"
    WEEKLY = "WEEKLY", "Weekly"
    MONTHLY = "MONTHLY", "Monthly"


class MaintenancePlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.PROTECT, related_name="maintenance_plans"
    )
    equipment = models.ForeignKey(
        "equipment.Equipment", on_delete=models.PROTECT, related_name="maintenance_plans"
    )
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    frequency = models.CharField(max_length=16, choices=Frequency.choices)
    interval_value = models.PositiveIntegerField(default=1)
    # Tanggal acuan jadwal. Semua tanggal jatuh tempo dihitung dari sini.
    start_date = models.DateField()
    # Diatur server (dihitung dari jadwal), bukan oleh klien
    next_due_date = models.DateField()
    estimated_duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    default_technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="default_maintenance_plans",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["next_due_date", "title"]
        constraints = [
            models.CheckConstraint(
                condition=Q(interval_value__gte=1), name="plan_interval_at_least_one"
            ),
            models.CheckConstraint(
                condition=Q(next_due_date__gte=F("start_date")),
                name="plan_next_due_not_before_start",
            ),
        ]
        indexes = [models.Index(fields=["organization", "is_active", "next_due_date"])]

    def __str__(self):
        return self.title


class MaintenanceOccurrence(models.Model):
    """
    Satu kejadian jadwal (plan + tanggal jatuh tempo) yang sudah dibuatkan work order.

    Constraint unik (maintenance_plan, scheduled_due_date) adalah jaminan terakhir
    bahwa satu jadwal tidak pernah menghasilkan work order ganda, walau task
    dijalankan bersamaan atau diulang.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.PROTECT, related_name="maintenance_occurrences"
    )
    maintenance_plan = models.ForeignKey(
        MaintenancePlan, on_delete=models.PROTECT, related_name="occurrences"
    )
    scheduled_due_date = models.DateField()
    generated_work_order = models.OneToOneField(
        "workorders.WorkOrder", on_delete=models.PROTECT, related_name="occurrence"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-scheduled_due_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["maintenance_plan", "scheduled_due_date"],
                name="uniq_occurrence_per_plan_and_due_date",
            ),
        ]

    def __str__(self):
        return f"{self.maintenance_plan_id} @ {self.scheduled_due_date}"