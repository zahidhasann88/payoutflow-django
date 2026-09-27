from __future__ import annotations

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone


class Creator(models.Model):
    class PayoutMethod(models.TextChoices):
        BANK = "BANK", "Bank transfer"
        PAYPAL = "PAYPAL", "PayPal"
        OTHER = "OTHER", "Other"

    class TaxStatus(models.TextChoices):
        NOT_SUBMITTED = "NOT_SUBMITTED", "Not submitted"
        SUBMITTED = "SUBMITTED", "Submitted"
        VERIFIED = "VERIFIED", "Verified"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="creator_profile",
    )
    display_name = models.CharField(max_length=120)
    phone = models.CharField(
        max_length=30, blank=True, default="",
        validators=[RegexValidator(r"^\+?[0-9 ()\-]{6,20}$", "Enter a valid phone number.")],
    )
    payout_method = models.CharField(
        max_length=10, choices=PayoutMethod.choices, default=PayoutMethod.BANK
    )
    payout_account = models.CharField(max_length=120, blank=True, default="")
    tax_status = models.CharField(
        max_length=20, choices=TaxStatus.choices, default=TaxStatus.NOT_SUBMITTED
    )

    minimum_payout = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Overrides the active payout rule's minimum payout when set.",
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "creators"
        ordering = ["display_name"]

    def __str__(self) -> str:
        return self.display_name

    @property
    def effective_minimum_payout(self):
        from apps.payouts.services import get_active_rule

        if self.minimum_payout is not None:
            return self.minimum_payout
        rule = get_active_rule()
        return rule.minimum_payout if rule else None
