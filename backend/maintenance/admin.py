from django.contrib import admin

from .models import MaintenanceOccurrence, MaintenancePlan

@admin.register(MaintenancePlan)
class MaintenancePlanAdmin(admin.ModelAdmin):
    list_display = ("title", "equipment", "organization", "frequency", "next_due_date", "is_active")
    list_filter = ("organization", "frequency", "is_active")
    search_fields = ("title", "equipment__equipment_code")

@admin.register(MaintenanceOccurrence)
class MaintenanceOccurrenceAdmin(admin.ModelAdmin):
    list_display = ("maintenance_plan", "scheduled_due_date", "generated_work_order")
    list_filter = ("organization",)