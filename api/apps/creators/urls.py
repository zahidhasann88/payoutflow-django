from rest_framework.routers import SimpleRouter

from .views import CreatorViewSet

router = SimpleRouter()
router.register("creators", CreatorViewSet, basename="creator")
