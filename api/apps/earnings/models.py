from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.money import ZERO


class Earning(models.Model):
    """
    One earning per completed job (``job`` is OneToOne + unique, so the same
    job can never generate two earnings).

    ``payout`` is a unique nullable FK (see field comment).
    """

    class PayoutStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        INCLUDED = "INCLUDED", "Included in batch"
        PAID = "PAID", "Paid"

    job = models.OneToOneField(
        "jobs.Job", on_delete=models.PROTECT, related_name="earning"
    )
    creator = models.ForeignKey(
        "creators.Creator", on_delete=models.PROTECT, related_name="earnings"
    )
    base_amount = models.DecimalField(max_digits=12, decimal_places=2)
    surge_amount = models.DecimalField(max_digits=12, decimal_places=2, default=ZERO)
    tip_amount = models.DecimalField(max_digits=12, decimal_places=2, default=ZERO)
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2)
    platform_fee = models.DecimalField(max_digits=12, decimal_places=2, default=ZERO)
    fee_percentage_applied = models.DecimalField(
        max_digits=5, decimal_places=2, default=ZERO,
        help_text="Fee percentage captured when the earning was calculated.",
    )
    adjustment_amount = models.DecimalField(max_digits=12, decimal_places=2, default=ZERO)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2)
    payout_status = models.CharField(
        max_length=10, choices=PayoutStatus.choices,
        default=PayoutStatus.PENDING, db_index=True,
    )
    payout = models.ForeignKey(
        "payouts.CreatorPayout", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="earnings",
    )
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "earnings"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["creator", "payout_status"], name="earning_creator_status_idx"),
            models.Index(fields=["payout_status", "created_at"],
                         name="earning_pstatus_created_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(gross_amount__gte=0), name="earning_gross_non_negative"
            ),
            models.CheckConstraint(
                condition=models.Q(platform_fee__gte=0), name="earning_fee_non_negative"
            ),
        ]

    def __str__(self) -> str:
        return f"Earning(job={self.job_id}, net={self.net_amount}, {self.payout_status})"


class Adjustment(models.Model):
    """
    A signed adjustment (+/-) applied to an earning before it is paid.
    The earning's ``adjustment_amount`` is the running sum of its adjustments
    and its ``net_amount`` is recalculated whenever one is added.
    """

    earning = models.ForeignKey(Earning, on_delete=models.PROTECT, related_name="adjustments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.CharField(max_length=255)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="adjustments_created",
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "earnings_adjustments"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Adjustment({self.amount}) for earning {self.earning_id}"
