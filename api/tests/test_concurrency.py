"""
Real concurrency tests — these need PostgreSQL.

Every other test runs inside a single transaction, so row locks are never
actually contended. These tests commit (``transaction=True``) and drive two
real threads, each with its own database connection, to prove the guarantees
the payout engine claims:

* two simultaneous generations for the same period produce exactly one batch
* an earning can never be attached to two payouts
* two simultaneous processings pay a batch exactly once
* two simultaneous rule activations leave exactly one active rule
"""
from __future__ import annotations

import threading
from datetime import datetime, time, timedelta
from decimal import Decimal

import pytest
from django.db import connections
from django.utils import timezone

from apps.accounts.models import User
from apps.core.exceptions import BusinessError
from apps.creators.models import Creator
from apps.earnings.models import Earning
from apps.earnings.services import create_earning_for_completed_job
from apps.jobs.models import Job
from apps.payouts.models import CreatorPayout, PayoutBatch, PayoutRule
from apps.payouts.services import (
    generate_payout_batch,
    last_completed_week,
    process_payout_batch,
)

THREAD_TIMEOUT = 30


def _run_in_parallel(target, count=2):
    """Run ``target`` in ``count`` threads released at the same instant."""
    barrier = threading.Barrier(count, timeout=THREAD_TIMEOUT)
    results: list[tuple[str, object]] = []
    lock = threading.Lock()

    def wrapped():
        try:
            barrier.wait()
            outcome = ("ok", target())
        except BusinessError as exc:
            outcome = ("business_error", exc.code)
        except Exception as exc:  # pragma: no cover - surfaced in assertions
            outcome = ("unexpected", f"{type(exc).__name__}: {exc}")
        finally:
            connections.close_all()
        with lock:
            results.append(outcome)

    threads = [threading.Thread(target=wrapped) for _ in range(count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=THREAD_TIMEOUT)
        assert not t.is_alive(), "thread deadlocked - row locking is wrong"
    return results


def _seed_creator_with_earning(email: str, base: str = "500.00") -> Creator:
    """A creator with one completed job inside the last completed week."""
    user = User.objects.create_user(email=email, password="Test!2345pass",
                                   name="Concurrent", role=User.Role.CREATOR)
    creator = Creator.objects.create(user=user, display_name=email.split("@")[0])
    period_start, _ = last_completed_week()
    completed_at = timezone.make_aware(
        datetime.combine(period_start + timedelta(days=2), time(12, 0))
    )
    job = Job.objects.create(
        creator=creator, title="Concurrent job", status=Job.Status.COMPLETED,
        base_amount=Decimal(base), surge_multiplier=Decimal("1.00"),
        tip_amount=Decimal("0.00"), completed_at=completed_at,
    )
    create_earning_for_completed_job(job, actor=None)
    return creator


@pytest.fixture
def active_rule(transactional_db):
    return PayoutRule.objects.create(
        name="Concurrency Weekly 10%", platform_fee_percentage=Decimal("10.00"),
        minimum_payout=Decimal("20.00"), is_active=True,
    )


@pytest.mark.django_db(transaction=True)
class TestParallelPayoutGeneration:
    def test_two_generators_create_exactly_one_batch(self, active_rule):
        creator = _seed_creator_with_earning("par1@test.local")
        start, end = last_completed_week()

        results = _run_in_parallel(
            lambda: generate_payout_batch(period_start=start, period_end=end,
                                          actor=None).id
        )

        unexpected = [r for r in results if r[0] == "unexpected"]
        assert not unexpected, unexpected

        winners = [r for r in results if r[0] == "ok"]
        losers = [r for r in results if r[0] == "business_error"]
        assert len(winners) == 1, results
        assert len(losers) == 1, results
        assert losers[0][1] == "PAYOUT_BATCH_ALREADY_EXISTS"

        assert PayoutBatch.objects.filter(period_start=start, period_end=end).count() == 1
        assert CreatorPayout.objects.filter(creator=creator).count() == 1
        earning = Earning.objects.get(creator=creator)
        assert earning.payout_status == Earning.PayoutStatus.INCLUDED
        assert earning.payout_id == CreatorPayout.objects.get(creator=creator).id

    def test_batch_totals_match_its_payouts_after_contention(self, active_rule):
        for i in range(3):
            _seed_creator_with_earning(f"par2{i}@test.local", base="300.00")
        start, end = last_completed_week()

        _run_in_parallel(
            lambda: generate_payout_batch(period_start=start, period_end=end,
                                          actor=None).id
        )

        batch = PayoutBatch.objects.get(period_start=start, period_end=end)
        payouts = list(batch.payouts.all())
        assert batch.creator_count == len(payouts) == 3
        assert batch.net_amount == sum(p.net_amount for p in payouts)
        assert batch.gross_amount == sum(p.gross_amount for p in payouts)
        assert Earning.objects.filter(payout__payout_batch=batch).count() == 3


@pytest.mark.django_db(transaction=True)
class TestParallelBatchProcessing:
    def test_two_processors_pay_the_batch_exactly_once(self, active_rule):
        """
        The ``FOR UPDATE`` status re-check in ``process_payout_batch`` is the only
        guarantee with no contended coverage otherwise: the sequential test just
        calls the endpoint twice, which never exercises the lock.
        """
        creator = _seed_creator_with_earning("proc1@test.local")
        start, end = last_completed_week()
        batch = generate_payout_batch(period_start=start, period_end=end, actor=None)

        results = _run_in_parallel(
            lambda: process_payout_batch(
                PayoutBatch.objects.get(pk=batch.pk), actor=None, failure_rate=0.0
            ).id
        )

        unexpected = [r for r in results if r[0] == "unexpected"]
        assert not unexpected, unexpected

        winners = [r for r in results if r[0] == "ok"]
        losers = [r for r in results if r[0] == "business_error"]
        assert len(winners) == 1, results
        assert len(losers) == 1, results
        assert losers[0][1] == "PAYOUT_BATCH_ALREADY_PROCESSED"

        batch.refresh_from_db()
        assert batch.status == PayoutBatch.Status.COMPLETED

        payout = CreatorPayout.objects.get(creator=creator, payout_batch=batch)
        assert payout.status == CreatorPayout.Status.PAID

        earning = Earning.objects.get(creator=creator)
        assert earning.payout_status == Earning.PayoutStatus.PAID
        assert earning.payout_id == payout.id


@pytest.mark.django_db(transaction=True)
class TestParallelRuleActivation:
    def test_two_activations_leave_one_active_rule(self, active_rule):
        from apps.payouts.serializers import PayoutRuleSerializer

        candidates = [
            PayoutRule.objects.create(
                name=f"Candidate {i}", platform_fee_percentage=Decimal("12.00"),
                minimum_payout=Decimal("20.00"), is_active=False,
            )
            for i in range(2)
        ]
        pending = iter(candidates)
        lock = threading.Lock()

        def activate():
            with lock:
                rule = next(pending)
            serializer = PayoutRuleSerializer(rule, data={"is_active": True},
                                              partial=True)
            serializer.is_valid(raise_exception=True)
            return serializer.save().id

        results = _run_in_parallel(activate)
        unexpected = [r for r in results if r[0] == "unexpected"]
        assert not unexpected, unexpected
        assert PayoutRule.objects.filter(is_active=True).count() == 1
