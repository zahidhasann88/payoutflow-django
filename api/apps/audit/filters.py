from django_filters import rest_framework as df

from .models import AuditLog


class AuditLogFilter(df.FilterSet):
    created_after = df.IsoDateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = df.IsoDateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = AuditLog
        fields = ["action", "entity_type", "entity_id", "user", "created_after", "created_before"]
