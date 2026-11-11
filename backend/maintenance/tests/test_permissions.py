import pytest

PLANS = "/api/v1/maintenance-plans/"

pytestmark = pytest.mark.django_db


def new_plan(equipment):
    return {"equipment": str(equipment.id), "title": "New plan", "frequency": "DAILY", "start_date": "2030-01-01"}


def test_anonymous_is_rejected(anon_client, equipment_a, make_plan):
    plan = make_plan(equipment_a)
    assert anon_client.get(PLANS).status_code == 401
    assert anon_client.get(f"{PLANS}{plan.id}/").status_code == 401
    assert anon_client.get(f"{PLANS}calendar/").status_code == 401
    assert anon_client.post(PLANS, new_plan(equipment_a), format="json").status_code == 401


def test_technician_can_read(auth_client, tech_a, equipment_a, make_plan):
    plan = make_plan(equipment_a)
    client = auth_client(tech_a)
    assert client.get(PLANS).status_code == 200
    assert client.get(f"{PLANS}{plan.id}/").status_code == 200
    assert client.get(f"{PLANS}calendar/").status_code == 200


def test_technician_cannot_modify(auth_client, tech_a, equipment_a, make_plan):
    plan = make_plan(equipment_a)
    client = auth_client(tech_a)
    assert client.post(PLANS, new_plan(equipment_a), format="json").status_code == 403
    assert client.patch(f"{PLANS}{plan.id}/", {"title": "Hacked"}, format="json").status_code == 403
    assert client.post(f"{PLANS}{plan.id}/deactivate/").status_code == 403
    assert client.post(f"{PLANS}{plan.id}/activate/").status_code == 403
    plan.refresh_from_db()
    assert plan.title == "Monthly inspection"
    assert plan.is_active is True


@pytest.mark.parametrize("role_fixture", ["admin_a", "manager_a"])
def test_admin_and_manager_can_manage_plans(request, auth_client, role_fixture, equipment_a, make_plan):
    plan = make_plan(equipment_a)
    client = auth_client(request.getfixturevalue(role_fixture))
    assert client.post(PLANS, new_plan(equipment_a), format="json").status_code == 201
    assert client.patch(f"{PLANS}{plan.id}/", {"title": "Edited"}, format="json").status_code == 200
    assert client.post(f"{PLANS}{plan.id}/deactivate/").status_code == 200
    assert client.post(f"{PLANS}{plan.id}/activate/").status_code == 200