"""Perhitungan jadwal berulang. Murni fungsi tanggal, tanpa database."""
from datetime import date

import pytest

from maintenance.recurrence import (
    DAILY,
    DUE,
    INACTIVE,
    MONTHLY,
    OVERDUE,
    UPCOMING,
    WEEKLY,
    add_months,
    due_status,
    first_due_date,
    next_due_date_after,
    occurrence,
    occurrence_on_or_after,
)

D = date


# --- add_months ---------------------------------------------------------------

@pytest.mark.parametrize(
    "start, months, expected",
    [
        (D(2026, 1, 15), 1, D(2026, 2, 15)),
        (D(2026, 1, 31), 1, D(2026, 2, 28)),  # Februari tidak punya tanggal 31
        (D(2028, 1, 31), 1, D(2028, 2, 29)),  # tahun kabisat
        (D(2026, 3, 31), 1, D(2026, 4, 30)),
        (D(2026, 11, 15), 2, D(2027, 1, 15)),  # lewat pergantian tahun
        (D(2026, 12, 31), 12, D(2027, 12, 31)),
    ],
)
def test_add_months(start, months, expected):
    assert add_months(start, months) == expected


def test_monthly_schedule_is_anchored_to_start_date_and_does_not_drift():
    start = D(2026, 1, 31)
    dates = [occurrence(start, MONTHLY, 1, n) for n in range(5)]
    # Bukan 31 Jan, 28 Feb, 28 Mar, ... melainkan kembali ke tanggal 31 bila ada
    assert dates == [D(2026, 1, 31), D(2026, 2, 28), D(2026, 3, 31), D(2026, 4, 30), D(2026, 5, 31)]


def test_unsupported_frequency_is_rejected():
    with pytest.raises(ValueError):
        occurrence(D(2026, 1, 1), "YEARLY", 1, 1)


# --- occurrence_on_or_after ---------------------------------------------------------

@pytest.mark.parametrize(
    "frequency, start, target, expected",
    [
        (DAILY, D(2026, 11, 1), D(2026, 11, 10), D(2026, 11, 10)),
        (DAILY, D(2026, 11, 1), D(2026, 10, 1), D(2026, 11, 1)),  # target sebelum start
        (WEEKLY, D(2026, 11, 3), D(2026, 11, 3), D(2026, 11, 3)),  # tepat di jadwal
        (WEEKLY, D(2026, 11, 3), D(2026, 11, 4), D(2026, 11, 10)),
        (WEEKLY, D(2026, 11, 3), D(2026, 11, 10), D(2026, 11, 10)),
        (WEEKLY, D(2026, 11, 3), D(2026, 11, 11), D(2026, 11, 17)),
        (MONTHLY, D(2026, 11, 3), D(2026, 11, 4), D(2026, 12, 3)),
        (MONTHLY, D(2026, 11, 3), D(2027, 3, 3), D(2027, 3, 3)),
        (MONTHLY, D(2026, 1, 31), D(2026, 3, 1), D(2026, 3, 31)),
        (MONTHLY, D(2026, 1, 31), D(2026, 2, 28), D(2026, 2, 28)),
    ],
)
def test_occurrence_on_or_after(frequency, start, target, expected):
    assert occurrence_on_or_after(start, frequency, 1, target) == expected


# --- first_due_date ------------------------------------------------------------------

def test_first_due_date_for_future_start_is_the_start_date():
    assert first_due_date(D(2026, 12, 1), MONTHLY, 1, today=D(2026, 11, 11)) == D(2026, 12, 1)


def test_first_due_date_when_start_is_today_is_today():
    assert first_due_date(D(2026, 11, 11), WEEKLY, 1, today=D(2026, 11, 11)) == D(2026, 11, 11)


def test_first_due_date_for_past_start_skips_to_the_next_occurrence():
    # Mulai 10 hari lalu, mingguan: jangan langsung overdue untuk tanggal yang sudah lewat
    assert first_due_date(D(2026, 11, 1), WEEKLY, 1, today=D(2026, 11, 11)) == D(2026, 11, 15)


# --- next_due_date_after --------------------------------------------------------------

def test_completed_on_time_advances_one_period():
    assert next_due_date_after(D(2026, 11, 3), WEEKLY, 1, D(2026, 11, 3), today=D(2026, 11, 3)) == D(2026, 11, 10)


def test_completed_early_still_moves_past_the_scheduled_date():
    assert next_due_date_after(D(2026, 11, 3), WEEKLY, 1, D(2026, 11, 10), today=D(2026, 11, 5)) == D(2026, 11, 17)


def test_completed_late_skips_missed_periods_instead_of_creating_a_backlog():
    # Jatuh tempo 3 Nov, baru selesai 20 Nov: 10 Nov dan 17 Nov dilewati, bukan dibuatkan work order
    result = next_due_date_after(D(2026, 11, 3), WEEKLY, 1, D(2026, 11, 3), today=D(2026, 11, 20))
    assert result == D(2026, 11, 24)


def test_next_due_date_is_always_in_the_future():
    result = next_due_date_after(D(2026, 1, 1), DAILY, 1, D(2026, 1, 1), today=D(2026, 11, 11))
    assert result == D(2026, 11, 12)


def test_monthly_next_due_after_month_end():
    result = next_due_date_after(D(2026, 1, 31), MONTHLY, 1, D(2026, 1, 31), today=D(2026, 1, 31))
    assert result == D(2026, 2, 28)
    result = next_due_date_after(D(2026, 1, 31), MONTHLY, 1, D(2026, 2, 28), today=D(2026, 2, 28))
    assert result == D(2026, 3, 31)  # kembali ke tanggal 31


# --- due_status ----------------------------------------------------------------------

TODAY = D(2026, 11, 11)


@pytest.mark.parametrize(
    "next_due, active, expected",
    [
        (D(2026, 11, 10), True, OVERDUE),
        (D(2026, 11, 11), True, DUE),
        (D(2026, 11, 12), True, UPCOMING),
        (D(2026, 11, 10), False, INACTIVE),  # nonaktif selalu INACTIVE, walau tanggalnya lewat
        (D(2026, 12, 1), False, INACTIVE),
    ],
)
def test_due_status(next_due, active, expected):
    assert due_status(next_due, active, TODAY) == expected