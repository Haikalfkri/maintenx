from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import Organization, User
from core.dates import organization_today
from core.roles import Role
from equipment.models import Equipment, EquipmentCategory, EquipmentStatus
from maintenance.models import MaintenancePlan

DEMO_PASSWORD = "demo-password"  # hanya untuk data demo lokal

# Plan demo: (kode equipment, judul, frekuensi, start_date, next_due_date, aktif, teknisi)
# Tanggal berupa selisih hari dari 'hari ini' agar status berbeda-beda (upcoming/due/overdue/inactive).
DEMO_PLANS = [
    ("CNC-001", "Monthly lubrication inspection", "MONTHLY", 7, 7, True, "technician@example.com"),
    ("CMP-001", "Weekly compressor drain check", "WEEKLY", -10, -3, True, "technician@example.com"),
    ("CNV-001", "Daily conveyor belt check", "DAILY", 0, 0, True, "technician2@example.com"),
    ("GEN-001", "Monthly generator test run", "MONTHLY", 20, 20, True, None),
    ("PRS-001", "Weekly hydraulic oil check", "WEEKLY", -20, -6, False, None),
]


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
        "categories": ["CNC Machine", "Compressor", "Conveyor", "Generator", "Press"],
        # (kode, nama, kategori, lokasi, status, pabrikan, model, serial)
        "equipment": [
            ("CNC-001", "CNC Milling Machine", "CNC Machine", "Production Hall A",
             EquipmentStatus.OPERATIONAL, "Example Industrial", "MX-200", "SN-CNC-1001"),
            ("CNC-002", "CNC Lathe", "CNC Machine", "Production Hall A",
             EquipmentStatus.UNDER_MAINTENANCE, "Example Industrial", "LX-100", "SN-CNC-1002"),
            ("CMP-001", "Screw Air Compressor", "Compressor", "Utility Room",
             EquipmentStatus.OPERATIONAL, "AirWorks", "AW-75", "SN-CMP-2001"),
            ("CMP-002", "Backup Air Compressor", "Compressor", "Utility Room",
             EquipmentStatus.OUT_OF_SERVICE, "AirWorks", "AW-50", "SN-CMP-2002"),
            ("CNV-001", "Packing Line Conveyor", "Conveyor", "Packing Area",
             EquipmentStatus.OPERATIONAL, "BeltCo", "BC-300", "SN-CNV-3001"),
            ("GEN-001", "Standby Generator", "Generator", "Power House",
             EquipmentStatus.OPERATIONAL, "PowerGen", "PG-500", "SN-GEN-4001"),
            ("PRS-001", "Hydraulic Press", "Press", "Production Hall B",
             EquipmentStatus.OPERATIONAL, "PressTech", "HP-80", "SN-PRS-5001"),
            ("PRS-002", "Old Stamping Press", "Press", "Production Hall B",
             EquipmentStatus.RETIRED, "PressTech", "SP-20", "SN-PRS-5002"),
        ],
    },
    {
        # Organisasi kedua, dipakai untuk menguji isolasi data antar organisasi
        "name": "Other Workshop",
        "slug": "other-workshop",
        "users": [
            ("manager@other.example.com", "Other", "Manager", Role.MANAGER),
        ],
        "categories": ["Welding"],
        "equipment": [
            # Kode sama dengan organisasi lain: sah karena unik per organisasi
            ("CNC-001", "Welding Robot", "Welding", "Workshop 1",
             EquipmentStatus.OPERATIONAL, "WeldCo", "WR-10", "SN-WLD-9001"),
        ],
    },
]


class Command(BaseCommand):
    help = "Buat organisasi, user, dan equipment demo fiktif (aman dijalankan berulang kali)."

    @transaction.atomic
    def handle(self, *args, **options):
        for org_data in DEMO_DATA:
            org, created = Organization.objects.get_or_create(
                slug=org_data["slug"], defaults={"name": org_data["name"]}
            )
            self.stdout.write(f"{'Created' if created else 'Exists '} org: {org.name}")

            self._seed_users(org, org_data["users"])
            categories = self._seed_categories(org, org_data["categories"])
            self._seed_equipment(org, categories, org_data["equipment"])
            if org.slug == "demo-manufacturing":
                self._seed_plans(org)

        self.stdout.write(self.style.SUCCESS(f"Selesai. Password demo: {DEMO_PASSWORD}"))

    def _seed_users(self, org, users):
        for email, first_name, last_name, role in users:
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

    def _seed_categories(self, org, names):
        categories = {}
        for name in names:
            categories[name], _ = EquipmentCategory.objects.get_or_create(
                organization=org, name=name
            )
        return categories

    def _seed_equipment(self, org, categories, items):
        for code, name, category, location, status, maker, model, serial in items:
            _, created = Equipment.objects.get_or_create(
                organization=org,
                equipment_code=code,
                defaults={
                    "name": name,
                    "category": categories[category],
                    "location": location,
                    "status": status,
                    "manufacturer": maker,
                    "model_number": model,
                    "serial_number": serial,
                    "retired_at": timezone.now() if status == EquipmentStatus.RETIRED else None,
                },
            )
            self.stdout.write(f"  {'Created' if created else 'Exists '} equipment: {code}")

    def _seed_plans(self, org):
        today = organization_today(org)
        for code, title, frequency, start_offset, due_offset, active, technician in DEMO_PLANS:
            _, created = MaintenancePlan.objects.get_or_create(
                organization=org,
                equipment=Equipment.objects.get(organization=org, equipment_code=code),
                title=title,
                defaults={
                    "frequency": frequency,
                    "start_date": today + timedelta(days=start_offset),
                    "next_due_date": today + timedelta(days=due_offset),
                    "is_active": active,
                    "default_technician": (
                        User.objects.get(email=technician) if technician else None
                    ),
                },
            )
            self.stdout.write(f"  {'Created' if created else 'Exists '} plan: {title}")