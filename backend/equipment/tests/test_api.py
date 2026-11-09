import pytest

from core.models import AuditLog
from equipment.models import Equipment

EQUIPMENT = "/api/v1/equipment/"
CATEGORIES = "/api/v1/equipment-categories/"

pytestmark = pytest.mark.django_db


def payload(**overrides):
    data = {
        "equipment_code": "cmp-001",
        "name": "Air Compressor",
        "manufacturer": "AirWorks",
        "model_number": "AW-75",
        "location": "Utility Room",
        "status": "OPERATIONAL",
    }
    data.update(overrides)
    return data


# --- create -------------------------------------------------------------------

def test_create_equipment(auth_client, manager_a, org_a, category_a):
    response = auth_client(manager_a).post(
        EQUIPMENT, payload(category=str(category_a.id)), format="json"
    )
    assert response.status_code == 201
    assert response.data["equipment_code"] == "CMP-001"  # dinormalisasi ke huruf besar
    assert response.data["category_name"] == "CNC Machine"
    assert response.data["status"] == "OPERATIONAL"
    assert "organization" not in response.data
    assert Equipment.objects.get(equipment_code="CMP-001").organization == org_a


def test_create_without_status_defaults_to_operational(auth_client, manager_a):
    data = payload()
    del data["status"]
    response = auth_client(manager_a).post(EQUIPMENT, data, format="json")
    assert response.status_code == 201
    assert response.data["status"] == "OPERATIONAL"


def test_create_requires_name_and_location(auth_client, manager_a):
    response = auth_client(manager_a).post(EQUIPMENT, {"equipment_code": "X-1"}, format="json")
    assert response.status_code == 400
    assert {"name", "location"} <= set(response.data)


def test_create_records_audit_event(auth_client, manager_a):
    response = auth_client(manager_a).post(EQUIPMENT, payload(), format="json")
    event = AuditLog.objects.get(entity_id=response.data["id"])
    assert event.action == "equipment.created"
    assert event.actor == manager_a
    assert event.organization == manager_a.organization


def test_duplicate_code_rejected_in_same_organization(auth_client, manager_a, equipment_a):
    response = auth_client(manager_a).post(
        EQUIPMENT, payload(equipment_code=equipment_a.equipment_code), format="json"
    )
    assert response.status_code == 400
    assert "equipment_code" in response.data


def test_duplicate_code_is_case_insensitive(auth_client, manager_a, equipment_a):
    response = auth_client(manager_a).post(
        EQUIPMENT, payload(equipment_code="cnc-001"), format="json"
    )
    assert response.status_code == 400


def test_cannot_create_retired_equipment_directly(auth_client, manager_a):
    response = auth_client(manager_a).post(EQUIPMENT, payload(status="RETIRED"), format="json")
    assert response.status_code == 400
    assert "status" in response.data


def test_installation_cannot_precede_purchase(auth_client, manager_a):
    response = auth_client(manager_a).post(
        EQUIPMENT,
        payload(purchase_date="2026-05-01", installation_date="2026-04-01"),
        format="json",
    )
    assert response.status_code == 400
    assert "installation_date" in response.data


def test_invalid_status_rejected(auth_client, manager_a):
    response = auth_client(manager_a).post(EQUIPMENT, payload(status="BROKEN"), format="json")
    assert response.status_code == 400


# --- update -------------------------------------------------------------------

def test_update_equipment(auth_client, manager_a, equipment_a):
    response = auth_client(manager_a).patch(
        f"{EQUIPMENT}{equipment_a.id}/",
        {"location": "Production Hall C", "status": "OUT_OF_SERVICE"},
        format="json",
    )
    assert response.status_code == 200
    equipment_a.refresh_from_db()
    assert equipment_a.location == "Production Hall C"
    assert equipment_a.status == "OUT_OF_SERVICE"


def test_update_records_only_changed_fields(auth_client, manager_a, equipment_a):
    auth_client(manager_a).patch(
        f"{EQUIPMENT}{equipment_a.id}/",
        {"location": "Hall C", "name": equipment_a.name},  # name tidak berubah
        format="json",
    )
    event = AuditLog.objects.get(entity_id=str(equipment_a.id), action="equipment.updated")
    assert set(event.metadata["changes"]) == {"location"}
    assert event.metadata["changes"]["location"] == {"from": "Production Hall A", "to": "Hall C"}


def test_update_without_changes_records_no_event(auth_client, manager_a, equipment_a):
    auth_client(manager_a).patch(
        f"{EQUIPMENT}{equipment_a.id}/", {"name": equipment_a.name}, format="json"
    )
    assert not AuditLog.objects.filter(action="equipment.updated").exists()


def test_update_cannot_set_retired_status(auth_client, manager_a, equipment_a):
    response = auth_client(manager_a).patch(
        f"{EQUIPMENT}{equipment_a.id}/", {"status": "RETIRED"}, format="json"
    )
    assert response.status_code == 400


def test_update_code_to_existing_code_rejected(auth_client, manager_a, equipment_a, org_a):
    other = Equipment.objects.create(
        organization=org_a, equipment_code="PRS-001", name="Press", location="Hall B"
    )
    response = auth_client(manager_a).patch(
        f"{EQUIPMENT}{other.id}/", {"equipment_code": equipment_a.equipment_code}, format="json"
    )
    assert response.status_code == 400


def test_keeping_own_code_on_update_is_allowed(auth_client, manager_a, equipment_a):
    response = auth_client(manager_a).patch(
        f"{EQUIPMENT}{equipment_a.id}/",
        {"equipment_code": equipment_a.equipment_code, "name": "Renamed"},
        format="json",
    )
    assert response.status_code == 200


def test_put_and_delete_not_allowed(auth_client, manager_a, equipment_a):
    client = auth_client(manager_a)
    assert client.put(f"{EQUIPMENT}{equipment_a.id}/", payload(), format="json").status_code == 405
    assert client.delete(f"{EQUIPMENT}{equipment_a.id}/").status_code == 405


# --- retire ---------------------------------------------------------------------

def test_retire_equipment(auth_client, manager_a, equipment_a):
    response = auth_client(manager_a).post(f"{EQUIPMENT}{equipment_a.id}/retire/")
    assert response.status_code == 200
    assert response.data["status"] == "RETIRED"
    assert response.data["retired_at"] is not None
    equipment_a.refresh_from_db()
    assert equipment_a.is_retired
    event = AuditLog.objects.get(action="equipment.retired")
    assert event.metadata == {"from_status": "OPERATIONAL"}


def test_retire_twice_returns_conflict(auth_client, manager_a, equipment_a):
    client = auth_client(manager_a)
    assert client.post(f"{EQUIPMENT}{equipment_a.id}/retire/").status_code == 200
    assert client.post(f"{EQUIPMENT}{equipment_a.id}/retire/").status_code == 409


def test_retired_equipment_cannot_be_modified(auth_client, manager_a, equipment_a):
    client = auth_client(manager_a)
    client.post(f"{EQUIPMENT}{equipment_a.id}/retire/")
    response = client.patch(f"{EQUIPMENT}{equipment_a.id}/", {"name": "New name"}, format="json")
    assert response.status_code == 409


def test_retired_equipment_stays_in_list_with_retired_status(auth_client, manager_a, equipment_a):
    client = auth_client(manager_a)
    client.post(f"{EQUIPMENT}{equipment_a.id}/retire/")
    response = client.get(EQUIPMENT, {"status": "RETIRED"})
    assert [e["equipment_code"] for e in response.data["results"]] == ["CNC-001"]


# --- list: search, filter, ordering, pagination -------------------------------

@pytest.fixture
def fleet(org_a, category_a):
    from equipment.models import EquipmentCategory

    compressor = EquipmentCategory.objects.create(organization=org_a, name="Compressor")
    rows = [
        ("CNC-001", "CNC Milling Machine", category_a, "Production Hall A", "OPERATIONAL", "SN-1"),
        ("CMP-001", "Air Compressor", compressor, "Utility Room", "OPERATIONAL", "SN-2"),
        ("CMP-002", "Backup Compressor", compressor, "Utility Room", "OUT_OF_SERVICE", "SN-3"),
        ("GEN-001", "Standby Generator", None, "Power House", "UNDER_MAINTENANCE", "GEN-77"),
    ]
    for code, name, category, location, status, serial in rows:
        Equipment.objects.create(
            organization=org_a,
            equipment_code=code,
            name=name,
            category=category,
            location=location,
            status=status,
            serial_number=serial,
        )
    return {"compressor": compressor}


def codes(response):
    return [row["equipment_code"] for row in response.data["results"]]


def test_list_is_paginated(auth_client, manager_a, fleet):
    response = auth_client(manager_a).get(EQUIPMENT)
    assert response.data["count"] == 4
    assert {"count", "next", "previous", "results"} <= set(response.data)
    assert codes(response) == ["CMP-001", "CMP-002", "CNC-001", "GEN-001"]  # default ordering


def test_page_size_is_capped(auth_client, manager_a, fleet):
    response = auth_client(manager_a).get(EQUIPMENT, {"page_size": 2})
    assert len(response.data["results"]) == 2
    assert response.data["next"] is not None


@pytest.mark.parametrize(
    "term, expected",
    [
        ("cnc", ["CNC-001"]),  # kode
        ("compressor", ["CMP-001", "CMP-002"]),  # nama
        ("GEN-77", ["GEN-001"]),  # serial number
        ("utility", ["CMP-001", "CMP-002"]),  # lokasi
    ],
)
def test_search(auth_client, manager_a, fleet, term, expected):
    assert codes(auth_client(manager_a).get(EQUIPMENT, {"search": term})) == expected


def test_filter_by_status(auth_client, manager_a, fleet):
    response = auth_client(manager_a).get(EQUIPMENT, {"status": "OUT_OF_SERVICE"})
    assert codes(response) == ["CMP-002"]


def test_filter_by_category(auth_client, manager_a, fleet):
    response = auth_client(manager_a).get(EQUIPMENT, {"category": str(fleet["compressor"].id)})
    assert codes(response) == ["CMP-001", "CMP-002"]


def test_filter_by_location(auth_client, manager_a, fleet):
    assert codes(auth_client(manager_a).get(EQUIPMENT, {"location": "hall"})) == ["CNC-001"]


def test_invalid_status_filter_is_rejected(auth_client, manager_a, fleet):
    assert auth_client(manager_a).get(EQUIPMENT, {"status": "NOPE"}).status_code == 400


def test_ordering(auth_client, manager_a, fleet):
    response = auth_client(manager_a).get(EQUIPMENT, {"ordering": "-name"})
    assert codes(response)[0] == "GEN-001"


def test_ordering_by_unlisted_field_is_ignored(auth_client, manager_a, fleet):
    assert auth_client(manager_a).get(EQUIPMENT, {"ordering": "organization"}).status_code == 200


def test_list_query_count_does_not_grow_with_rows(
    auth_client, manager_a, fleet, django_assert_max_num_queries
):
    # Tidak boleh N+1: nama kategori diambil dengan select_related
    with django_assert_max_num_queries(6):
        assert auth_client(manager_a).get(EQUIPMENT).status_code == 200


# --- history ----------------------------------------------------------------------

def test_history_lists_events_newest_first(auth_client, manager_a, equipment_a):
    client = auth_client(manager_a)
    client.patch(f"{EQUIPMENT}{equipment_a.id}/", {"location": "Hall C"}, format="json")
    client.post(f"{EQUIPMENT}{equipment_a.id}/retire/")

    response = client.get(f"{EQUIPMENT}{equipment_a.id}/history/")
    assert response.status_code == 200
    assert [e["action"] for e in response.data["results"]] == [
        "equipment.retired",
        "equipment.updated",
    ]
    assert str(response.data["results"][0]["actor"]) == str(manager_a.id)
    assert response.data["results"][0]["actor_name"] == manager_a.full_name


# --- categories -------------------------------------------------------------------

def test_create_and_list_categories(auth_client, manager_a, category_a):
    client = auth_client(manager_a)
    assert client.post(CATEGORIES, {"name": "Compressor"}, format="json").status_code == 201
    response = client.get(CATEGORIES)
    assert [c["name"] for c in response.data] == ["CNC Machine", "Compressor"]  # tanpa paginasi


def test_duplicate_category_name_rejected_case_insensitive(auth_client, manager_a, category_a):
    response = auth_client(manager_a).post(CATEGORIES, {"name": "cnc machine"}, format="json")
    assert response.status_code == 400


def test_rename_category(auth_client, manager_a, category_a):
    response = auth_client(manager_a).patch(
        f"{CATEGORIES}{category_a.id}/", {"name": "CNC Machines"}, format="json"
    )
    assert response.status_code == 200
    category_a.refresh_from_db()
    assert category_a.name == "CNC Machines"


def test_categories_cannot_be_deleted(auth_client, manager_a, category_a):
    assert auth_client(manager_a).delete(f"{CATEGORIES}{category_a.id}/").status_code == 405