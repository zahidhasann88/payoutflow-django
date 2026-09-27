"""
Weekly payout generation command — safe to run repeatedly.

    python manage.py generate_payouts
    python manage.py generate_payouts --period-start 2026-09-14 --period-end 2026-09-20

Production scheduling (Linux cron, weekly on Monday at 00:00 UTC):

    0 0 * * 1 cd /app && python manage.py generate_payouts >> /var/log/payoutflow-cron.log 2>&1

The command is idempotent: if a batch for the period already exists it exits
cleanly without creating a duplicate (guarded by both an explicit check and a
database unique constraint).
"""
from __future__ import annotations

from datetime import date, datetime

from django.core.management.base import BaseCommand, CommandError

from apps.core.exceptions import BusinessError
from apps.payouts.services import generate_payout_batch, last_completed_week


class Command(BaseCommand):
    help = "Generate the weekly payout batch (idempotent, duplicate-safe)."

    def add_arguments(self, parser):
        parser.add_argument("--period-start", type=str, default=None,
                            help="Period start date (YYYY-MM-DD). Default: last completed week.")
        parser.add_argument("--period-end", type=str, default=None,
                            help="Period end date (YYYY-MM-DD). Default: last completed week.")
        parser.add_argument("--dry-run", action="store_true",
                            help="Report what would happen without writing.")

    def handle(self, *args, **options):
        start = self._parse_date(options["period_start"], "--period-start")
        end = self._parse_date(options["period_end"], "--period-end")
        if (start is None) != (end is None):
            raise CommandError("Provide both --period-start and --period-end, or neither.")
        if start is None:
            start, end = last_completed_week()

        self.stdout.write(f"Payout period: {start} -> {end}")
        if options["dry_run"]:
            from apps.earnings.models import Earning
            count = Earning.objects.filter(
                payout_status=Earning.PayoutStatus.PENDING,
                job__status="COMPLETED",
                job__completed_at__date__lte=end,
            ).count()
            self.stdout.write(self.style.WARNING(
                f"[dry-run] {count} pending earning(s) would be considered."))
            return

        try:
            batch = generate_payout_batch(period_start=start, period_end=end, actor=None)
        except BusinessError as exc:
            if exc.code == "PAYOUT_BATCH_ALREADY_EXISTS":
                self.stdout.write(self.style.WARNING(
                    f"Batch for {start} -> {end} already exists - nothing to do."))
                return
            raise CommandError(f"{exc.code}: {exc.message}") from exc

        self.stdout.write(self.style.SUCCESS(
            f"Batch {batch.id} created: creators={batch.creator_count} "
            f"gross={batch.gross_amount} fees={batch.platform_fee} net={batch.net_amount} "
            f"status={batch.status}"
        ))

    @staticmethod
    def _parse_date(value: str | None, flag: str) -> date | None:
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError as exc:
            raise CommandError(f"{flag} must be formatted YYYY-MM-DD.") from exc
