import uuid
from decimal import Decimal

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin
)

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from core.roles import Role

class Organization(models.Model):
    """Tenant. Semua data bisnis menempel ke satu organisasi."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=100, unique=True)
    timezone = models.CharField(max_length=64, default="Asia/Jakarta")
    assumed_operating_hours_per_day = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("8.00"),
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Dipakai untuk estimasi MTBF."
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required.")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)  # selalu di-hash, tidak pernah plaintext
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", Role.ADMIN)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=25, blank=True)
    last_name = models.CharField(max_length=25, blank=True)
    # protect organisasi tidak bisa dihapus jika masih ada user
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="users",
        null=True,
        blank=True
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.TECHNICIAN)
    is_active = models.BooleanField(default=True)
    # is_staff = akses Django admin, TERPISAH dari role Admin MaintenX
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        ordering = ["email"]
        constraints = [
            # user wajib punya organisasi.
            # hanya superuser yang boleh tanpa organisasi.
            models.CheckConstraint(
                condition=Q(is_superuser=True) | Q(organization__isnull=False),
                name="user_requires_organization_unless_superuser",
            ),
        ]

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email