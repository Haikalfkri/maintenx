from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from core.mixins import OrganizationScopedMixin
from core.permissions import IsAdmin, IsAdminOrManager, IsOrganizationMember
from core.roles import Role

from .models import User
from .serializers import (
    CurrentUserSerializer,
    LoginSerializer,
    LogoutSerializer,
    TechnicianSerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer


class LogoutView(generics.GenericAPIView):
    """Cabut sesi dengan mem-blacklist refresh token."""

    serializer_class = LogoutSerializer
    # Cukup refresh token sebagai bukti, sehingga logout tetap bisa
    # walau access token sudah kedaluwarsa.
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            RefreshToken(serializer.validated_data["refresh"]).blacklist()
        except TokenError:
            return Response(
                {"refresh": ["Token is invalid or expired."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(generics.RetrieveAPIView):
    serializer_class = CurrentUserSerializer
    permission_classes = [IsOrganizationMember]

    def get_object(self):
        return self.request.user


class UserViewSet(
    OrganizationScopedMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = User.objects.select_related("organization")
    http_method_names = ["get", "post", "patch", "head", "options"]  # tanpa PUT/DELETE

    filterset_fields = ["role", "is_active"]
    search_fields = ["email", "first_name", "last_name"]
    ordering_fields = ["email", "created_at", "role"]  # allowlist
    ordering = ["email"]

    def get_permissions(self):
        if self.action == "technicians":
            return [IsAdminOrManager()]
        return [IsAdmin()]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ("update", "partial_update"):
            return UserUpdateSerializer
        if self.action == "technicians":
            return TechnicianSerializer
        return UserSerializer

    @action(detail=False, methods=["get"], pagination_class=None)
    def technicians(self, request):
        """Teknisi aktif di organisasi ini, untuk dropdown (tanpa paginasi)."""
        queryset = self.get_queryset().filter(role=Role.TECHNICIAN, is_active=True)
        queryset = queryset.order_by("first_name", "last_name")
        return Response(self.get_serializer(queryset, many=True).data)