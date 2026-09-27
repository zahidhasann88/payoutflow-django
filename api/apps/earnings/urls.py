from rest_framework.routers import SimpleRouter

from .views import EarningViewSet

router = SimpleRouter()
router.register("earnings", EarningViewSet, basename="earning")
