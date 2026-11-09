import django_filters

from .models import Equipment, EquipmentCategory


def categories_for_request(request):
    """Filter category hanya boleh memilih kategori milik organisasi user."""
    if request is None or not request.user.is_authenticated:
        return EquipmentCategory.objects.none()
    return EquipmentCategory.objects.filter(organization=request.user.organization)


class EquipmentFilter(django_filters.FilterSet):
    category = django_filters.ModelChoiceFilter(queryset=categories_for_request)
    location = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = Equipment
        fields = ["status", "category", "location"]