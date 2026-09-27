from django.urls import path

from .views import AdminDashboardView, CreatorDashboardView

urlpatterns = [
    path("admin/", AdminDashboardView.as_view(), name="dashboard-admin"),
    path("creator/", CreatorDashboardView.as_view(), name="dashboard-creator"),
]
