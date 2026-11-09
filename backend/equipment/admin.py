from django.contrib import admin

from .models import Equipment, EquipmentCategory


@admin.register(EquipmentCategory)
class EquipmentCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "organization")
    list_filter = ("organization",)
    search_fields = ("name",)


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ("equipment_code", "name", "organization", "category", "location", "status")
    list_filter = ("organization", "status", "category")
    search_fields = ("equipment_code", "name", "serial_number", "location")