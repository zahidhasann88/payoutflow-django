from rest_framework import serializers

from .models import Adjustment, Earning


class AdjustmentSerializer(serializers.ModelSerializer):
    created_by_email = serializers.CharField(
        source="created_by.email", read_only=True, default=None
    )

    class Meta:
        model = Adjustment
        fields = ["id", "earning", "amount", "reason", "created_by",
                  "created_by_email", "created_at"]
        read_only_fields = ["id", "earning", "created_by", "created_at"]


class EarningSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source="job.title", read_only=True)
    job_id = serializers.PrimaryKeyRelatedField(source="job", read_only=True)
    creator_name = serializers.CharField(source="creator.display_name", read_only=True)
    payout_id = serializers.PrimaryKeyRelatedField(source="payout", read_only=True)
    adjustments = AdjustmentSerializer(many=True, read_only=True)

    class Meta:
        model = Earning
        fields = [
            "id", "job", "job_id", "job_title", "creator", "creator_name",
            "base_amount", "surge_amount", "tip_amount", "gross_amount",
            "platform_fee", "fee_percentage_applied", "adjustment_amount",
            "net_amount", "payout_status", "payout_id", "adjustments",
            "created_at", "updated_at",
        ]
        read_only_fields = fields
