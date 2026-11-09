import pytest

EQUIPMENT = "/api/v1/equipment/"
CATEGORIES = "/api/v1/equipment-categories/"

pytestmark = pytest.mark.django_db

NEW_EQUIPMENT = {"equipment_code": "NEW-1", "name": "New Machine", "location": "Hall A"}


def test_anonymous_is_rejected(anon_client, equipment_a):
    assert anon_client.get(EQUIPMENT).status_code == 401
    assert anon_client.get(f"{EQUIPMENT}{equipment_a.id}/").status_code == 401
    assert anon_client.post(EQUIPMENT, NEW_EQUIPMENT, format="json").status_code == 401
    assert anon_client.get(CATEGORIES).status_code == 401


# --- technician: read-only ------------------------------------------------------

def test_technician_can_read_equipment(auth_client, tech_a, equipment_a):
    client = auth_client(tech_a)
    assert client.get(EQUIPMENT).status_code == 200
    assert client.get(f"{EQUIPMENT}{equipment_a.id}/").status_code == 200
    assert client.get(f"{EQUIPMENT}{equipment_a.id}/history/").status_code == 200
    assert client.get(CATEGORIES).status_code == 200


def test_technician_cannot_create_equipment(auth_client, tech_a):
    assert auth_client(tech_a).post(EQUIPMENT, NEW_EQUIPMENT, format="json").status_code == 403


def test_technician_cannot_update_equipment(auth_client, tech_a, equipment_a):
    response = auth_client(tech_a).patch(
        f"{EQUIPMENT}{equipment_a.id}/", {"name": "Hacked"}, format="json"
    )
    assert response.status_code == 403
    equipment_a.refresh_from_db()
    assert equipment_a.name == "CNC Milling Machine"


def test_technician_cannot_retire_equipment(auth_client, tech_a, equipment_a):
    assert auth_client(tech_a).post(f"{EQUIPMENT}{equipment_a.id}/retire/").status_code == 403
    equipment_a.refresh_from_db()
    assert not equipment_a.is_retired


def test_technician_cannot_manage_categories(auth_client, tech_a, category_a):
    client = auth_client(tech_a)
    assert client.post(CATEGORIES, {"name": "New"}, format="json").status_code == 403
    assert client.patch(f"{CATEGORIES}{category_a.id}/", {"name": "X"}, format="json").status_code == 403


# --- admin and manager: full access ----------------------------------------------

@pytest.mark.parametrize("role_fixture", ["admin_a", "manager_a"])
def test_admin_and_manager_can_manage_equipment(request, auth_client, role_fixture, equipment_a):
    client = auth_client(request.getfixturevalue(role_fixture))
    assert client.post(EQUIPMENT, NEW_EQUIPMENT, format="json").status_code == 201
    assert client.patch(f"{EQUIPMENT}{equipment_a.id}/", {"name": "Edited"}, format="json").status_code == 200
    assert client.post(f"{EQUIPMENT}{equipment_a.id}/retire/").status_code == 200
    assert client.post(CATEGORIES, {"name": "Brand new"}, format="json").status_code == 201