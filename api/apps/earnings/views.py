from __future__ import annotations

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response

from apps.accounts.models import User
from apps.core.permissions import IsAdmin, IsAdminOrSelf

from .filters import EarningFilter
from .models import Earning
from .serializers import AdjustmentSerializer, EarningSerializer
from .services import add_adjustment


class EarningViewSet(ListModelMixin, RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = EarningSerializer
    permission_classes = [IsAdminOrSelf]
    filterset_class = EarningFilter
    search_fields = ["job__title"]
    ordering_fields = ["created_at", "gross_amount", "net_amount"]
    ordering = ["-created_at"]

    queryset = Earning.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Earning.objects.none()
        qs = Earning.objects.select_related(
            "job", "creator", "creator__user", "payout", "payout__payout_batch"
        ).prefetch_related("adjustments", "adjustments__created_by")
        if self.request.user.role == User.Role.CREATOR:
            profile = getattr(self.request.user, "creator_profile", None)
            qs = qs.filter(creator=profile) if profile else qs.none()
        return qs

    @action(detail=True, methods=["post"], permission_classes=[IsAdmin])
    def adjustments(self, request, pk=None):
        """POST /api/earnings/:id/adjustments/ — admin adds a signed adjustment."""
        earning = self.get_object()
        serializer = AdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        adjustment = add_adjustment(
            earning=earning,
            amount=serializer.validated_data["amount"],
            reason=serializer.validated_data["reason"],
            actor=request.user,
        )
        return Response(AdjustmentSerializer(adjustment).data, status=201)
