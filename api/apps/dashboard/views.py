from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.core.exceptions import UnauthorizedAccess
from apps.core.permissions import IsActiveUser

from .services import admin_dashboard, creator_dashboard


@extend_schema(responses=OpenApiTypes.OBJECT, tags=["dashboard"])
class AdminDashboardView(APIView):
    permission_classes = [IsActiveUser]

    def get(self, request):
        if request.user.role != User.Role.ADMIN:
            raise UnauthorizedAccess("Admin access is required.")
        return Response({"success": True, "data": admin_dashboard(request.user)})


@extend_schema(responses=OpenApiTypes.OBJECT, tags=["dashboard"])
class CreatorDashboardView(APIView):
    permission_classes = [IsActiveUser]

    def get(self, request):
        if not getattr(request.user, "creator_profile", None):
            raise UnauthorizedAccess("Creator profile is required.")
        return Response({"success": True, "data": creator_dashboard(request.user)})
