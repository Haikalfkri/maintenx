from rest_framework import serializers

class OrganizationScopedRelatedField(serializers.PrimaryKeyRelatedField):
    """
    Field relasi (FK) yang hanya menerima objek dari organisasi user yang login.

    Objek milik organisasi lain diperlakukan sama seperti objek yang tidak ada,
    sehingga keberadaannya tidak bocor.
    """

    def get_queryset(self):
        queryset = super().get_queryset()
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return queryset.none()
        return queryset.filter(organization=request.user.organization)