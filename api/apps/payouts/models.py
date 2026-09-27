from __future__ import annotations

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.money import ZERO


class PayoutRule(models.Model):
    """
    Configurable payout rules. Only ONE rule may be active at a time —
    enforced by a partial unique index. Batches snapshot the rule they used,
    so later changes never rewrite historical payouts.
    """

    class Frequency(models.TextChoices):
        WEEKLY = "WEEKLY", "Weekly"

    name = models.CharField(max_length=120, unique=True)
    platform_fee_percentage = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(ZERO), MaxValueValidator(100)],
    )
    minimum_payout = models.DecimalField(
        max_digits=12, decimal_places=2, default=20, validators=[MinValueValidator(ZERO)]
    )
    payout_frequency = models.CharField(
        max_length=10, choices=Frequency.choices, default=Frequency.WEEKLY
    )
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payout_rules"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["is_active"],
                condition=models.Q(is_active=True),
                name="only_one_active_payout_rule",
            ),
            models.CheckConstraint(
                condition=models.Q(platform_fee_percentage__gte=0)
                & models.Q(platform_fee_percentage__lte=100),
                name="rule_fee_percentage_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.platform_fee_percentage}%)"

    def snapshot(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "platform_fee_percentage": str(self.platform_fee_percentage),
            "minimum_payout": str(self.minimum_payout),
            "payout_frequency": self.payout_frequency,
            "snapshotted_at": timezone.now().isoformat(),
        }


class PayoutBatch(models.Model):
    """One weekly payout run over a period (e.g. Sep 21 – Sep 27)."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        READY = "READY", "Ready"
        PROCESSING = "PROCESSING", "Processing"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    period_start = models.DateField()
    period_end = models.DateField()
    creator_count = models.PositiveIntegerField(default=0)
    gross_amount = models.DecimalField(max_digits=14, decimal_places=2, default=ZERO)
    platform_fee = models.DecimalField(max_digits=14, decimal_places=2, default=ZERO)
    net_amount = models.DecimalField(max_digits=14, decimal_places=2, default=ZERO)
    payout_rule_snapshot = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "payout_batches"
        ordering = ["-period_end", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["period_start", "period_end"],
                name="one_batch_per_period",
            ),
            models.CheckConstraint(
                condition=models.Q(period_start__lte=models.F("period_end")),
                name="batch_period_order",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "period_end"], name="batch_status_period_idx"),
        ]

    def __str__(self) -> str:
        return f"Batch {self.period_start} -> {self.period_end} ({self.status})"


class CreatorPayout(models.Model):
    """One creator's payout inside a batch."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        PAID = "PAID", "Paid"
        FAILED = "FAILED", "Failed"

    payout_batch = models.ForeignKey(
        PayoutBatch, on_delete=models.PROTECT, related_name="payouts"
    )
    creator = models.ForeignKey(
        "creators.Creator", on_delete=models.PROTECT, related_name="payouts"
    )
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2)
    platform_fee = models.DecimalField(max_digits=12, decimal_places=2)
    adjustments = models.DecimalField(max_digits=12, decimal_places=2, default=ZERO)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2)
    earning_count = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "creator_payouts"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["payout_batch", "creator"], name="one_payout_per_creator_per_batch"
            ),
            models.CheckConstraint(
                condition=models.Q(net_amount__gte=0), name="payout_net_non_negative"
            ),
            models.CheckConstraint(
                condition=models.Q(gross_amount__gte=0), name="payout_gross_non_negative"
            ),
        ]
        indexes = [
            models.Index(fields=["creator", "status"], name="payout_creator_status_idx"),
        ]

    def __str__(self) -> str:
        return f"Payout({self.creator}, {self.net_amount}, {self.status})"
