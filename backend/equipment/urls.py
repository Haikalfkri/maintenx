from rest_framework.routers import SimpleRouter

from .views import EquipmentCategoryViewSet, EquipmentViewSet

router = SimpleRouter()
router.register("equipment-categories", EquipmentCategoryViewSet, basename="equipment-category")
router.register("equipment", EquipmentViewSet, basename="equipment")

urlpatterns = router.urls