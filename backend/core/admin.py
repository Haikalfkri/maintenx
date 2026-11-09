from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "organization", "actor", "action", "entity_type", "entity_id")
    list_filter = ("organization", "action", "entity_type")
    search_fields = ("entity_id", "action")

    # Audit log hanya boleh dibaca
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False