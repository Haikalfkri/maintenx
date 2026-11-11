"""Isolasi data: user Org A tidak boleh melihat atau mengubah plan Org B."""
import pytest

from maintenance.models import MaintenancePlan
from maintenance.services import generate_due_work_orders

PLANS = "/api/v1/maintenance-plans/"

pytestmark = pytest.mark.django_db


@pytest.fixture
def plan_b(equipment_b, make_plan):
    return make_plan(equipment_b, title="Plan of Org B")


def test_list_excludes_other_organization(auth_client, manager_a, equipment_a, make_plan, plan_b):
    own = make_plan(equipment_a, title="Plan of Org A")
    response = auth_client(manager_a).get(PLANS)
    assert [row["id"] for row in response.data["results"]] == [str(own.id)]


@pytest.mark.parametrize("role_fixture", ["admin_a", "manager_a", "tech_a"])
def test_cannot_retrieve_other_organization_plan(request, auth_client, role_fixture, plan_b):
    client = auth_client(request.getfixturevalue(role_fixture))
    assert client.get(f"{PLANS}{plan_b.id}/").status_code == 404


def test_cannot_modify_other_organization_plan(auth_client, manager_a, plan_b):
    client = auth_client(manager_a)
    assert client.patch(f"{PLANS}{plan_b.id}/", {"title": "Hacked"}, format="json").status_code == 404
    assert client.post(f"{PLANS}{plan_b.id}/deactivate/").status_code == 404
    assert client.post(f"{PLANS}{plan_b.id}/activate/").status_code == 404
    plan_b.refresh_from_db()
    assert (plan_b.title, plan_b.is_active) == ("Plan of Org B", True)


def test_cannot_create_plan_for_other_organization_equipment(auth_client, manager_a, equipment_b):
    response = auth_client(manager_a).post(
        PLANS,
        {"equipment": str(equipment_b.id), "title": "X", "frequency": "DAILY", "start_date": "2030-01-01"},
        format="json",
    )
    assert response.status_code == 400
    assert "equipment" in response.data
    assert not MaintenancePlan.objects.filter(title="X").exists()


def test_cannot_use_technician_of_other_organization(auth_client, manager_a, equipment_a, tech_b):
    response = auth_client(manager_a).post(
        PLANS,
        {
            "equipment": str(equipment_a.id),
            "title": "X",
            "frequency": "DAILY",
            "start_date": "2030-01-01",
            "default_technician": str(tech_b.id),
        },
        format="json",
    )
    assert response.status_code == 400
    assert "default_technician" in response.data


def test_filter_by_other_organization_equipment_is_rejected(auth_client, manager_a, equipment_b):
    assert auth_client(manager_a).get(PLANS, {"equipment": str(equipment_b.id)}).status_code == 400


def test_calendar_excludes_other_organization(auth_client, manager_a, plan_b):
    response = auth_client(manager_a).get(f"{PLANS}calendar/", {"start_date": "2026-11-01", "end_date": "2026-11-30"})
    assert response.data == []


def test_organization_in_payload_is_ignored(auth_client, manager_a, org_a, org_b, equipment_a):
    response = auth_client(manager_a).post(
        PLANS,
        {
            "equipment": str(equipment_a.id),
            "title": "Mine",
            "frequency": "DAILY",
            "start_date": "2030-01-01",
            "organization": str(org_b.id),
        },
        format="json",
    )
    assert response.status_code == 201
    assert MaintenancePlan.objects.get(title="Mine").organization == org_a


def test_generated_work_orders_stay_in_the_plan_organization(equipment_a, equipment_b, make_plan, org_a, org_b):
    from datetime import date

    from workorders.models import WorkOrder

    past = date(2026, 1, 1)
    make_plan(equipment_a, start_date=past, next_due_date=past)
    make_plan(equipment_b, start_date=past, next_due_date=past)
    generate_due_work_orders()
    assert WorkOrder.objects.filter(organization=org_a).count() == 1
    assert WorkOrder.objects.filter(organization=org_b).count() == 1
    assert not WorkOrder.objects.exclude(organization=org_a).filter(equipment=equipment_a).exists()