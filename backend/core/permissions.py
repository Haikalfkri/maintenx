from django.contrib.sites import requests
from django.contrib.sites import requests
from django.contrib.sites import requests
from django.contrib.sites import requests
from rest_framework.permissions import BasePermission

from core.roles import Role

class IsOrganizationMember(BasePermission):
    """
    Dasar semua endpoint aplikasi: user login, aktif, punya organisasi,
    dan organisasinya aktif. Superuser platform tanpa organisasi ditolak.
    """

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.organization_id
            and user.organization.is_active
        )

class IsAdmin(IsOrganizationMember):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == Role.ADMIN

class IsAdminOrManager(IsOrganizationMember):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role in (
            Role.ADMIN,
            Role.MANAGER,
        )