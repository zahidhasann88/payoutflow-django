from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True, default=None)
    user_name = serializers.CharField(source="user.name", read_only=True, default=None)

    class Meta:
        model = AuditLog
        fields = [
            "id", "user", "user_email", "user_name",
            "action", "entity_type", "entity_id", "metadata", "created_at",
        ]
