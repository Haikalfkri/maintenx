"""
Perhitungan jadwal berulang. Murni fungsi tanggal: tanpa database dan tanpa Django,
sehingga mudah diuji dan dipahami.

Semua tanggal jatuh tempo dihitung dari `start_date` (anchor), bukan dari tanggal
jatuh tempo sebelumnya. Dengan begitu jadwal bulanan tidak 'melorot':
start 31 Jan -> 31 Jan, 28 Feb, 31 Mar, 30 Apr (bukan 28 Mar).
"""
import calendar
from datetime import date, timedelta

DAILY = "DAILY"
WEEKLY = "WEEKLY"
MONTHLY = "MONTHLY"

# Status jatuh tempo sebuah plan
UPCOMING = "UPCOMING"
DUE = "DUE"
OVERDUE = "OVERDUE"
INACTIVE = "INACTIVE"

_DAYS_PER_STEP = {DAILY: 1, WEEKLY: 7}


def add_months(start: date, months: int) -> date:
    """Tambah bulan; jika hari tidak ada di bulan tujuan, pakai hari terakhir bulan itu."""
    index = start.year * 12 + (start.month - 1) + months
    year, month_zero_based = divmod(index, 12)
    month = month_zero_based + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def occurrence(start_date: date, frequency: str, interval: int, n: int) -> date:
    """Tanggal jatuh tempo ke-n (n=0 adalah start_date)."""
    if frequency == MONTHLY:
        return add_months(start_date, n * interval)
    if frequency in _DAYS_PER_STEP:
        return start_date + timedelta(days=_DAYS_PER_STEP[frequency] * interval * n)
    raise ValueError(f"Unsupported frequency: {frequency!r}")


def occurrence_on_or_after(start_date: date, frequency: str, interval: int, target: date) -> date:
    """Tanggal jatuh tempo pertama yang sama dengan atau setelah `target`."""
    if target <= start_date:
        return start_date

    if frequency == MONTHLY:
        months_between = (target.year - start_date.year) * 12 + target.month - start_date.month
        n = max(0, months_between // interval - 1)  # mulai sedikit sebelum target, lalu maju
        while occurrence(start_date, frequency, interval, n) < target:
            n += 1
        return occurrence(start_date, frequency, interval, n)

    if frequency in _DAYS_PER_STEP:
        step = _DAYS_PER_STEP[frequency] * interval
        n = -(-(target - start_date).days // step)  # pembulatan ke atas
        return start_date + timedelta(days=n * step)

    raise ValueError(f"Unsupported frequency: {frequency!r}")


def first_due_date(start_date: date, frequency: str, interval: int, today: date) -> date:
    """
    Jatuh tempo pertama untuk plan baru (atau plan yang diaktifkan kembali).
    Jika start_date sudah lewat, langsung ke jadwal berikutnya yang belum lewat,
    agar tidak langsung 'overdue' untuk tanggal yang sebenarnya tidak pernah direncanakan.
    """
    return occurrence_on_or_after(start_date, frequency, interval, max(start_date, today))


def next_due_date_after(
    start_date: date, frequency: str, interval: int, scheduled_due: date, today: date
) -> date:
    """
    Jatuh tempo berikutnya setelah satu jadwal selesai: jadwal pertama yang SETELAH
    tanggal jatuh tempo itu DAN setelah hari ini. Jadwal yang terlewat tidak dibuatkan
    work order susulan (tidak ada backlog).
    """
    reference = max(scheduled_due, today)
    return occurrence_on_or_after(start_date, frequency, interval, reference + timedelta(days=1))


def due_status(next_due_date: date, is_active: bool, today: date) -> str:
    if not is_active:
        return INACTIVE
    if next_due_date < today:
        return OVERDUE
    if next_due_date == today:
        return DUE
    return UPCOMING