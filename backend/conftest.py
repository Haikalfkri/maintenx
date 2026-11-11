"""Fixture bersama untuk semua test."""
import uuid

import pytest
from rest_framework.test import APIClient

from accounts.models import Organization, User
from core.roles import Role
from equipment.models import Equipment, EquipmentCategory
from maintenance.models import MaintenancePlan

PASSWORD = "TestPass12345!"


@pytest.fixture
def password():
    return PASSWORD


@pytest.fixture
def make_user(db):
    def _make(organization, role, email=None, **extra):
        email = email or f"{role.lower()}-{uuid.uuid4().hex[:6]}@{organization.slug}.test"
        return User.objects.create_user(
            email, PASSWORD, organization=organization, role=role, **extra
        )

    return _make


@pytest.fixture
def org_a(db):
    return Organization.objects.create(name="Org A", slug="org-a")


@pytest.fixture
def org_b(db):
    return Organization.objects.create(name="Org B", slug="org-b")


@pytest.fixture
def admin_a(make_user, org_a):
    return make_user(org_a, Role.ADMIN, first_name="Ada", last_name="Admin")


@pytest.fixture
def manager_a(make_user, org_a):
    return make_user(org_a, Role.MANAGER)


@pytest.fixture
def tech_a(make_user, org_a):
    return make_user(org_a, Role.TECHNICIAN, first_name="Tono", last_name="Teknisi")


@pytest.fixture
def admin_b(make_user, org_b):
    return make_user(org_b, Role.ADMIN)


@pytest.fixture
def manager_b(make_user, org_b):
    return make_user(org_b, Role.MANAGER)


@pytest.fixture
def tech_b(make_user, org_b):
    return make_user(org_b, Role.TECHNICIAN, first_name="Tina", last_name="Teknisi")


@pytest.fixture
def anon_client():
    return APIClient()


@pytest.fixture
def auth_client():
    """Pemakaian: auth_client(user) -> APIClient yang sudah login sebagai user."""

    def _client(user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    return _client


# --- equipment ---------------------------------------------------------------

@pytest.fixture
def category_a(org_a):
    return EquipmentCategory.objects.create(organization=org_a, name="CNC Machine")


@pytest.fixture
def category_b(org_b):
    return EquipmentCategory.objects.create(organization=org_b, name="Welding")


@pytest.fixture
def equipment_a(org_a, category_a):
    return Equipment.objects.create(
        organization=org_a,
        category=category_a,
        equipment_code="CNC-001",
        name="CNC Milling Machine",
        location="Production Hall A",
        serial_number="SN-1001",
    )


@pytest.fixture
def equipment_b(org_b, category_b):
    # Kode sama dengan equipment_a: sah karena unik per organisasi
    return Equipment.objects.create(
        organization=org_b,
        category=category_b,
        equipment_code="CNC-001",
        name="Welding Robot",
        location="Workshop 1",
    )

# --- maintenance -------------------------------------------------------------

@pytest.fixture
def make_plan(db):
    """Pemakaian: make_plan(equipment, start_date=..., next_due_date=..., **opsional)."""
    from datetime import date

    def _make(equipment, **overrides):
        data = {
            "organization": equipment.organization,
            "equipment": equipment,
            "title": "Monthly inspection",
            "frequency": "MONTHLY",
            "start_date": date(2026, 11, 1),
            "next_due_date": date(2026, 11, 1),
        }
        data.update(overrides)
        return MaintenancePlan.objects.create(**data)

    return _make