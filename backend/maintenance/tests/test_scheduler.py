"""Penjadwal harian: membuat work order untuk plan jatuh tempo, aman diulang dan bersamaan."""
import threading
from datetime import date, datetime, timedelta, timezone as dt_timezone
from unittest import mock

import pytest
from django.conf import settings
from django.db import connection

from core.models import AuditLog
from maintenance import services
from maintenance.models import MaintenanceOccurrence
from maintenance.services import advance_plan_after_completion, generate_due_work_orders
from maintenance.tasks import generate_due_work_orders_task
from workorders.models import WorkOrder, WorkOrderHistory

pytestmark = pytest.mark.django_db

DUE = date(2026, 11, 11)
# 10:00 WIB (UTC+7) pada tanggal jatuh tempo
NOW = datetime(2026, 11, 11, 3, 0, tzinfo=dt_timezone.utc)


def utc(*args):
    return datetime(*args, tzinfo=dt_timezone.utc)


# --- membuat work order ------------------------------------------------------

def test_generates_a_preventive_work_order_for_a_due_plan(equipment_a, tech_a, make_plan):
    plan = make_plan(
        equipment_a,
        title="Check lubrication",
        description="Inspect and record.",
        next_due_date=DUE,
        start_date=DUE,
        default_technician=tech_a,
    )

    result = generate_due_work_orders(now=NOW)

    assert (result.created, result.already_generated, result.failed) == (1, 0, 0)
    work_order = WorkOrder.objects.get()
    assert work_order.work_order_number == "WO-00001"
    assert work_order.work_order_type == "PREVENTIVE"
    assert work_order.status == "ASSIGNED"
    assert work_order.assigned_technician == tech_a
    assert work_order.due_date == DUE
    assert work_order.equipment == equipment_a
    assert work_order.maintenance_plan == plan
    assert work_order.title == "Check lubrication"
    assert work_order.reported_by is None  # dibuat oleh sistem

    occurrence = MaintenanceOccurrence.objects.get()
    assert (occurrence.maintenance_plan, occurrence.scheduled_due_date) == (plan, DUE)
    assert occurrence.generated_work_order == work_order

    event = WorkOrderHistory.objects.get()
    assert (event.event_type, event.to_status, event.actor) == ("CREATED", "ASSIGNED", None)
    assert AuditLog.objects.filter(action="maintenance_plan.work_order_generated").count() == 1

    # next_due_date baru maju saat work order SELESAI (Phase 4), bukan saat dibuat
    plan.refresh_from_db()
    assert plan.next_due_date == DUE


def test_work_order_is_open_when_plan_has_no_default_technician(equipment_a, make_plan):
    make_plan(equipment_a, next_due_date=DUE, start_date=DUE)
    generate_due_work_orders(now=NOW)
    work_order = WorkOrder.objects.get()
    assert (work_order.status, work_order.assigned_technician) == ("OPEN", None)


def test_inactive_default_technician_falls_back_to_unassigned(equipment_a, tech_a, make_plan):
    make_plan(equipment_a, next_due_date=DUE, start_date=DUE, default_technician=tech_a)
    tech_a.is_active = False
    tech_a.save()
    generate_due_work_orders(now=NOW)
    work_order = WorkOrder.objects.get()
    assert (work_order.status, work_order.assigned_technician) == ("OPEN", None)


def test_upcoming_plan_is_not_generated(equipment_a, make_plan):
    make_plan(equipment_a, next_due_date=DUE + timedelta(days=1), start_date=DUE)
    result = generate_due_work_orders(now=NOW)
    assert (result.created, result.skipped) == (0, 1)
    assert not WorkOrder.objects.exists()


# --- idempotensi (inti Phase 3) -------------------------------------------------

def test_running_twice_creates_only_one_work_order(equipment_a, make_plan):
    make_plan(equipment_a, next_due_date=DUE, start_date=DUE)

    first = generate_due_work_orders(now=NOW)
    second = generate_due_work_orders(now=NOW)

    assert first.created == 1
    assert (second.created, second.already_generated) == (0, 1)
    assert WorkOrder.objects.count() == 1
    assert MaintenanceOccurrence.objects.count() == 1


def test_overdue_plan_generates_one_work_order_not_a_backlog(equipment_a, make_plan):
    # Mingguan sejak 1 Okt, tidak pernah diselesaikan. Task berjalan tiap hari.
    plan = make_plan(equipment_a, frequency="WEEKLY", start_date=date(2026, 10, 1), next_due_date=date(2026, 10, 1))

    for day in range(11, 16):
        generate_due_work_orders(now=utc(2026, 11, day, 3))

    assert WorkOrder.objects.count() == 1
    assert WorkOrder.objects.get().due_date == date(2026, 10, 1)
    plan.refresh_from_db()
    assert plan.next_due_date == date(2026, 10, 1)  # tetap, sampai work order-nya selesai


def test_unique_constraint_is_the_last_line_of_defense(equipment_a, make_plan, org_a):
    """Jika dua proses lolos dari pengecekan awal, database tetap menolak duplikat."""
    make_plan(equipment_a, next_due_date=DUE, start_date=DUE)
    generate_due_work_orders(now=NOW)
    org_a.refresh_from_db()
    sequence_before = org_a.work_order_sequence

    # Simulasi balapan: pengecekan awal 'tidak melihat' occurrence yang sudah ada
    with mock.patch.object(services, "_occurrence_exists", return_value=False):
        result = generate_due_work_orders(now=NOW)

    assert (result.created, result.already_generated) == (0, 1)
    assert WorkOrder.objects.count() == 1
    org_a.refresh_from_db()
    assert org_a.work_order_sequence == sequence_before  # nomor tidak 'bolong'


@pytest.mark.django_db(transaction=True)
def test_concurrent_runs_create_exactly_one_work_order(equipment_a, make_plan):
    """Beberapa worker menjalankan task BERSAMAAN (thread sungguhan, koneksi database terpisah)."""
    make_plan(equipment_a, next_due_date=DUE, start_date=DUE)
    results, errors = [], []
    barrier = threading.Barrier(4)

    def worker():
        try:
            barrier.wait()  # semua thread mulai serentak
            results.append(generate_due_work_orders(now=NOW))
        except Exception as exc:  # pragma: no cover
            errors.append(exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors
    assert sum(r.created for r in results) == 1
    assert sum(r.failed for r in results) == 0
    assert WorkOrder.objects.count() == 1
    assert MaintenanceOccurrence.objects.count() == 1


# --- plan mana yang diproses ----------------------------------------------------

def test_inactive_plan_is_ignored(equipment_a, make_plan):
    make_plan(equipment_a, next_due_date=DUE, start_date=DUE, is_active=False)
    assert generate_due_work_orders(now=NOW).created == 0


def test_plan_on_retired_equipment_is_ignored(equipment_a, make_plan):
    make_plan(equipment_a, next_due_date=DUE, start_date=DUE)
    equipment_a.status = "RETIRED"
    equipment_a.retired_at = NOW
    equipment_a.save()
    assert generate_due_work_orders(now=NOW).created == 0


def test_plan_of_inactive_organization_is_ignored(equipment_a, make_plan, org_a):
    make_plan(equipment_a, next_due_date=DUE, start_date=DUE)
    org_a.is_active = False
    org_a.save()
    assert generate_due_work_orders(now=NOW).created == 0


@pytest.mark.parametrize(
    "now, expected_created",
    [
        (utc(2026, 11, 10, 16, 59), 0),  # 23:59 WIB, masih 10 Nov di Jakarta
        (utc(2026, 11, 10, 17, 0), 1),  # 00:00 WIB, sudah 11 Nov di Jakarta
    ],
)
def test_due_date_uses_the_organization_timezone(equipment_a, make_plan, now, expected_created):
    make_plan(equipment_a, next_due_date=DUE, start_date=DUE)  # organisasi: Asia/Jakarta
    assert generate_due_work_orders(now=now).created == expected_created


def test_work_order_numbers_are_sequential_per_organization(
    equipment_a, equipment_b, make_plan, make_user, org_a
):
    second_equipment = type(equipment_a).objects.create(
        organization=org_a, equipment_code="PRS-1", name="Press", location="Hall B"
    )
    make_plan(equipment_a, title="A1", next_due_date=DUE, start_date=DUE)
    make_plan(second_equipment, title="A2", next_due_date=DUE, start_date=DUE)
    make_plan(equipment_b, title="B1", next_due_date=DUE, start_date=DUE)

    generate_due_work_orders(now=NOW)

    numbers_a = sorted(WorkOrder.objects.filter(organization=org_a).values_list("work_order_number", flat=True))
    numbers_b = list(WorkOrder.objects.filter(organization=equipment_b.organization).values_list("work_order_number", flat=True))
    assert numbers_a == ["WO-00001", "WO-00002"]
    assert numbers_b == ["WO-00001"]  # penomoran terpisah per organisasi


def test_one_failing_plan_does_not_block_the_others(equipment_a, make_plan, org_a):
    other = type(equipment_a).objects.create(
        organization=org_a, equipment_code="PRS-1", name="Press", location="Hall B"
    )
    make_plan(equipment_a, title="Broken", next_due_date=DUE, start_date=DUE)
    make_plan(other, title="Healthy", next_due_date=DUE, start_date=DUE)

    real_create = services.create_work_order

    def flaky(**kwargs):
        if kwargs["title"] == "Broken":
            raise RuntimeError("boom")
        return real_create(**kwargs)

    with mock.patch.object(services, "create_work_order", side_effect=flaky):
        result = generate_due_work_orders(now=NOW)

    assert (result.created, result.failed) == (1, 1)
    assert list(WorkOrder.objects.values_list("title", flat=True)) == ["Healthy"]


# --- memajukan jadwal setelah work order selesai ---------------------------------------

def test_advance_after_completion_moves_to_next_period(equipment_a, make_plan):
    plan = make_plan(equipment_a, frequency="WEEKLY", start_date=date(2026, 11, 3), next_due_date=date(2026, 11, 3))
    assert advance_plan_after_completion(plan=plan, scheduled_due_date=date(2026, 11, 3), today=date(2026, 11, 3))
    plan.refresh_from_db()
    assert plan.next_due_date == date(2026, 11, 10)


def test_advance_after_late_completion_skips_the_backlog(equipment_a, make_plan):
    plan = make_plan(equipment_a, frequency="WEEKLY", start_date=date(2026, 11, 3), next_due_date=date(2026, 11, 3))
    advance_plan_after_completion(plan=plan, scheduled_due_date=date(2026, 11, 3), today=date(2026, 11, 20))
    plan.refresh_from_db()
    assert plan.next_due_date == date(2026, 11, 24)


def test_advance_is_idempotent(equipment_a, make_plan):
    plan = make_plan(equipment_a, frequency="WEEKLY", start_date=date(2026, 11, 3), next_due_date=date(2026, 11, 3))
    assert advance_plan_after_completion(plan=plan, scheduled_due_date=date(2026, 11, 3), today=date(2026, 11, 3))
    # Panggilan kedua untuk jadwal yang sama: tidak ada yang berubah
    assert not advance_plan_after_completion(plan=plan, scheduled_due_date=date(2026, 11, 3), today=date(2026, 11, 3))
    plan.refresh_from_db()
    assert plan.next_due_date == date(2026, 11, 10)


def test_after_advancing_the_next_run_generates_the_next_occurrence(equipment_a, make_plan):
    plan = make_plan(equipment_a, frequency="DAILY", start_date=DUE, next_due_date=DUE)
    generate_due_work_orders(now=NOW)
    advance_plan_after_completion(plan=plan, scheduled_due_date=DUE, today=DUE)

    generate_due_work_orders(now=NOW + timedelta(days=1))

    assert WorkOrder.objects.count() == 2
    assert sorted(WorkOrder.objects.values_list("due_date", flat=True)) == [DUE, DUE + timedelta(days=1)]


# --- Celery -----------------------------------------------------------------------

def test_celery_task_runs_the_service(equipment_a, make_plan):
    yesterday = date.today() - timedelta(days=2)
    make_plan(equipment_a, start_date=yesterday, next_due_date=yesterday)

    result = generate_due_work_orders_task.apply().get()

    assert result == {"created": 1, "already_generated": 0, "skipped": 0, "failed": 0}


def test_daily_task_is_registered_in_celery_beat():
    from celery import current_app

    from config.celery import app  # noqa: F401  (memuat konfigurasi Celery)

    schedule = settings.CELERY_BEAT_SCHEDULE
    assert any(entry["task"] == "maintenance.generate_due_work_orders" for entry in schedule.values())
    assert "maintenance.generate_due_work_orders" in current_app.tasks