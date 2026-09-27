from rest_framework import viewsets
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin

from apps.core.permissions import IsAdmin

from .filters import AuditLogFilter
from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(ListModelMixin, RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = AuditLog.objects.select_related("user").all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdmin]
    filterset_class = AuditLogFilter
    search_fields = ["action", "entity_type", "entity_id", "user__email", "user__name"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]
