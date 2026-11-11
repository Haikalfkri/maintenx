import django_filters

from equipment.models import Equipment
from core.dates import organization_today

from .models import MaintenancePlan
from .recurrence import DUE, INACTIVE, OVERDUE, UPCOMING

STATUS_CHOICES = [(UPCOMING, "Upcoming"), (DUE, "Due"), (OVERDUE, "Overdue"), (INACTIVE, "Inactive")]


def equipment_for_request(request):
    if request is None or not request.user.is_authenticated:
        return Equipment.objects.none()
    return Equipment.objects.filter(organization=request.user.organization)


class MaintenancePlanFilter(django_filters.FilterSet):
    # UPCOMING / DUE / OVERDUE dihitung terhadap tanggal 'hari ini' milik organisasi
    status = django_filters.ChoiceFilter(choices=STATUS_CHOICES, method="filter_status")
    # Batas tanggal bersifat inklusif
    due_before = django_filters.DateFilter(field_name="next_due_date", lookup_expr="lte")
    due_after = django_filters.DateFilter(field_name="next_due_date", lookup_expr="gte")
    equipment = django_filters.ModelChoiceFilter(queryset=equipment_for_request)

    class Meta:
        model = MaintenancePlan
        fields = ["status", "due_before", "due_after", "equipment"]

    def filter_status(self, queryset, name, value):
        if value == INACTIVE:
            return queryset.filter(is_active=False)

        today = organization_today(self.request.user.organization)
        queryset = queryset.filter(is_active=True)
        if value == OVERDUE:
            return queryset.filter(next_due_date__lt=today)
        if value == DUE:
            return queryset.filter(next_due_date=today)
        return queryset.filter(next_due_date__gt=today)  # UPCOMING