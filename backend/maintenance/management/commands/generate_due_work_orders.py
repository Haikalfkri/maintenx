from django.core.management.base import BaseCommand

from maintenance.services import generate_due_work_orders


class Command(BaseCommand):
    help = "Buat work order preventif untuk plan yang jatuh tempo (sama dengan task Celery harian)."

    def handle(self, *args, **options):
        result = generate_due_work_orders()
        self.stdout.write(
            f"created={result.created} already_generated={result.already_generated} "
            f"skipped={result.skipped} failed={result.failed}"
        )