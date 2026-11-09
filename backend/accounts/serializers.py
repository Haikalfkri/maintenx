from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from core.roles import Role

from .models import Organization, User


class LoginSerializer(TokenObtainPairSerializer):
    """Login dengan email (tidak peka huruf besar/kecil) dan tolak organisasi nonaktif."""

    def validate(self, attrs):
        attrs[self.username_field] = attrs.get(self.username_field, "").strip().lower()
        data = super().validate(attrs)  # cek email + password + user aktif
        organization = self.user.organization
        if organization is None or not organization.is_active:
            # Pesan sama dengan kredensial salah, agar tidak membocorkan informasi
            raise AuthenticationFailed(
                self.error_messages["no_active_account"], "no_active_account"
            )
        return data


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class OrganizationSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ("id", "name", "timezone")
        read_only_fields = fields


class CurrentUserSerializer(serializers.ModelSerializer):
    organization = OrganizationSummarySerializer(read_only=True)

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "role", "organization")
        read_only_fields = fields


class UserSerializer(serializers.ModelSerializer):
    """Representasi user untuk list dan detail (read-only)."""

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "created_at",
        )
        read_only_fields = fields


class UserCreateSerializer(serializers.ModelSerializer):
    # Didefinisikan eksplisit agar validasi unik tidak peka huruf besar/kecil
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    role = serializers.ChoiceField(choices=Role.choices)

    class Meta:
        model = User
        fields = ("email", "password", "first_name", "last_name", "role")

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        # Organisasi SELALU dari user yang login, tidak pernah dari input klien
        organization = self.context["request"].user.organization
        return User.objects.create_user(organization=organization, **validated_data)

    def to_representation(self, instance):
        return UserSerializer(instance, context=self.context).data


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "role", "is_active")

    def validate(self, attrs):
        request_user = self.context["request"].user
        if self.instance == request_user:
            # Cegah admin mengunci dirinya sendiri
            if attrs.get("is_active") is False:
                raise serializers.ValidationError("You cannot deactivate your own account.")
            if "role" in attrs and attrs["role"] != Role.ADMIN:
                raise serializers.ValidationError("You cannot change your own role.")
        return attrs

    def to_representation(self, instance):
        return UserSerializer(instance, context=self.context).data


class TechnicianSerializer(serializers.ModelSerializer):
    """Data minimal untuk dropdown 'Assign technician'."""

    class Meta:
        model = User
        fields = ("id", "first_name", "last_name")
        read_only_fields = fields