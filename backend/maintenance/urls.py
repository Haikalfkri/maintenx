from rest_framework.routers import SimpleRouter

from .views import MaintenancePlanViewSet

router = SimpleRouter()
router.register("maintenance-plans", MaintenancePlanViewSet, basename="maintenance-plan")

urlpatterns = router.urls