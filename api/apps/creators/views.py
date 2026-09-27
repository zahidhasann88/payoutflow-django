from __future__ import annotations

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import User
from apps.core.exceptions import UnauthorizedAccess
from apps.core.permissions import IsAdminOrSelf

from .filters import CreatorFilter
from .models import Creator
from .serializers import CreatorCreateSerializer, CreatorSerializer, CreatorUpdateSerializer
from .services import create_creator, update_creator


class CreatorViewSet(viewsets.ModelViewSet):
    serializer_class = CreatorSerializer
    permission_classes = [IsAdminOrSelf]
    filterset_class = CreatorFilter
    search_fields = ["display_name", "user__email", "user__name", "phone"]
    ordering_fields = ["created_at", "display_name"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    queryset = Creator.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Creator.objects.none()
        qs = Creator.objects.select_related("user").filter(user__isnull=False)
        if self.request.user.role == User.Role.CREATOR:
            qs = qs.filter(user=self.request.user)
        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return CreatorCreateSerializer
        if self.action in {"partial_update", "update"}:
            return CreatorUpdateSerializer
        return CreatorSerializer

    def create(self, request, *args, **kwargs):
        if request.user.role != User.Role.ADMIN:
            raise UnauthorizedAccess("Only admins can create creators.")
        serializer = CreatorCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        creator = create_creator(
            actor=request.user,
            email=serializer.validated_data["email"],
            name=serializer.validated_data["name"],
            password=serializer.validated_data["password"],
            profile_fields=serializer.profile_fields,
        )
        return Response(CreatorSerializer(creator).data, status=201)

    def partial_update(self, request, *args, **kwargs):
        creator: Creator = self.get_object()
        is_self = creator.user == request.user
        if is_self:
            data = {k: v for k, v in request.data.items() if k in
                    {"display_name", "phone", "payout_method", "payout_account"}}
        else:
            data = request.data
        serializer = CreatorUpdateSerializer(data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        creator = update_creator(
            actor=request.user, creator=creator,
            profile_fields=serializer.profile_fields,
            user_fields=serializer.user_fields if not is_self else None,
        )
        return Response(CreatorSerializer(creator).data)

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        """Convenience endpoint returning the calling creator's profile."""
        profile = getattr(request.user, "creator_profile", None)
        if profile is None:
            raise UnauthorizedAccess("This account has no creator profile.")
        return Response({"success": True, "data": CreatorSerializer(profile).data})
