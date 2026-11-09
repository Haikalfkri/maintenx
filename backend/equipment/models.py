import uuid

from django.db import models
from django.db.models import Q


class EquipmentStatus(models.TextChoices):
    OPERATIONAL = "OPERATIONAL", "Operational"
    UNDER_MAINTENANCE = "UNDER_MAINTENANCE", "Under maintenance"
    OUT_OF_SERVICE = "OUT_OF_SERVICE", "Out of service"
    RETIRED = "RETIRED", "Retired"


class EquipmentCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.PROTECT,
        related_name="equipment_categories",
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "equipment categories"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"], name="uniq_category_name_per_organization"
            ),
        ]

    def __str__(self):
        return self.name


class Equipment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.PROTECT, related_name="equipment"
    )
    category = models.ForeignKey(
        EquipmentCategory,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="equipment",
    )
    equipment_code = models.CharField(max_length=50)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    manufacturer = models.CharField(max_length=120, blank=True)
    model_number = models.CharField(max_length=120, blank=True)
    serial_number = models.CharField(max_length=120, blank=True)
    location = models.CharField(max_length=160)
    purchase_date = models.DateField(null=True, blank=True)
    installation_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=32, choices=EquipmentStatus.choices, default=EquipmentStatus.OPERATIONAL
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    retired_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["equipment_code"]
        verbose_name_plural = "equipment"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "equipment_code"],
                name="uniq_equipment_code_per_organization",
            ),
            # Equipment berstatus RETIRED wajib punya waktu retired_at
            models.CheckConstraint(
                condition=~Q(status="RETIRED") | Q(retired_at__isnull=False),
                name="retired_equipment_has_retired_at",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "location"]),
        ]

    def __str__(self):
        return f"{self.equipment_code} - {self.name}"

    @property
    def is_retired(self):
        return self.status == EquipmentStatus.RETIRED