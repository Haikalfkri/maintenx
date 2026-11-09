from django.db import models


class Role(models.TextChoices):
    ADMIN = "ADMIN", "Admin"
    MANAGER = "MANAGER", "Manager"
    TECHNICIAN = "TECHNICIAN", "Technician"