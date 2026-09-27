from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db.models import Count, DecimalField, Sum
from django.db.models.functions import TruncMonth, TruncWeek
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.audit.serializers import AuditLogSerializer
from apps.creators.models import Creator
from apps.earnings.models import Earning
from apps.jobs.models import Job
from apps.jobs.serializers import JobSerializer
from apps.payouts.models import CreatorPayout, PayoutBatch
from apps.payouts.serializers import CreatorPayoutSerializer, PayoutBatchSerializer

MONEY = DecimalField(max_digits=14, decimal_places=2)
ZERO = Decimal("0.00")


def _s(value: Decimal | None) -> str:
    return str((value or ZERO).quantize(ZERO))


def admin_dashboard(user: User) -> dict:
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    month_earnings = Earning.objects.filter(job__completed_at__gte=month_start)
    month_totals = month_earnings.aggregate(
        gross=Sum("gross_amount", output_field=MONEY),
        fee=Sum("platform_fee", output_field=MONEY),
    )
    paid_totals = CreatorPayout.objects.filter(status=CreatorPayout.Status.PAID).aggregate(
        total=Sum("net_amount", output_field=MONEY), count=Count("id")
    )
    pending_payouts = CreatorPayout.objects.filter(
        status__in=[CreatorPayout.Status.PENDING, CreatorPayout.Status.PROCESSING]
    ).aggregate(total=Sum("net_amount", output_field=MONEY), count=Count("id"))
    pending_earnings = Earning.objects.filter(
        payout_status=Earning.PayoutStatus.PENDING
    ).aggregate(total=Sum("net_amount", output_field=MONEY), count=Count("id"))

    weekly_start = (now - timedelta(weeks=7)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    weekly = (
        Earning.objects.filter(job__completed_at__gte=weekly_start)
        .annotate(week=TruncWeek("job__completed_at"))
        .values("week")
        .annotate(
            gross=Sum("gross_amount", output_field=MONEY),
            fees=Sum("platform_fee", output_field=MONEY),
            net=Sum("net_amount", output_field=MONEY),
        )
        .order_by("week")
    )
    monthly_start = (month_start - timedelta(days=150)).replace(day=1)
    monthly = (
        Earning.objects.filter(job__completed_at__gte=monthly_start)
        .annotate(month=TruncMonth("job__completed_at"))
        .values("month")
        .annotate(
            gross=Sum("gross_amount", output_field=MONEY),
            fees=Sum("platform_fee", output_field=MONEY),
            net=Sum("net_amount", output_field=MONEY),
        )
        .order_by("month")
    )

    recent_batches = PayoutBatch.objects.order_by("-created_at")[:5]
    recent_activity = AuditLog.objects.select_related("user")[:8]

    return {
        "cards": {
            "total_creators": Creator.objects.count(),
            "month_gross": _s(month_totals["gross"]),
            "month_platform_fees": _s(month_totals["fee"]),
            "total_paid": _s(paid_totals["total"]),
            "total_paid_count": paid_totals["count"] or 0,
            "pending_payout_amount": _s(pending_payouts["total"]),
            "pending_payout_count": pending_payouts["count"] or 0,
            "pending_earnings_amount": _s(pending_earnings["total"]),
            "pending_earnings_count": pending_earnings["count"] or 0,
        },
        "chart": {
            "weekly": [
                {"period": row["week"].date().isoformat(),
                 "gross": _s(row["gross"]), "fees": _s(row["fees"]), "net": _s(row["net"])}
                for row in weekly
            ],
            "monthly": [
                {"period": row["month"].date().isoformat(),
                 "gross": _s(row["gross"]), "fees": _s(row["fees"]), "net": _s(row["net"])}
                for row in monthly
            ],
        },
        "recent_batches": PayoutBatchSerializer(recent_batches, many=True).data,
        "recent_activity": AuditLogSerializer(recent_activity, many=True).data,
        "payout_cron": settings.PAYOUT_CRON,
    }


def creator_dashboard(user: User) -> dict:
    creator: Creator = getattr(user, "creator_profile", None)
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    current = Earning.objects.filter(
        creator=creator, payout_status=Earning.PayoutStatus.PENDING
    ).aggregate(total=Sum("net_amount", output_field=MONEY), count=Count("id"))

    pending_payout = CreatorPayout.objects.filter(
        creator=creator,
        status__in=[CreatorPayout.Status.PENDING, CreatorPayout.Status.PROCESSING],
    ).aggregate(total=Sum("net_amount", output_field=MONEY), count=Count("id"))

    paid_month = CreatorPayout.objects.filter(
        creator=creator, status=CreatorPayout.Status.PAID, processed_at__gte=month_start
    ).aggregate(total=Sum("net_amount", output_field=MONEY))

    totals = Earning.objects.filter(creator=creator).aggregate(
        net=Sum("net_amount", output_field=MONEY), gross=Sum("gross_amount", output_field=MONEY)
    )

    recent_jobs = (
        Job.objects.filter(creator=creator)
        .select_related("creator", "earning")
        .order_by("-created_at")[:5]
    )
    recent_payouts = (
        CreatorPayout.objects.filter(creator=creator)
        .select_related("creator", "payout_batch")
        .order_by("-created_at")[:5]
    )

    return {
        "cards": {
            "current_earnings": _s(current["total"]),
            "current_earnings_count": current["count"] or 0,
            "pending_payout": _s(pending_payout["total"]),
            "pending_payout_count": pending_payout["count"] or 0,
            "paid_this_month": _s(paid_month["total"]),
            "total_earnings": _s(totals["net"]),
            "total_gross": _s(totals["gross"]),
        },
        "recent_jobs": JobSerializer(recent_jobs, many=True).data,
        "recent_payouts": CreatorPayoutSerializer(recent_payouts, many=True).data,
    }
