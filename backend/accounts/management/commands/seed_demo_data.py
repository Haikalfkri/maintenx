from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Organization, User
from core.roles import Role

DEMO_PASSWORD = "demo-password"  # hanya untuk data demo lokal

DEMO_DATA = [
    {
        "name": "Demo Manufacturing",
        "slug": "demo-manufacturing",
        "users": [
            ("admin@example.com", "Demo", "Admin", Role.ADMIN),
            ("manager@example.com", "Demo", "Manager", Role.MANAGER),
            ("technician@example.com", "Budi", "Teknisi", Role.TECHNICIAN),
            ("technician2@example.com", "Sari", "Teknisi", Role.TECHNICIAN),
        ],
    },
    {
        # Organisasi kedua, dipakai untuk menguji isolasi data antar organisasi
        "name": "Other Workshop",
        "slug": "other-workshop",
        "users": [
            ("manager@other.example.com", "Other", "Manager", Role.MANAGER),
        ],
    },
]


class Command(BaseCommand):
    help = "Buat organisasi dan user demo fiktif (aman dijalankan berulang kali)."

    @transaction.atomic
    def handle(self, *args, **options):
        for org_data in DEMO_DATA:
            org, org_created = Organization.objects.get_or_create(
                slug=org_data["slug"], defaults={"name": org_data["name"]}
            )
            self.stdout.write(f"{'Created' if org_created else 'Exists '} org: {org.name}")

            for email, first_name, last_name, role in org_data["users"]:
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        "first_name": first_name,
                        "last_name": last_name,
                        "organization": org,
                        "role": role,
                    },
                )
                if created:
                    user.set_password(DEMO_PASSWORD)
                    user.save(update_fields=["password"])
                self.stdout.write(f"  {'Created' if created else 'Exists '} user: {email} ({role})")

        self.stdout.write(self.style.SUCCESS(f"Selesai. Password demo: {DEMO_PASSWORD}"))