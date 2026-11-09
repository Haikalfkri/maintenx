from rest_framework import serializers

from core.models import AuditLog
from core.serializers import OrganizationScopedRelatedField

from .models import Equipment, EquipmentCategory, EquipmentStatus


class EquipmentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipmentCategory
        fields = ("id", "name", "description", "created_at")
        read_only_fields = ("id", "created_at")

    def validate_name(self, value):
        value = value.strip()
        organization = self.context["request"].user.organization
        duplicates = EquipmentCategory.objects.filter(organization=organization, name__iexact=value)
        if self.instance is not None:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError("A category with this name already exists.")
        return value


class EquipmentSerializer(serializers.ModelSerializer):
    category = OrganizationScopedRelatedField(
        queryset=EquipmentCategory.objects.all(), required=False, allow_null=True
    )
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)

    class Meta:
        model = Equipment
        fields = (
            "id",
            "equipment_code",
            "name",
            "description",
            "category",
            "category_name",
            "manufacturer",
            "model_number",
            "serial_number",
            "location",
            "purchase_date",
            "installation_date",
            "status",
            "created_at",
            "updated_at",
            "retired_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "retired_at")
        # Unik per organisasi dicek manual (organization tidak ada di field serializer)
        extra_kwargs = {"equipment_code": {"validators": []}}

    def validate_equipment_code(self, value):
        value = value.strip().upper()
        organization = self.context["request"].user.organization
        duplicates = Equipment.objects.filter(organization=organization, equipment_code=value)
        if self.instance is not None:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError(
                "An equipment item with this code already exists."
            )
        return value

    def validate_status(self, value):
        if value == EquipmentStatus.RETIRED:
            raise serializers.ValidationError("Use the retire endpoint to retire equipment.")
        return value

    def validate(self, attrs):
        purchase = attrs.get("purchase_date", getattr(self.instance, "purchase_date", None))
        installation = attrs.get(
            "installation_date", getattr(self.instance, "installation_date", None)
        )
        if purchase and installation and installation < purchase:
            raise serializers.ValidationError(
                {"installation_date": "Installation date cannot be before the purchase date."}
            )
        return attrs


class EquipmentHistorySerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = ("id", "action", "actor", "actor_name", "metadata", "created_at")
        read_only_fields = fields

    def get_actor_name(self, obj) -> str | None:
        return obj.actor.full_name if obj.actor else None