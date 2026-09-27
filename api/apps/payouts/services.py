from __future__ import annotations

import logging
import random
from datetime import date, timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit.services import AuditAction, record_audit
from apps.core.error_codes import ErrorCode
from apps.core.exceptions import BusinessError
from apps.core.money import ZERO, to_money
from apps.earnings.models import Earning

from .models import CreatorPayout, PayoutBatch, PayoutRule

logger = logging.getLogger("payoutflow.payouts")


def get_active_rule() -> PayoutRule | None:
    return PayoutRule.objects.filter(is_active=True).first()


def week_bounds(day: date) -> tuple[date, date]:
    """Monday–Sunday bounds of the week containing ``day``."""
    start = day - timedelta(days=day.weekday())
    return start, start + timedelta(days=6)


def last_completed_week(today: date | None = None) -> tuple[date, date]:
    """The most recent fully-completed Mon–Sun week (the default period)."""
    today = today or timezone.localdate()
    this_monday, _ = week_bounds(today)
    end = this_monday - timedelta(days=1)
    return end - timedelta(days=6), end


def validate_period(period_start: date, period_end: date) -> None:
    if period_start > period_end:
        raise BusinessError(
            "period_start must be on or before period_end.",
            code=ErrorCode.INVALID_PAYOUT_PERIOD,
        )
    if period_end > timezone.localdate():
        raise BusinessError(
            "Payout period cannot end in the future.",
            code=ErrorCode.INVALID_PAYOUT_PERIOD,
        )
    if (period_end - period_start).days > 13:
        raise BusinessError(
            "Payout period cannot span more than two weeks.",
            code=ErrorCode.INVALID_PAYOUT_PERIOD,
        )


@transaction.atomic
def generate_payout_batch(
    *,
    period_start: date | None = None,
    period_end: date | None = None,
    actor=None,
) -> PayoutBatch:
    """
    Generate the weekly payout batch for a period (default: last completed
    Mon–Sun week).

    Steps (all inside one transaction):
      1. Resolve/validate the period; refuse duplicates early.
      2. Load the active payout rule (snapshot stored on the batch).
      3. Create the batch row — the unique (period_start, period_end)
         constraint is the real guard against concurrent duplicates.
      4. Select eligible earnings (PENDING, job COMPLETED, completed within
         the period or carried over from earlier periods) with row locks.
      5. Group by creator; sum gross / fees / adjustments / net.
      6. Apply the minimum payout threshold — creators below it are skipped
         and their earnings stay PENDING for the next period (roll-over).
      7. Create one CreatorPayout per eligible creator and mark their
         earnings INCLUDED.
      8. Finalize batch totals, flip DRAFT → READY, record an audit event.
    """
    if period_start is None or period_end is None:
        period_start, period_end = last_completed_week()
    validate_period(period_start, period_end)

    if PayoutBatch.objects.filter(period_start=period_start,
                                  period_end=period_end).exists():
        raise BusinessError(
            f"A payout batch for {period_start} -> {period_end} already exists.",
            code=ErrorCode.PAYOUT_BATCH_ALREADY_EXISTS,
            status_code=409,
        )

    rule = get_active_rule()
    if rule is None:
        raise BusinessError(
            "No active payout rule — configure one before generating payouts.",
            code=ErrorCode.NO_ACTIVE_PAYOUT_RULE,
            status_code=409,
        )

    try:
        batch = PayoutBatch.objects.create(
            period_start=period_start,
            period_end=period_end,
            status=PayoutBatch.Status.DRAFT,
            payout_rule_snapshot=rule.snapshot(),
        )
    except IntegrityError as exc:
        raise BusinessError(
            f"A payout batch for {period_start} -> {period_end} already exists.",
            code=ErrorCode.PAYOUT_BATCH_ALREADY_EXISTS,
            status_code=409,
        ) from exc

    eligible = list(
        Earning.objects.select_for_update()
        .select_related("creator", "job")
        .filter(
            payout_status=Earning.PayoutStatus.PENDING,
            job__status="COMPLETED",
            job__completed_at__date__lte=period_end,
        )
        .order_by("creator_id", "created_at")
    )

    grouped: dict[int, list[Earning]] = {}
    for earning in eligible:
        grouped.setdefault(earning.creator_id, []).append(earning)

    creator_count = 0
    total_gross = total_fee = total_net = ZERO
    skipped = []

    for creator_id, earnings in grouped.items():
        creator = earnings[0].creator
        gross = to_money(sum((e.gross_amount for e in earnings), ZERO))
        fee = to_money(sum((e.platform_fee for e in earnings), ZERO))
        adjustments = to_money(sum((e.adjustment_amount for e in earnings), ZERO))
        net = to_money(gross - fee + adjustments)

        minimum = creator.minimum_payout
        if minimum is None:
            minimum = rule.minimum_payout
        if net < (minimum or ZERO):
            skipped.append({"creator_id": str(creator_id),
                            "display_name": creator.display_name,
                            "net_amount": str(net),
                            "minimum_payout": str(minimum or ZERO)})
            continue

        payout = CreatorPayout.objects.create(
            payout_batch=batch,
            creator=creator,
            gross_amount=gross,
            platform_fee=fee,
            adjustments=adjustments,
            net_amount=net,
            earning_count=len(earnings),
            status=CreatorPayout.Status.PENDING,
        )
        for earning in earnings:
            earning.payout_status = Earning.PayoutStatus.INCLUDED
            earning.payout = payout
            earning.save(update_fields=["payout_status", "payout", "updated_at"])

        creator_count += 1
        total_gross += gross
        total_fee += fee
        total_net += net

    batch.creator_count = creator_count
    batch.gross_amount = to_money(total_gross)
    batch.platform_fee = to_money(total_fee)
    batch.net_amount = to_money(total_net)
    batch.status = PayoutBatch.Status.READY
    batch.save(update_fields=["creator_count", "gross_amount", "platform_fee",
                              "net_amount", "status", "updated_at"])

    record_audit(
        actor, AuditAction.PAYOUT_BATCH_CREATED, "PayoutBatch", batch.id,
        metadata={
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "creator_count": creator_count,
            "gross_amount": batch.gross_amount,
            "platform_fee": batch.platform_fee,
            "net_amount": batch.net_amount,
            "rule_name": rule.name,
            "skipped_below_minimum": skipped,
        },
    )
    logger.info(
        "Generated payout batch %s for %s->%s creators=%s net=%s skipped=%s",
        batch.id, period_start, period_end, creator_count, batch.net_amount, len(skipped),
    )
    return batch


def simulate_transfer(payout: CreatorPayout, failure_rate: float | None = None) -> tuple[bool, str]:
    """
    Simulated money transfer — PayoutFlow never talks to real providers.

    Fails when:
      * the payout account is flagged for demo failures (contains ``FAIL``), or
      * a random draw falls under ``PAYOUT_SIMULATED_FAILURE_RATE``.
    """
    if failure_rate is None:
        failure_rate = settings.PAYOUT_SIMULATED_FAILURE_RATE

    account = (payout.creator.payout_account or "").upper()
    if "FAIL" in account:
        return False, "Simulated failure: recipient account rejected the transfer."
    if random.random() < failure_rate:
        return False, "Simulated failure: temporary provider outage — retry next period."
    return True, ""


@transaction.atomic
def process_payout_batch(
    batch: PayoutBatch,
    *,
    actor=None,
    failure_rate: float | None = None,
) -> PayoutBatch:
    """
    Process every PENDING payout in a READY (or previously FAILED) batch:

        PENDING → PROCESSING → PAID   (or → FAILED with a stored reason)

    * A batch that is PROCESSING or COMPLETED can never be processed twice.
    * PAID payouts mark their earnings PAID (they can never be re-included).
    * FAILED payouts release their earnings back to PENDING so the money
      rolls over into the next batch — while the failure stays recorded here.
    """
    locked = PayoutBatch.objects.select_for_update().get(pk=batch.pk)
    if locked.status in (PayoutBatch.Status.PROCESSING, PayoutBatch.Status.COMPLETED):
        raise BusinessError(
            "Payout batch has already been processed.",
            code=ErrorCode.PAYOUT_BATCH_ALREADY_PROCESSED,
            status_code=409,
        )
    if locked.status == PayoutBatch.Status.DRAFT:
        raise BusinessError(
            "Payout batch is still a draft.",
            code=ErrorCode.INVALID_STATUS_TRANSITION,
            status_code=409,
        )

    locked.status = PayoutBatch.Status.PROCESSING
    locked.save(update_fields=["status", "updated_at"])

    payouts = list(
        CreatorPayout.objects.select_for_update()
        .select_related("creator")
        .prefetch_related("earnings")
        .filter(payout_batch=locked, status=CreatorPayout.Status.PENDING)
    )

    paid_count = failed_count = 0
    for payout in payouts:
        payout.status = CreatorPayout.Status.PROCESSING
        payout.save(update_fields=["status", "updated_at"])

        ok, reason = simulate_transfer(payout, failure_rate=failure_rate)
        payout.processed_at = timezone.now()
        if ok:
            payout.status = CreatorPayout.Status.PAID
            payout.failure_reason = ""
            Earning.objects.filter(payout=payout).update(
                payout_status=Earning.PayoutStatus.PAID, updated_at=payout.processed_at
            )
            paid_count += 1
        else:
            payout.status = CreatorPayout.Status.FAILED
            payout.failure_reason = reason
            for earning in payout.earnings.all():
                earning.payout_status = Earning.PayoutStatus.PENDING
                earning.payout = None
                earning.save(update_fields=["payout_status", "payout", "updated_at"])
            failed_count += 1
            record_audit(actor, AuditAction.PAYOUT_FAILED, "CreatorPayout", payout.id,
                         metadata={"creator_id": str(payout.creator_id),
                                   "net_amount": payout.net_amount,
                                   "failure_reason": reason})
        payout.save(update_fields=["status", "failure_reason",
                                   "processed_at", "updated_at"])

    all_failed = failed_count > 0 and paid_count == 0
    locked.status = (
        PayoutBatch.Status.FAILED if all_failed else PayoutBatch.Status.COMPLETED
    )
    locked.processed_at = timezone.now()
    locked.save(update_fields=["status", "processed_at", "updated_at"])

    record_audit(
        actor, AuditAction.PAYOUT_BATCH_PROCESSED, "PayoutBatch", locked.id,
        metadata={"period_start": locked.period_start.isoformat(),
                  "period_end": locked.period_end.isoformat(),
                  "paid_count": paid_count, "failed_count": failed_count,
                  "batch_status": locked.status},
    )
    logger.info("Processed payout batch %s paid=%s failed=%s status=%s",
                locked.id, paid_count, failed_count, locked.status)
    return locked
