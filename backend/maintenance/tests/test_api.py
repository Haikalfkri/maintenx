from datetime import timedelta

import pytest
from django.utils import timezone

from core.dates import organization_today
from core.models import AuditLog
from maintenance.models import MaintenancePlan
from maintenance.services import generate_due_work_orders

PLANS = "/api/v1/maintenance-plans/"

pytestmark = pytest.mark.django_db


@pytest.fixture
def today(org_a):
    return organization_today(org_a)


def payload(equipment, start_date, **overrides):
    data = {
        "equipment": str(equipment.id),
        "title": "Monthly lubrication inspection",
        "description": "Inspect lubrication system.",
        "frequency": "MONTHLY",
        "start_date": str(start_date),
    }
    data.update(overrides)
    return data


# --- create -------------------------------------------------------------------

def test_create_plan_in_the_future(auth_client, manager_a, equipment_a, tech_a, today):
    start = today + timedelta(days=5)
    response = auth_client(manager_a).post(
        PLANS,
        payload(equipment_a, start, estimated_duration_minutes=45, default_technician=str(tech_a.id)),
        format="json",
    )
    assert response.status_code == 201
    assert response.data["next_due_date"] == str(start)  # dihitung server
    assert response.data["due_status"] == "UPCOMING"
    assert response.data["is_active"] is True
    assert response.data["equipment_code"] == "CNC-001"
    assert response.data["default_technician_name"] == tech_a.full_name
    assert response.data["last_work_order"] is None
    assert "organization" not in response.data
    plan = MaintenancePlan.objects.get(pk=response.data["id"])
    assert plan.organization == manager_a.organization
    assert AuditLog.objects.filter(action="maintenance_plan.created", entity_id=str(plan.pk)).exists()


def test_plan_starting_today_is_due_today(auth_client, manager_a, equipment_a, today):
    response = auth_client(manager_a).post(PLANS, payload(equipment_a, today), format="json")
    assert response.data["due_status"] == "DUE"


def test_plan_with_past_start_gets_the_next_future_occurrence(auth_client, manager_a, equipment_a, today):
    response = auth_client(manager_a).post(
        PLANS, payload(equipment_a, today - timedelta(days=10), frequency="WEEKLY"), format="json"
    )
    assert response.status_code == 201
    assert response.data["next_due_date"] == str(today + timedelta(days=4))  # bukan overdue
    assert response.data["due_status"] == "UPCOMING"


def test_next_due_date_cannot_be_set_by_the_client(auth_client, manager_a, equipment_a, today):
    start = today + timedelta(days=5)
    response = auth_client(manager_a).post(
        PLANS, payload(equipment_a, start, next_due_date=str(today + timedelta(days=99))), format="json"
    )
    assert response.status_code == 201
    assert response.data["next_due_date"] == str(start)


@pytest.mark.parametrize(
    "overrides, field",
    [
        ({"frequency": "YEARLY"}, "frequency"),
        ({"interval_value": 2}, "interval_value"),
        ({"title": "   "}, "title"),
        ({"estimated_duration_minutes": 0}, "estimated_duration_minutes"),
    ],
)
def test_create_validation(auth_client, manager_a, equipment_a, today, overrides, field):
    response = auth_client(manager_a).post(PLANS, payload(equipment_a, today, **overrides), format="json")
    assert response.status_code == 400
    assert field in response.data


def test_create_requires_start_date_and_equipment(auth_client, manager_a):
    response = auth_client(manager_a).post(PLANS, {"title": "X", "frequency": "DAILY"}, format="json")
    assert response.status_code == 400
    assert {"equipment", "start_date"} <= set(response.data)


def test_retired_equipment_cannot_get_a_plan(auth_client, manager_a, equipment_a, today):
    equipment_a.status = "RETIRED"
    equipment_a.retired_at = timezone.now()
    equipment_a.save()
    response = auth_client(manager_a).post(PLANS, payload(equipment_a, today), format="json")
    assert response.status_code == 400
    assert "equipment" in response.data


def test_default_technician_must_be_an_active_technician(auth_client, manager_a, equipment_a, today, make_user, org_a):
    client = auth_client(manager_a)
    not_a_technician = client.post(PLANS, payload(equipment_a, today, default_technician=str(manager_a.id)), format="json")
    assert not_a_technician.status_code == 400

    inactive = make_user(org_a, "TECHNICIAN", is_active=False)
    inactive_response = client.post(PLANS, payload(equipment_a, today, default_technician=str(inactive.id)), format="json")
    assert inactive_response.status_code == 400


# --- update ------------------------------------------------------------------------

def test_update_plan_and_record_audit(auth_client, manager_a, equipment_a, make_plan):
    plan = make_plan(equipment_a, title="Old title")
    response = auth_client(manager_a).patch(
        f"{PLANS}{plan.id}/", {"title": "New title", "frequency": "WEEKLY"}, format="json"
    )
    assert response.status_code == 200
    plan.refresh_from_db()
    assert (plan.title, plan.frequency) == ("New title", "WEEKLY")
    event = AuditLog.objects.get(action="maintenance_plan.updated", entity_id=str(plan.pk))
    assert event.metadata["changes"]["title"] == {"from": "Old title", "to": "New title"}


def test_equipment_and_start_date_cannot_be_changed(auth_client, manager_a, equipment_a, make_plan, org_a):
    plan = make_plan(equipment_a)
    other = type(equipment_a).objects.create(organization=org_a, equipment_code="PRS-1", name="P", location="B")
    client = auth_client(manager_a)
    assert client.patch(f"{PLANS}{plan.id}/", {"equipment": str(other.id)}, format="json").status_code == 400
    assert client.patch(f"{PLANS}{plan.id}/", {"start_date": "2030-01-01"}, format="json").status_code == 400


def test_is_active_and_next_due_date_are_ignored_on_update(auth_client, manager_a, equipment_a, make_plan):
    plan = make_plan(equipment_a)
    original_due = plan.next_due_date
    auth_client(manager_a).patch(
        f"{PLANS}{plan.id}/", {"is_active": False, "next_due_date": "2030-01-01"}, format="json"
    )
    plan.refresh_from_db()
    assert plan.is_active is True
    assert plan.next_due_date == original_due


def test_put_and_delete_not_allowed(auth_client, manager_a, equipment_a, make_plan):
    plan = make_plan(equipment_a)
    client = auth_client(manager_a)
    assert client.put(f"{PLANS}{plan.id}/", {}, format="json").status_code == 405
    assert client.delete(f"{PLANS}{plan.id}/").status_code == 405


# --- deactivate / activate -------------------------------------------------------------

def test_deactivate_and_activate(auth_client, manager_a, equipment_a, make_plan, today):
    plan = make_plan(equipment_a, start_date=today, next_due_date=today)
    client = auth_client(manager_a)

    deactivated = client.post(f"{PLANS}{plan.id}/deactivate/")
    assert deactivated.status_code == 200
    assert deactivated.data["is_active"] is False
    assert deactivated.data["due_status"] == "INACTIVE"
    assert client.post(f"{PLANS}{plan.id}/deactivate/").status_code == 409

    activated = client.post(f"{PLANS}{plan.id}/activate/")
    assert activated.status_code == 200
    assert activated.data["is_active"] is True
    assert client.post(f"{PLANS}{plan.id}/activate/").status_code == 409
    actions = set(AuditLog.objects.filter(entity_id=str(plan.pk)).values_list("action", flat=True))
    assert {"maintenance_plan.deactivated", "maintenance_plan.activated"} <= actions


def test_activating_an_old_plan_does_not_chase_missed_dates(auth_client, manager_a, equipment_a, make_plan, today):
    plan = make_plan(
        equipment_a,
        frequency="WEEKLY",
        start_date=today - timedelta(days=60),
        next_due_date=today - timedelta(days=53),
        is_active=False,
    )
    response = auth_client(manager_a).post(f"{PLANS}{plan.id}/activate/")
    assert response.status_code == 200
    assert response.data["next_due_date"] >= str(today)
    assert response.data["due_status"] in ("DUE", "UPCOMING")


def test_cannot_activate_plan_of_retired_equipment(auth_client, manager_a, equipment_a, make_plan, today):
    plan = make_plan(equipment_a, is_active=False)
    equipment_a.status = "RETIRED"
    equipment_a.retired_at = timezone.now()
    equipment_a.save()
    assert auth_client(manager_a).post(f"{PLANS}{plan.id}/activate/").status_code == 400


# --- list, filters ----------------------------------------------------------------------

@pytest.fixture
def fleet(equipment_a, make_plan, today, org_a):
    from equipment.models import Equipment

    second = Equipment.objects.create(organization=org_a, equipment_code="CMP-001", name="Compressor", location="Utility")
    d = timedelta
    return {
        "overdue": make_plan(equipment_a, title="Overdue plan", start_date=today - d(days=9), next_due_date=today - d(days=2), frequency="WEEKLY"),
        "due": make_plan(second, title="Due plan", start_date=today, next_due_date=today, frequency="DAILY"),
        "upcoming": make_plan(equipment_a, title="Upcoming plan", start_date=today + d(days=6), next_due_date=today + d(days=6)),
        "inactive": make_plan(second, title="Inactive plan", start_date=today - d(days=5), next_due_date=today - d(days=1), is_active=False),
        "second_equipment": second,
    }


def titles(response):
    return [row["title"] for row in response.data["results"]]


def test_list_is_paginated_and_ordered_by_due_date(auth_client, manager_a, fleet):
    response = auth_client(manager_a).get(PLANS)
    assert response.status_code == 200
    assert {"count", "next", "previous", "results"} <= set(response.data)
    assert titles(response) == ["Overdue plan", "Inactive plan", "Due plan", "Upcoming plan"]


@pytest.mark.parametrize(
    "status, expected",
    [
        ("OVERDUE", ["Overdue plan"]),
        ("DUE", ["Due plan"]),
        ("UPCOMING", ["Upcoming plan"]),
        ("INACTIVE", ["Inactive plan"]),  # nonaktif tidak pernah dihitung overdue/due/upcoming
    ],
)
def test_filter_by_status(auth_client, manager_a, fleet, status, expected):
    assert titles(auth_client(manager_a).get(PLANS, {"status": status})) == expected


def test_each_row_reports_its_due_status(auth_client, manager_a, fleet):
    rows = {r["title"]: r["due_status"] for r in auth_client(manager_a).get(PLANS).data["results"]}
    assert rows == {
        "Overdue plan": "OVERDUE",
        "Inactive plan": "INACTIVE",
        "Due plan": "DUE",
        "Upcoming plan": "UPCOMING",
    }


def test_invalid_status_filter_is_rejected(auth_client, manager_a, fleet):
    assert auth_client(manager_a).get(PLANS, {"status": "SOON"}).status_code == 400


def test_due_date_range_filters_are_inclusive(auth_client, manager_a, fleet, today):
    client = auth_client(manager_a)
    only_due_today = client.get(PLANS, {"due_after": str(today), "due_before": str(today)})
    assert titles(only_due_today) == ["Due plan"]


def test_filter_by_equipment_and_search(auth_client, manager_a, fleet, equipment_a):
    client = auth_client(manager_a)
    assert sorted(titles(client.get(PLANS, {"equipment": str(equipment_a.id)}))) == ["Overdue plan", "Upcoming plan"]
    assert titles(client.get(PLANS, {"search": "CMP-001"})) == ["Inactive plan", "Due plan"]
    assert titles(client.get(PLANS, {"search": "upcoming"})) == ["Upcoming plan"]


def test_ordering_by_unlisted_field_is_ignored(auth_client, manager_a, fleet):
    assert auth_client(manager_a).get(PLANS, {"ordering": "organization"}).status_code == 200


def test_list_shows_the_last_generated_work_order(auth_client, manager_a, fleet):
    generate_due_work_orders()
    rows = {r["title"]: r["last_work_order"] for r in auth_client(manager_a).get(PLANS).data["results"]}
    assert rows["Overdue plan"]["work_order_number"].startswith("WO-")
    assert rows["Overdue plan"]["status"] == "OPEN"
    assert rows["Due plan"] is not None
    assert rows["Upcoming plan"] is None  # belum jatuh tempo, belum ada work order


def test_list_query_count_does_not_grow_with_rows(auth_client, manager_a, fleet, django_assert_max_num_queries):
    with django_assert_max_num_queries(8):
        assert auth_client(manager_a).get(PLANS).status_code == 200


# --- calendar ---------------------------------------------------------------------------

def test_calendar_projects_future_due_dates(auth_client, manager_a, equipment_a, make_plan, today):
    make_plan(equipment_a, title="Weekly", frequency="WEEKLY", start_date=today, next_due_date=today)
    response = auth_client(manager_a).get(
        f"{PLANS}calendar/", {"start_date": str(today), "end_date": str(today + timedelta(days=15))}
    )
    assert response.status_code == 200
    assert [e["date"] for e in response.data] == [today, today + timedelta(days=7), today + timedelta(days=14)]
    assert response.data[0]["status"] == "DUE"
    assert response.data[1]["status"] == "UPCOMING"  # proyeksi, bukan work order


def test_calendar_excludes_inactive_plans_and_retired_equipment(auth_client, manager_a, fleet, today):
    response = auth_client(manager_a).get(
        f"{PLANS}calendar/", {"start_date": str(today - timedelta(days=3)), "end_date": str(today + timedelta(days=1))}
    )
    assert "Inactive plan" not in {e["title"] for e in response.data}

    fleet["second_equipment"].status = "RETIRED"
    fleet["second_equipment"].retired_at = timezone.now()
    fleet["second_equipment"].save()
    response = auth_client(manager_a).get(f"{PLANS}calendar/", {"start_date": str(today), "end_date": str(today + timedelta(days=1))})
    assert "Due plan" not in {e["title"] for e in response.data}


@pytest.mark.parametrize(
    "params",
    [
        {"start_date": "2026-12-01", "end_date": "2026-11-01"},  # terbalik
        {"start_date": "2026-01-01", "end_date": "2026-12-31"},  # lebih dari 92 hari
        {"start_date": "not-a-date"},
    ],
)
def test_calendar_validates_the_range(auth_client, manager_a, params):
    assert auth_client(manager_a).get(f"{PLANS}calendar/", params).status_code == 400