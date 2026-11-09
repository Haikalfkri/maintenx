"""Isolasi data: user Org A tidak boleh melihat atau mengubah equipment Org B."""
import pytest

from core.models import AuditLog
from equipment.models import Equipment

EQUIPMENT = "/api/v1/equipment/"
CATEGORIES = "/api/v1/equipment-categories/"

pytestmark = pytest.mark.django_db


def test_list_excludes_other_organization(auth_client, manager_a, equipment_a, equipment_b):
    response = auth_client(manager_a).get(EQUIPMENT)
    ids = [row["id"] for row in response.data["results"]]
    assert ids == [str(equipment_a.id)]


@pytest.mark.parametrize("role_fixture", ["admin_a", "manager_a", "tech_a"])
def test_cannot_retrieve_other_organization_equipment(
    request, auth_client, role_fixture, equipment_b
):
    client = auth_client(request.getfixturevalue(role_fixture))
    assert client.get(f"{EQUIPMENT}{equipment_b.id}/").status_code == 404


def test_cannot_update_other_organization_equipment(auth_client, manager_a, equipment_b):
    response = auth_client(manager_a).patch(
        f"{EQUIPMENT}{equipment_b.id}/", {"name": "Hacked"}, format="json"
    )
    assert response.status_code == 404
    equipment_b.refresh_from_db()
    assert equipment_b.name == "Welding Robot"


def test_cannot_retire_other_organization_equipment(auth_client, manager_a, equipment_b):
    assert auth_client(manager_a).post(f"{EQUIPMENT}{equipment_b.id}/retire/").status_code == 404
    equipment_b.refresh_from_db()
    assert not equipment_b.is_retired


def test_cannot_read_history_of_other_organization_equipment(
    auth_client, manager_a, manager_b, equipment_b
):
    auth_client(manager_b).patch(f"{EQUIPMENT}{equipment_b.id}/", {"location": "X"}, format="json")
    assert AuditLog.objects.filter(entity_id=str(equipment_b.id)).exists()
    response = auth_client(manager_a).get(f"{EQUIPMENT}{equipment_b.id}/history/")
    assert response.status_code == 404


def test_same_code_allowed_in_different_organizations(equipment_a, equipment_b):
    assert equipment_a.equipment_code == equipment_b.equipment_code


def test_cannot_use_category_of_other_organization(auth_client, manager_a, category_b):
    response = auth_client(manager_a).post(
        EQUIPMENT,
        {"equipment_code": "X-1", "name": "X", "location": "Y", "category": str(category_b.id)},
        format="json",
    )
    assert response.status_code == 400
    assert "category" in response.data
    assert not Equipment.objects.filter(equipment_code="X-1").exists()


def test_cannot_move_equipment_to_category_of_other_organization(
    auth_client, manager_a, equipment_a, category_b
):
    response = auth_client(manager_a).patch(
        f"{EQUIPMENT}{equipment_a.id}/", {"category": str(category_b.id)}, format="json"
    )
    assert response.status_code == 400
    equipment_a.refresh_from_db()
    assert equipment_a.category != category_b


def test_filter_by_other_organization_category_is_rejected(auth_client, manager_a, category_b):
    response = auth_client(manager_a).get(EQUIPMENT, {"category": str(category_b.id)})
    assert response.status_code == 400  # sama seperti kategori yang tidak ada


def test_organization_in_payload_is_ignored(auth_client, manager_a, org_a, org_b):
    response = auth_client(manager_a).post(
        EQUIPMENT,
        {"equipment_code": "NEW-1", "name": "N", "location": "L", "organization": str(org_b.id)},
        format="json",
    )
    assert response.status_code == 201
    assert Equipment.objects.get(equipment_code="NEW-1").organization == org_a


def test_categories_are_isolated(auth_client, manager_a, category_a, category_b):
    client = auth_client(manager_a)
    assert [c["id"] for c in client.get(CATEGORIES).data] == [str(category_a.id)]
    assert client.get(f"{CATEGORIES}{category_b.id}/").status_code == 404
    assert client.patch(f"{CATEGORIES}{category_b.id}/", {"name": "X"}, format="json").status_code == 404


def test_same_category_name_allowed_in_different_organizations(auth_client, manager_b, category_a):
    response = auth_client(manager_b).post(CATEGORIES, {"name": category_a.name}, format="json")
    assert response.status_code == 201