from dataclasses import asdict

from celery import shared_task

from . import services


@shared_task(name="maintenance.generate_due_work_orders")
def generate_due_work_orders_task() -> dict:
    """Entry point Celery: hanya memanggil service. Aman dijalankan ulang (retry)."""
    return asdict(services.generate_due_work_orders())