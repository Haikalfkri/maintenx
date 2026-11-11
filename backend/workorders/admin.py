from django.contrib import admin

from .models import WorkOrder, WorkOrderHistory

@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = ("work_order_number", "title", "organization", "work_order_type", "status", "due_date")
    list_filter = ("organization", "status", "work_order_type", "priority")
    search_fields = ("work_order_number", "title")

@admin.register(WorkOrderHistory)
class WorkOrderHistoryAdmin(admin.ModelAdmin):
    list_display = ("created_at", "work_order", "event_type", "actor", "from_status", "to_status")
    list_filter = ("organization", "event_type")