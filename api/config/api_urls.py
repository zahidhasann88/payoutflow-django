from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.audit.urls import router as audit_router
from apps.creators.urls import router as creators_router
from apps.earnings.urls import router as earnings_router
from apps.jobs.urls import router as jobs_router
from apps.payouts.urls import router as payouts_router

router = DefaultRouter()
for app_router in (
    creators_router,
    jobs_router,
    earnings_router,
    payouts_router,
    audit_router,
):
    router.registry.extend(app_router.registry)

urlpatterns = [
    path("auth/", include("apps.accounts.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
    *router.urls,
]
