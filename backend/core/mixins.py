class OrganizationScopedMixin:
    """
    Batasi queryset ke organisasi user yang login.

    Detail dan action mengambil objek lewat get_queryset(), sehingga objek
    milik organisasi lain otomatis menghasilkan 404.
    Taruh mixin ini PALING KIRI di daftar kelas view.
    """

    organization_field = "organization"

    def get_queryset(self):
        queryset = super().get_queryset()
        if getattr(self, "swagger_fake_view", False):  # pembuatan skema OpenAPI
            return queryset.none()
        return queryset.filter(**{self.organization_field: self.request.user.organization})