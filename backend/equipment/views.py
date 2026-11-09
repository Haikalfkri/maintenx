from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.mixins import OrganizationScopedMixin
from core.models import AuditLog
from core.permissions import IsAdminOrManager, IsOrganizationMember

from .filters import EquipmentFilter
from .models import Equipment, EquipmentCategory
from .serializers import (
    EquipmentCategorySerializer,
    EquipmentHistorySerializer,
    EquipmentSerializer,
)
from .services import create_equipment, retire_equipment, update_equipment

WRITE_ACTIONS = {"create", "update", "partial_update", "retire"}


class EquipmentCategoryViewSet(
    OrganizationScopedMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = EquipmentCategory.objects.all()
    serializer_class = EquipmentCategorySerializer
    http_method_names = ["get", "post", "patch", "head", "options"]
    pagination_class = None  # daftar kecil per organisasi, dipakai untuk dropdown
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_permissions(self):
        if self.action in WRITE_ACTIONS:
            return [IsAdminOrManager()]
        return [IsOrganizationMember()]

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)


class EquipmentViewSet(
    OrganizationScopedMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Equipment.objects.select_related("category")
    http_method_names = ["get", "post", "patch", "head", "options"]  # tanpa PUT/DELETE

    filterset_class = EquipmentFilter
    search_fields = ["equipment_code", "name", "serial_number", "location"]
    ordering_fields = ["equipment_code", "name", "location", "status", "created_at"]
    ordering = ["equipment_code"]

    def get_permissions(self):
        if self.action in WRITE_ACTIONS:
            return [IsAdminOrManager()]
        return [IsOrganizationMember()]

    def get_serializer_class(self):
        if self.action == "history":
            return EquipmentHistorySerializer
        return EquipmentSerializer

    def perform_create(self, serializer):
        user = self.request.user
        serializer.instance = create_equipment(
            organization=user.organization, actor=user, data=serializer.validated_data
        )

    def perform_update(self, serializer):
        serializer.instance = update_equipment(
            equipment=serializer.instance,
            actor=self.request.user,
            data=serializer.validated_data,
        )

    @extend_schema(request=None, responses=EquipmentSerializer)
    @action(detail=True, methods=["post"])
    def retire(self, request, pk=None):
        equipment = retire_equipment(equipment=self.get_object(), actor=request.user)
        return Response(EquipmentSerializer(equipment, context=self.get_serializer_context()).data)

    @action(detail=True, methods=["get"], filter_backends=[])
    def history(self, request, pk=None):
        """Riwayat kejadian equipment (dari audit log), terbaru lebih dulu."""
        equipment = self.get_object()  # lewat queryset terscope: 404 bila milik organisasi lain
        events = (
            AuditLog.objects.filter(
                organization=request.user.organization,
                entity_type="equipment",
                entity_id=str(equipment.pk),
            )
            .select_related("actor")
            .order_by("-created_at")
        )
        page = self.paginate_queryset(events)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)