from django.urls import include, path
from rest_framework.routers import SimpleRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import LoginView, LogoutView, MeView, UserViewSet

router = SimpleRouter()
router.register("users", UserViewSet, basename="user")

urlpatterns = [
    path("auth/token/", LoginView.as_view(), name="token_obtain"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("", include(router.urls)),
]