from __future__ import annotations

from django.db import IntegrityError, transaction
from rest_framework import serializers

from apps.audit.services import AuditAction, record_audit
from apps.core.db import LockKey, advisory_lock
from apps.core.error_codes import ErrorCode
from apps.core.exceptions import BusinessError
from apps.core.money import to_money

from .models import CreatorPayout, PayoutBatch, PayoutRule


class PayoutRuleSerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField(required=False)

    class Meta:
        model = PayoutRule
        fields = [
            "id", "name", "platform_fee_percentage", "minimum_payout",
            "payout_frequency", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_platform_fee_percentage(self, value):
        return to_money(value)

    def validate_minimum_payout(self, value):
        return to_money(value)

    def validate_payout_frequency(self, value):
        if value != PayoutRule.Frequency.WEEKLY:
            raise serializers.ValidationError("Only WEEKLY payouts are supported.")
        return value

    def save(self, **kwargs):
        """
        Persist the rule, keeping the single-active invariant.

        Activation is serialized with an advisory lock rather than a row lock:
        two transactions racing to become the active rule would each lock the
        *currently* active row, both see it deactivated once the lock released,
        and then collide on the partial unique index. With the advisory lock the
        activations simply queue, so concurrent switches both succeed and the
        last one wins. The whole switch is one transaction: either the new rule
        is active and the old one is not, or nothing changed.
        """
        with transaction.atomic():
            making_active = bool(self.validated_data.get("is_active"))
            if not making_active:
                return self._save_and_audit(**kwargs)

            with advisory_lock(LockKey.PAYOUT_RULE_ACTIVATION):
                others = PayoutRule.objects.filter(is_active=True)
                if self.instance is not None:
                    others = others.exclude(pk=self.instance.pk)
                others.update(is_active=False)
                try:
                    return self._save_and_audit(**kwargs)
                except IntegrityError as exc:
                    raise BusinessError(
                        "Another payout rule was activated at the same time. "
                        "Reload and try again.",
                        code=ErrorCode.PAYOUT_RULE_ACTIVATION_CONFLICT,
                        status_code=409,
                    ) from exc

    def _save_and_audit(self, **kwargs) -> PayoutRule:
        rule = super().save(**kwargs)
        actor = getattr(self.context.get("request"), "user", None)
        record_audit(actor, AuditAction.PAYOUT_RULE_CHANGED, "PayoutRule", rule.id,
                     metadata={"name": rule.name,
                               "platform_fee_percentage": rule.platform_fee_percentage,
                               "minimum_payout": rule.minimum_payout,
                               "is_active": rule.is_active})
        return rule


class CreatorPayoutSerializer(serializers.ModelSerializer):
    creator_name = serializers.CharField(source="creator.display_name", read_only=True)
    period_start = serializers.DateField(source="payout_batch.period_start", read_only=True)
    period_end = serializers.DateField(source="payout_batch.period_end", read_only=True)
    batch_status = serializers.CharField(source="payout_batch.status", read_only=True)

    class Meta:
        model = CreatorPayout
        fields = [
            "id", "payout_batch", "creator", "creator_name",
            "period_start", "period_end", "batch_status",
            "gross_amount", "platform_fee", "adjustments", "net_amount",
            "earning_count", "status", "processed_at", "failure_reason",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class PayoutBatchSerializer(serializers.ModelSerializer):
    payout_count = serializers.SerializerMethodField()
    paid_count = serializers.SerializerMethodField()
    failed_count = serializers.SerializerMethodField()
    rule_name = serializers.SerializerMethodField()
    fee_percentage = serializers.SerializerMethodField()

    class Meta:
        model = PayoutBatch
        fields = [
            "id", "period_start", "period_end", "creator_count",
            "gross_amount", "platform_fee", "net_amount",
            "payout_rule_snapshot", "status", "created_at", "updated_at",
            "processed_at", "payout_count", "paid_count", "failed_count",
            "rule_name", "fee_percentage",
        ]
        read_only_fields = fields

    def get_payout_count(self, obj) -> int:
        annotated = getattr(obj, "payout_count_annotated", None)
        return annotated if annotated is not None else obj.payouts.count()

    def get_paid_count(self, obj) -> int:
        annotated = getattr(obj, "paid_count_annotated", None)
        if annotated is not None:
            return annotated
        return obj.payouts.filter(status=CreatorPayout.Status.PAID).count()

    def get_failed_count(self, obj) -> int:
        annotated = getattr(obj, "failed_count_annotated", None)
        if annotated is not None:
            return annotated
        return obj.payouts.filter(status=CreatorPayout.Status.FAILED).count()

    def get_rule_name(self, obj) -> str | None:
        return (obj.payout_rule_snapshot or {}).get("name")

    def get_fee_percentage(self, obj) -> str | None:
        return (obj.payout_rule_snapshot or {}).get("platform_fee_percentage")


class PayoutBatchDetailSerializer(PayoutBatchSerializer):
    payouts = CreatorPayoutSerializer(many=True, read_only=True)

    class Meta(PayoutBatchSerializer.Meta):
        fields = [*PayoutBatchSerializer.Meta.fields, "payouts"]


class GenerateBatchSerializer(serializers.Serializer):
    """Optional explicit period; defaults to the last completed Mon–Sun week."""

    period_start = serializers.DateField(required=False)
    period_end = serializers.DateField(required=False)

    def validate(self, attrs):
        start, end = attrs.get("period_start"), attrs.get("period_end")
        if bool(start) != bool(end):
            raise serializers.ValidationError(
                "Provide both period_start and period_end, or neither."
            )
        return attrs
