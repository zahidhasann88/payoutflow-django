from __future__ import annotations

from rest_framework import serializers

from apps.accounts.models import User
from apps.core.money import to_money

from .models import Job


class JobSerializer(serializers.ModelSerializer):
    creator_name = serializers.CharField(source="creator.display_name", read_only=True)
    earning_net = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            "id", "creator", "creator_name", "title", "description", "status",
            "base_amount", "surge_multiplier", "tip_amount",
            "completed_at", "created_at", "updated_at", "earning_net",
        ]
        read_only_fields = ["id", "status", "completed_at", "created_at", "updated_at"]
        extra_kwargs = {
            "base_amount": {"min_value": 0},
            "tip_amount": {"min_value": 0},
            "surge_multiplier": {"min_value": 1},
        }

    def get_earning_net(self, obj: Job) -> str | None:
        earning = getattr(obj, "earning", None)
        return str(to_money(earning.net_amount)) if earning else None

    def validate_surge_multiplier(self, value):
        if value > 10:
            raise serializers.ValidationError("Surge multiplier cannot exceed 10.00.")
        return to_money(value)

    def validate_base_amount(self, value):
        return to_money(value)

    def validate_tip_amount(self, value):
        return to_money(value)

    def validate_creator(self, creator):
        if creator.user.status == User.Status.SUSPENDED:
            raise serializers.ValidationError("This creator is suspended.")
        return creator


class JobUpdateSerializer(serializers.ModelSerializer):
    """Admin update — money fields locked once COMPLETED; status transitions validated."""

    class Meta:
        model = Job
        fields = ["title", "description", "base_amount", "surge_multiplier",
                  "tip_amount", "status"]
        extra_kwargs = {
            "base_amount": {"min_value": 0},
            "tip_amount": {"min_value": 0},
            "surge_multiplier": {"min_value": 1},
        }

    def validate(self, attrs):
        from .services import validate_status_transition

        instance: Job = self.instance
        new_status = attrs.get("status")
        if new_status and new_status != instance.status:
            validate_status_transition(instance.status, new_status)
            if new_status == Job.Status.COMPLETED and not attrs.get("completed_at"):
                attrs["_complete_via_service"] = True
        if instance.status == Job.Status.COMPLETED:
            money_fields = {"base_amount", "surge_multiplier", "tip_amount"}
            if money_fields & set(attrs):
                raise serializers.ValidationError(
                    "Money fields cannot change after a job is completed."
                )
        return attrs
