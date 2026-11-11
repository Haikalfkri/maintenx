from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.utils import timezone

def organization_today(organization, now: datetime | None = None) -> date:
    """
    Tanggal 'hari ini' menurut timezone organisasi.

    Semua timestamp disimpan dalam UTC, tetapi 'jatuh tempo hari ini' harus dihitung
    berdasarkan kalender lokal organisasi (Asia/Jakarta untuk organisasi demo).
    `now` bisa diisi agar logika waktu mudah diuji.
    """
    now = now or timezone.now()
    try:
        tz = ZoneInfo(organization.timezone)
    except (ZoneInfoNotFoundError, ValueError):
        tz = ZoneInfo("UTC")
    return now.astimezone(tz).date()