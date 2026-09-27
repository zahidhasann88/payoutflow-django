"""
Development seed data for PayoutFlow.

    python manage.py seed_data            # idempotent — safe to re-run
    python manage.py seed_data --flush    # wipe app data first

Creates: 1 admin, 10 creators (incl. creator1-3@payoutflow.local), jobs
across ~10 weeks in every status, an active payout rule (10% / $20 / WEEKLY),
adjustments, and processed historical payout batches.

Documented dev credentials (see README):
    admin@payoutflow.local   / Admin!2345
    creator1@payoutflow.local / Creator!2345   (same for creator2..10)
"""
from __future__ import annotations

import random
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

ADMIN_PASSWORD = "Admin!2345"
CREATOR_PASSWORD = "Creator!2345"

CREATOR_SEEDS = [
    ("creator1", "Ayesha Rahman", "BANK", "BD10-2200-4451", "VERIFIED", None),
    ("creator2", "Marcus Lee", "PAYPAL", "marcus.lee@pay.example", "SUBMITTED", None),
    ("creator3", "Sofia Almeida", "BANK", "PT50-0033-9921", "NOT_SUBMITTED", None),
    ("creator4", "Daniel Okafor", "BANK", "FAIL-NG-9921", "VERIFIED", None),
    ("creator5", "Hana Sato", "PAYPAL", "hana.sato@pay.example", "VERIFIED", None),
    ("creator6", "Lucas Meyer", "OTHER", "wallet-lm-771", "SUBMITTED", None),
    ("creator7", "Priya Nair", "BANK", "IN30-8871-2210", "VERIFIED", None),
    ("creator8", "Tom Wilson", "PAYPAL", "tom.wilson@pay.example", "NOT_SUBMITTED", Decimal("50")),
    ("creator9", "Elena Petrova", "BANK", "BG80-BNBG-9661", "SUBMITTED", None),
    ("creator10", "Jamal Carter", "OTHER", "wallet-jc-118", "VERIFIED", None),
]

JOB_TITLES = [
    "Product photography session", "Logo design sprint", "Weekly newsletter edit",
    "Social media video pack", "Podcast episode editing", "Landing page copywriting",
    "Brand style guide", "Illustration set (6 pcs)", "UGC ad creatives",
    "Tutorial screencast", "Etsy listing refresh", "Motion graphics intro",
]


class Command(BaseCommand):
    help = "Seed PayoutFlow with realistic development data."

    def add_arguments(self, parser):
        parser.add_argument("--flush", action="store_true",
                            help="Delete existing app data before seeding.")

    @transaction.atomic
    def handle(self, *args, **options):
        from apps.accounts.models import User
        from apps.audit.models import AuditLog
        from apps.creators.models import Creator
        from apps.earnings.models import Adjustment, Earning
        from apps.jobs.models import Job
        from apps.payouts.models import CreatorPayout, PayoutBatch, PayoutRule

        if options["flush"]:
            self.stdout.write("Flushing existing data...")
            Adjustment.objects.all().delete()
            Earning.objects.all().delete()
            CreatorPayout.objects.all().delete()
            PayoutBatch.objects.all().delete()
            PayoutRule.objects.all().delete()
            Job.objects.all().delete()
            Creator.objects.all().delete()
            AuditLog.objects.all().delete()
            User.objects.all().delete()

        if User.objects.filter(email="admin@payoutflow.local").exists():
            self.stdout.write(self.style.WARNING(
                "Seed data already present (admin@payoutflow.local exists). "
                "Use --flush to re-seed from scratch."))
            return

        rng = random.Random(20260921)

        admin = User.objects.create_superuser(
            email="admin@payoutflow.local", password=ADMIN_PASSWORD,
            name="Platform Admin",
        )
        self.stdout.write(f"Admin: {admin.email}")

        rule = PayoutRule.objects.create(
            name="Standard Weekly 10%",
            platform_fee_percentage=Decimal("10.00"),
            minimum_payout=Decimal("20.00"),
            payout_frequency=PayoutRule.Frequency.WEEKLY,
            is_active=True,
        )
        self.stdout.write(f"Payout rule: {rule.name}")

        creators = []
        for i, (prefix, display, method, account, tax, minimum) in enumerate(CREATOR_SEEDS):
            user = User.objects.create_user(
                email=f"{prefix}@payoutflow.local", password=CREATOR_PASSWORD,
                name=display, role=User.Role.CREATOR,
            )
            creator = Creator.objects.create(
                user=user, display_name=display,
                phone=f"+1 555 01{i:02d}",
                payout_method=method, payout_account=account,
                tax_status=tax, minimum_payout=minimum,
            )
            creators.append(creator)
        self.stdout.write(f"Creators: {len(creators)}")

        today = timezone.localdate()
        weeks_back = 10
        created_jobs = completed = 0
        for week in range(weeks_back, 0, -1):
            week_monday = today - timedelta(days=today.weekday() + 7 * week)
            for creator in creators:
                n_jobs = rng.randint(1, 3)
                for _ in range(n_jobs):
                    day = week_monday + timedelta(days=rng.randint(0, 6))
                    title = rng.choice(JOB_TITLES)
                    base = Decimal(str(rng.choice(
                        [40, 60, 75, 100, 120, 150, 180, 200, 250, 300, 500])))
                    surge = Decimal(str(rng.choice(
                        ["1.00", "1.00", "1.00", "1.25", "1.50", "1.75", "2.00"])))
                    tip = Decimal(str(rng.choice([0, 0, 0, 5, 10, 15, 20, 40])))
                    completed_dt = timezone.make_aware(
                        datetime.combine(day, time(rng.randint(9, 19), rng.randint(0, 59)))
                    )

                    roll = rng.random()
                    if week <= 1 and roll < 0.45:
                        job_status = rng.choice([Job.Status.PENDING,
                                                 Job.Status.IN_PROGRESS,
                                                 Job.Status.CANCELLED])
                        completed_at = None
                    else:
                        job_status = Job.Status.COMPLETED
                        completed_at = completed_dt

                    Job.objects.create(
                        creator=creator, title=title,
                        description=f"{title} for a marketplace client.",
                        status=job_status, base_amount=base,
                        surge_multiplier=surge, tip_amount=tip,
                        completed_at=completed_at,
                        created_at=completed_dt - timedelta(days=rng.randint(1, 3)),
                    )
                    created_jobs += 1
                    if job_status == Job.Status.COMPLETED:
                        completed += 1

        this_monday = today - timedelta(days=today.weekday())
        for creator in rng.sample(creators, 4):
            for status_ in (Job.Status.PENDING, Job.Status.IN_PROGRESS):
                day = min(this_monday + timedelta(days=rng.randint(0, 6)), today)
                created = timezone.make_aware(
                    datetime.combine(day, time(rng.randint(9, 17), 0)))
                title = rng.choice(JOB_TITLES)
                Job.objects.create(
                    creator=creator, title=title,
                    description=f"{title} for a marketplace client.",
                    status=status_,
                    base_amount=Decimal(str(rng.choice([75, 120, 180, 250]))),
                    surge_multiplier=Decimal("1.00"),
                    tip_amount=Decimal("0"),
                    completed_at=None,
                    created_at=created,
                )
                created_jobs += 1
        self.stdout.write(f"Jobs: {created_jobs} ({completed} completed)")

        from apps.earnings.services import create_earning_for_completed_job

        earnings = []
        for job in Job.objects.filter(status=Job.Status.COMPLETED).select_related("creator"):
            earnings.append(create_earning_for_completed_job(job, actor=admin))
        self.stdout.write(f"Earnings: {len(earnings)}")

        from apps.earnings.services import add_adjustment

        recent_pending = [e for e in earnings
                          if e.payout_status == Earning.PayoutStatus.PENDING
                          and e.job.completed_at >= timezone.now() - timedelta(days=10)]
        adj_count = 0
        for earning in rng.sample(recent_pending, min(3, len(recent_pending))):
            try:
                add_adjustment(earning=earning, amount=Decimal("-5.00"),
                               reason="Partial refund to client", actor=admin)
                adj_count += 1
            except Exception:
                pass
        self.stdout.write(f"Adjustments: {adj_count}")

        from apps.payouts.services import generate_payout_batch, process_payout_batch

        processed_batches = 0
        ready_batch = None
        for week in range(weeks_back, 1, -1):
            week_monday = today - timedelta(days=today.weekday() + 7 * week)
            week_sunday = week_monday + timedelta(days=6)
            if week_sunday >= today:
                continue
            try:
                batch = generate_payout_batch(
                    period_start=week_monday, period_end=week_sunday, actor=admin)
            except Exception as exc:  # pragma: no cover
                self.stdout.write(self.style.WARNING(f"Skip {week_monday}: {exc}"))
                continue
            rate = 0.08 if week > 3 else 0.0
            process_payout_batch(batch, actor=admin, failure_rate=rate)
            backdated = timezone.make_aware(
                datetime.combine(week_sunday + timedelta(days=1), time(1, 0)))
            PayoutBatch.objects.filter(pk=batch.pk).update(
                created_at=backdated, processed_at=backdated + timedelta(minutes=20))
            CreatorPayout.objects.filter(payout_batch=batch).update(created_at=backdated)
            processed_batches += 1
        self.stdout.write(f"Historical batches generated & processed: {processed_batches}")

        last_monday = today - timedelta(days=today.weekday() + 7)
        last_sunday = last_monday + timedelta(days=6)
        ready_batch = generate_payout_batch(
            period_start=last_monday, period_end=last_sunday, actor=admin)
        backdated = timezone.make_aware(
            datetime.combine(last_sunday + timedelta(days=1), time(1, 0)))
        PayoutBatch.objects.filter(pk=ready_batch.pk).update(created_at=backdated)
        CreatorPayout.objects.filter(payout_batch=ready_batch).update(created_at=backdated)
        self.stdout.write(
            f"READY batch left for demo: {last_monday} -> {last_sunday} "
            f"(net={ready_batch.net_amount})")

        self.stdout.write(self.style.SUCCESS("""
Seed complete. Development logins:
    Admin:    admin@payoutflow.local    / Admin!2345
    Creators: creator1@payoutflow.local / Creator!2345   (...through creator10)
"""))
