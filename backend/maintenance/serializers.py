from rest_framework import serializers

from accounts.models import User
from core.dates import organization_today
from core.roles import Role
from core.serializers import OrganizationScopedRelatedField
from equipment.models import Equipment

from .models import MaintenancePlan
from .recurrence import due_status

MAX_CALENDAR_DAYS = 92


class MaintenancePlanSerializer(serializers.ModelSerializer):
    equipment = OrganizationScopedRelatedField(queryset=Equipment.objects.all())
    default_technician = OrganizationScopedRelatedField(
        queryset=User.objects.filter(role=Role.TECHNICIAN, is_active=True),
        required=False,
        allow_null=True,
    )
    equipment_code = serializers.CharField(source="equipment.equipment_code", read_only=True)
    equipment_name = serializers.CharField(source="equipment.name", read_only=True)
    equipment_status = serializers.CharField(source="equipment.status", read_only=True)
    default_technician_name = serializers.SerializerMethodField()
    due_status = serializers.SerializerMethodField()
    last_work_order = serializers.SerializerMethodField()

    class Meta:
        model = MaintenancePlan
        fields = (
            "id",
            "equipment",
            "equipment_code",
            "equipment_name",
            "equipment_status",
            "title",
            "description",
            "frequency",
            "interval_value",
            "start_date",
            "next_due_date",
            "due_status",
            "estimated_duration_minutes",
            "default_technician",
            "default_technician_name",
            "is_active",
            "last_work_order",
            "created_at",
            "updated_at",
        )
        # next_due_date dihitung server; is_active hanya lewat endpoint activate/deactivate
        read_only_fields = ("id", "next_due_date", "is_active", "created_at", "updated_at")
        extra_kwargs = {"estimated_duration_minutes": {"min_value": 1}}

    def get_default_technician_name(self, obj) -> str | None:
        return obj.default_technician.full_name if obj.default_technician else None

    def get_due_status(self, obj) -> str:
        today = self.context.get("today") or organization_today(
            self.context["request"].user.organization
        )
        return due_status(obj.next_due_date, obj.is_active, today)

    def get_last_work_order(self, obj) -> dict | None:
        # Diisi oleh annotate() di view; kosong jika plan belum pernah menghasilkan work order
        work_order_id = getattr(obj, "last_wo_id", None)
        if work_order_id is None:
            return None
        return {
            "id": work_order_id,
            "work_order_number": obj.last_wo_number,
            "status": obj.last_wo_status,
        }

    def validate_title(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def validate_interval_value(self, value):
        if value != 1:
            raise serializers.ValidationError("Only an interval of 1 is supported in this version.")
        return value

    def validate_equipment(self, value):
        if value.is_retired:
            raise serializers.ValidationError("Retired equipment cannot have maintenance plans.")
        if self.instance is not None and value != self.instance.equipment:
            raise serializers.ValidationError("Equipment cannot be changed after the plan is created.")
        return value

    def validate(self, attrs):
        if (
            self.instance is not None
            and "start_date" in attrs
            and attrs["start_date"] != self.instance.start_date
        ):
            raise serializers.ValidationError(
                {"start_date": "Start date cannot be changed after the plan is created."}
            )
        return attrs


class CalendarQuerySerializer(serializers.Serializer):
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    def validate(self, attrs):
        start, end = attrs.get("start_date"), attrs.get("end_date")
        if start and end:
            if start > end:
                raise serializers.ValidationError("start_date must not be after end_date.")
            if (end - start).days > MAX_CALENDAR_DAYS:
                raise serializers.ValidationError(
                    f"The date range cannot exceed {MAX_CALENDAR_DAYS} days."
                )
        return attrs