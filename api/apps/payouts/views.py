from __future__ import annotations

from django.db.models import Count, Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response

from apps.accounts.models import User
from apps.core.permissions import IsActiveUser, IsAdmin, IsAdminOrSelf

from .filters import CreatorPayoutFilter, PayoutBatchFilter
from .models import CreatorPayout, PayoutBatch, PayoutRule
from .serializers import (
    CreatorPayoutSerializer,
    GenerateBatchSerializer,
    PayoutBatchDetailSerializer,
    PayoutBatchSerializer,
    PayoutRuleSerializer,
)
from .services import generate_payout_batch, last_completed_week, process_payout_batch


class PayoutRuleViewSet(viewsets.ModelViewSet):
    """Read: any authenticated user. Write: admins only."""

    queryset = PayoutRule.objects.all()
    serializer_class = PayoutRuleSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]
    search_fields = ["name"]
    ordering_fields = ["created_at", "name"]

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [IsActiveUser()]
        return [IsAdmin()]

    def destroy(self, request, *args, **kwargs):
        return Response({"success": False, "message": "Deleting payout rules is disabled.",
                         "code": "METHOD_NOT_ALLOWED"}, status=405)


class PayoutBatchViewSet(ListModelMixin, RetrieveModelMixin, viewsets.GenericViewSet):
    """Admin-only batch listing plus generate/process actions."""

    queryset = PayoutBatch.objects.all()
    serializer_class = PayoutBatchSerializer
    permission_classes = [IsAdmin]
    filterset_class = PayoutBatchFilter
    ordering_fields = ["period_start", "period_end", "created_at", "net_amount"]
    ordering = ["-period_end", "-created_at"]

    def get_queryset(self):
        """Annotate payout counts so list responses stay at one query."""
        qs = PayoutBatch.objects.annotate(
            payout_count_annotated=Count("payouts", distinct=True),
            paid_count_annotated=Count(
                "payouts", filter=Q(payouts__status=CreatorPayout.Status.PAID),
                distinct=True,
            ),
            failed_count_annotated=Count(
                "payouts", filter=Q(payouts__status=CreatorPayout.Status.FAILED),
                distinct=True,
            ),
        )
        if self.action == "retrieve":
            qs = qs.prefetch_related("payouts__creator__user")
        return qs

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PayoutBatchDetailSerializer
        return PayoutBatchSerializer

    @action(detail=False, methods=["get"], url_path="next-period")
    def next_period(self, request):
        """Helper for the UI: the period the Generate button would target."""
        start, end = last_completed_week()
        exists = PayoutBatch.objects.filter(period_start=start, period_end=end).exists()
        return Response({"success": True,
                         "data": {"period_start": start, "period_end": end,
                                  "already_generated": exists}})

    @action(detail=False, methods=["post"])
    def generate(self, request):
        """POST /api/payout-batches/generate/ — manual admin trigger."""
        serializer = GenerateBatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        batch = generate_payout_batch(
            period_start=serializer.validated_data.get("period_start"),
            period_end=serializer.validated_data.get("period_end"),
            actor=request.user,
        )
        return Response(PayoutBatchDetailSerializer(batch).data, status=201)

    @action(detail=True, methods=["post"])
    def process(self, request, pk=None):
        """POST /api/payout-batches/:id/process/ — simulated processing."""
        batch = self.get_object()
        failure_rate = request.data.get("failure_rate")
        if failure_rate is not None:
            failure_rate = max(0.0, min(1.0, float(failure_rate)))
        batch = process_payout_batch(batch, actor=request.user, failure_rate=failure_rate)
        return Response(PayoutBatchDetailSerializer(batch).data)


class CreatorPayoutViewSet(ListModelMixin, RetrieveModelMixin, viewsets.GenericViewSet):
    """Payout history — admins see all, creators see only their own."""

    serializer_class = CreatorPayoutSerializer
    permission_classes = [IsAdminOrSelf]
    filterset_class = CreatorPayoutFilter
    ordering_fields = ["created_at", "net_amount", "processed_at"]
    ordering = ["-created_at"]

    queryset = CreatorPayout.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return CreatorPayout.objects.none()
        qs = CreatorPayout.objects.select_related(
            "creator", "creator__user", "payout_batch"
        )
        if self.request.user.role == User.Role.CREATOR:
            profile = getattr(self.request.user, "creator_profile", None)
            qs = qs.filter(creator=profile) if profile else qs.none()
        return qs
