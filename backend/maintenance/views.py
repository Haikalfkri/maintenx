from datetime import timedelta

from django.db.models import OuterRef, Subquery
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.dates import organization_today
from core.mixins import OrganizationScopedMixin
from core.permissions import IsAdminOrManager, IsOrganizationMember
from equipment.models import EquipmentStatus

from .filters import MaintenancePlanFilter
from .models import MaintenanceOccurrence, MaintenancePlan
from .recurrence import due_status, occurrence_on_or_after
from .serializers import MAX_CALENDAR_DAYS, CalendarQuerySerializer, MaintenancePlanSerializer
from .services import activate_plan, create_plan, deactivate_plan, update_plan

WRITE_ACTIONS = {"create", "update", "partial_update", "deactivate", "activate"}

# Work order terakhir yang dihasilkan tiap plan, diambil dalam SATU query (tanpa N+1)
_latest_occurrence = MaintenanceOccurrence.objects.filter(
    maintenance_plan=OuterRef("pk")
).order_by("-scheduled_due_date")


class MaintenancePlanViewSet(
    OrganizationScopedMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = MaintenancePlan.objects.select_related(
        "equipment", "default_technician"
    ).annotate(
        last_wo_id=Subquery(_latest_occurrence.values("generated_work_order_id")[:1]),
        last_wo_number=Subquery(
            _latest_occurrence.values("generated_work_order__work_order_number")[:1]
        ),
        last_wo_status=Subquery(_latest_occurrence.values("generated_work_order__status")[:1]),
    )
    serializer_class = MaintenancePlanSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    filterset_class = MaintenancePlanFilter
    search_fields = ["title", "equipment__equipment_code", "equipment__name"]
    ordering_fields = ["next_due_date", "title", "frequency", "created_at"]
    ordering = ["next_due_date", "title"]

    def get_permissions(self):
        if self.action in WRITE_ACTIONS:
            return [IsAdminOrManager()]
        return [IsOrganizationMember()]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        user = self.request.user
        if user.is_authenticated and user.organization_id:
            context["today"] = organization_today(user.organization)  # dihitung sekali per request
        return context

    def _fresh(self, plan):
        """Ambil ulang plan lewat queryset ber-annotate agar respons lengkap (last_work_order)."""
        return self.get_queryset().get(pk=plan.pk)

    def perform_create(self, serializer):
        user = self.request.user
        plan = create_plan(
            organization=user.organization, actor=user, data=serializer.validated_data
        )
        serializer.instance = self._fresh(plan)

    def perform_update(self, serializer):
        plan = update_plan(
            plan=serializer.instance, actor=self.request.user, data=serializer.validated_data
        )
        serializer.instance = self._fresh(plan)

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        plan = deactivate_plan(plan=self.get_object(), actor=request.user)
        return Response(self.get_serializer(self._fresh(plan)).data)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        plan = activate_plan(plan=self.get_object(), actor=request.user)
        return Response(self.get_serializer(self._fresh(plan)).data)

    @action(detail=False, methods=["get"], pagination_class=None)
    def calendar(self, request):
        """
        Jatuh tempo plan aktif dalam rentang tanggal (default: bulan ini), untuk tampilan kalender.
        Jadwal ke depan diproyeksikan dari next_due_date; ini bukan work order.
        """
        query = CalendarQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        today = organization_today(request.user.organization)
        start = query.validated_data.get("start_date") or today.replace(day=1)
        end = query.validated_data.get("end_date") or (start + timedelta(days=30))
        if (end - start).days > MAX_CALENDAR_DAYS:
            end = start + timedelta(days=MAX_CALENDAR_DAYS)

        plans = (
            self.get_queryset()
            .filter(is_active=True)
            .exclude(equipment__status=EquipmentStatus.RETIRED)
        )
        events = []
        for plan in plans:
            current = occurrence_on_or_after(
                plan.start_date, plan.frequency, plan.interval_value, max(plan.next_due_date, start)
            )
            while current <= end:
                events.append(
                    {
                        "date": current,
                        "maintenance_plan": plan.pk,
                        "title": plan.title,
                        "equipment": plan.equipment_id,
                        "equipment_code": plan.equipment.equipment_code,
                        # Hanya jatuh tempo saat ini yang bisa DUE/OVERDUE; sisanya proyeksi
                        "status": due_status(current, True, today)
                        if current == plan.next_due_date
                        else "UPCOMING",
                    }
                )
                current = occurrence_on_or_after(
                    plan.start_date, plan.frequency, plan.interval_value, current + timedelta(days=1)
                )

        events.sort(key=lambda e: (e["date"], e["title"]))
        return Response(events)