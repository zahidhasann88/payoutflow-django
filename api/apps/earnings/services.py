from __future__ import annotations

import logging

from django.db import IntegrityError, transaction

from apps.core.error_codes import ErrorCode
from apps.core.exceptions import BusinessError
from apps.core.money import ZERO, calculate_earning_amounts, to_money
from apps.jobs.models import Job
from apps.payouts.services import get_active_rule

from .models import Adjustment, Earning

logger = logging.getLogger("payoutflow.earnings")


@transaction.atomic
def create_earning_for_completed_job(job: Job, actor=None) -> Earning:
    if job.status != Job.Status.COMPLETED:
        raise BusinessError(
            f"Job '{job.title}' must be completed before earnings are calculated.",
            code=ErrorCode.JOB_NOT_COMPLETED,
            status_code=409,
        )

    rule = get_active_rule()
    fee_percentage = rule.platform_fee_percentage if rule else ZERO

    amounts = calculate_earning_amounts(
        base_amount=job.base_amount,
        surge_multiplier=job.surge_multiplier,
        tip_amount=job.tip_amount,
        fee_percentage=fee_percentage,
    )
    try:
        earning = Earning.objects.create(
            job=job,
            creator=job.creator,
            fee_percentage_applied=fee_percentage,
            **amounts,
        )
    except IntegrityError as exc:
        raise BusinessError(
            "This job already has an earning — it cannot be paid twice.",
            code=ErrorCode.EARNING_ALREADY_PAID,
            status_code=409,
        ) from exc
    logger.info("Created earning %s for job %s net=%s", earning.id, job.id, earning.net_amount)
    return earning


@transaction.atomic
def add_adjustment(*, earning: Earning, amount, reason: str, actor) -> Adjustment:
    """
    Add a signed adjustment to a PENDING earning and recalculate its net.

    Adjustments on earnings already INCLUDED in a batch or PAID are refused —
    historical/pending payout amounts must stay stable.
    """
    from apps.audit.services import AuditAction, record_audit

    amount = to_money(amount)
    if amount == ZERO:
        raise BusinessError("Adjustment amount must not be zero.",
                            code=ErrorCode.VALIDATION_ERROR)
    if earning.payout_status == Earning.PayoutStatus.PAID:
        raise BusinessError(
            "Cannot adjust an earning that has already been paid.",
            code=ErrorCode.EARNING_ALREADY_PAID, status_code=409,
        )
    if earning.payout_status == Earning.PayoutStatus.INCLUDED:
        raise BusinessError(
            "Cannot adjust an earning already included in a payout batch.",
            code=ErrorCode.EARNING_ALREADY_INCLUDED, status_code=409,
        )

    locked = Earning.objects.select_for_update().get(pk=earning.pk)
    adjustment = Adjustment.objects.create(
        earning=locked, amount=amount, reason=reason, created_by=actor
    )
    new_adjustment_total = to_money(locked.adjustment_amount + amount)
    new_net = to_money(locked.gross_amount - locked.platform_fee + new_adjustment_total)
    if new_net < ZERO:
        raise BusinessError(
            "Adjustment would make net earnings negative — not allowed.",
            code=ErrorCode.VALIDATION_ERROR,
        )
    locked.adjustment_amount = new_adjustment_total
    locked.net_amount = new_net
    locked.save(update_fields=["adjustment_amount", "net_amount", "updated_at"])
    record_audit(actor, AuditAction.ADJUSTMENT_CREATED, "Earning", locked.id,
                 metadata={"amount": amount, "reason": reason,
                           "new_net_amount": new_net})
    return adjustment
