"""Payout batch generation & processing — the core payout engine tests."""
from datetime import timedelta
from decimal import Decimal
from unittest import mock

import pytest
from django.db import IntegrityError
from django.db.models import QuerySet
from django.utils import timezone

from apps.core.exceptions import BusinessError
from apps.earnings.models import Earning
from apps.earnings.services import add_adjustment, create_earning_for_completed_job
from apps.payouts.models import CreatorPayout, PayoutBatch, PayoutRule
from apps.payouts.services import (
    generate_payout_batch,
    last_completed_week,
    process_payout_batch,
)
from tests.conftest import make_job


def _earning(creator, base="100", surge="1.00", tip="0", days_ago=10, actor=None):
    completed = timezone.now() - timedelta(days=days_ago)
    job = make_job(creator, base=base, surge=surge, tip=tip, completed_at=completed)
    return create_earning_for_completed_job(job, actor=actor)


@pytest.mark.django_db
class TestPeriods:
    def test_last_completed_week_is_monday_to_sunday(self):
        start, end = last_completed_week()
        assert start.weekday() == 0
        assert end.weekday() == 6
        assert (end - start).days == 6
        assert end < timezone.localdate()


@pytest.mark.django_db
class TestGeneration:
    def test_batch_totals_and_payout_creation(self, creator_factory, rule, admin):
        c1 = creator_factory("g1@test.local")
        c2 = creator_factory("g2@test.local")
        _earning(c1, base="500", surge="1.15", tip="40", actor=admin)
        _earning(c2, base="100", actor=admin)

        start, end = last_completed_week()
        batch = generate_payout_batch(period_start=start, period_end=end, actor=admin)

        assert batch.status == PayoutBatch.Status.READY
        assert batch.creator_count == 2
        assert batch.gross_amount == Decimal("615.00") + Decimal("100.00")
        assert batch.platform_fee == Decimal("61.50") + Decimal("10.00")
        assert batch.net_amount == Decimal("553.50") + Decimal("90.00")
        assert batch.payouts.count() == 2
        assert Earning.objects.filter(payout_status=Earning.PayoutStatus.INCLUDED).count() == 2

    def test_duplicate_batch_rejected(self, creator_factory, rule, admin):
        creator_factory("g3@test.local")
        start, end = last_completed_week()
        generate_payout_batch(period_start=start, period_end=end, actor=admin)
        with pytest.raises(BusinessError) as exc:
            generate_payout_batch(period_start=start, period_end=end, actor=admin)
        assert exc.value.code == "PAYOUT_BATCH_ALREADY_EXISTS"
        assert PayoutBatch.objects.count() == 1

    def test_included_earnings_never_double_included(self, creator_factory, rule, admin):
        """An earning already INCLUDED in a batch is never swept into another."""
        creator = creator_factory("g4@test.local")
        _earning(creator, base="100", actor=admin)
        s1, e1 = last_completed_week()
        b1 = generate_payout_batch(period_start=s1, period_end=e1, actor=admin)
        assert b1.payouts.first().earnings.count() == 1

        earning = Earning.objects.get(creator=creator)
        assert earning.payout_status == Earning.PayoutStatus.INCLUDED

        b0s, b0e = s1 - timedelta(days=7), e1 - timedelta(days=7)
        b0 = generate_payout_batch(period_start=b0s, period_end=b0e, actor=admin)
        assert b0.creator_count == 0
        assert b0.payouts.count() == 0

        earning.refresh_from_db()
        assert earning.payout_status == Earning.PayoutStatus.INCLUDED
        assert earning.payout_id == b1.payouts.first().id
        assert Earning.objects.filter(payout__payout_batch=b0).count() == 0

    def test_minimum_payout_skip_and_rollover(self, creator_factory, rule, admin):
        creator = creator_factory("g5@test.local")
        _earning(creator, base="12", actor=admin)

        s1, e1 = last_completed_week()
        batch = generate_payout_batch(period_start=s1, period_end=e1, actor=admin)
        assert batch.creator_count == 0
        earning = Earning.objects.get(creator=creator)
        assert earning.payout_status == Earning.PayoutStatus.PENDING

        _earning(creator, base="100", days_ago=1, actor=admin)
        s2, e2 = s1 + timedelta(days=7), e1 + timedelta(days=7)
        e2 = min(e2, timezone.localdate())
        s2 = e2 - timedelta(days=6)
        batch2 = generate_payout_batch(period_start=s2, period_end=e2, actor=admin)
        payout = batch2.payouts.get(creator=creator)
        assert payout.earning_count == 2
        assert payout.net_amount == Decimal("10.80") + Decimal("90.00")

    def test_creator_specific_minimum_override(self, creator_factory, rule, admin):
        creator = creator_factory("g6@test.local", minimum_payout=Decimal("500.00"))
        _earning(creator, base="300", actor=admin)
        s, e = last_completed_week()
        batch = generate_payout_batch(period_start=s, period_end=e, actor=admin)
        assert batch.creator_count == 0

    def test_adjustments_flow_into_batch(self, creator_factory, rule, admin):
        creator = creator_factory("g7@test.local")
        earning = _earning(creator, base="500", actor=admin)
        add_adjustment(earning=earning, amount=Decimal("-5.00"), reason="refund", actor=admin)
        s, e = last_completed_week()
        batch = generate_payout_batch(period_start=s, period_end=e, actor=admin)
        payout = batch.payouts.get(creator=creator)
        assert payout.adjustments == Decimal("-5.00")
        assert payout.net_amount == Decimal("445.00")
        assert batch.net_amount == Decimal("445.00")

    def test_rule_snapshot_stored_on_batch(self, creator_factory, rule, admin):
        creator = creator_factory("g8@test.local")
        _earning(creator, base="100", actor=admin)
        s, e = last_completed_week()
        batch = generate_payout_batch(period_start=s, period_end=e, actor=admin)
        snap = batch.payout_rule_snapshot
        assert snap["platform_fee_percentage"] == "10.00"
        assert snap["minimum_payout"] == "20.00"
        assert snap["payout_frequency"] == "WEEKLY"

    def test_no_active_rule_blocks_generation(self, creator_factory, admin):
        creator_factory("g9@test.local")
        with pytest.raises(BusinessError) as exc:
            generate_payout_batch(actor=admin)
        assert exc.value.code == "NO_ACTIVE_PAYOUT_RULE"

    def test_future_period_rejected(self, rule, admin):
        tomorrow = timezone.localdate() + timedelta(days=1)
        with pytest.raises(BusinessError) as exc:
            generate_payout_batch(period_start=tomorrow, period_end=tomorrow, actor=admin)
        assert exc.value.code == "INVALID_PAYOUT_PERIOD"

    def test_inverted_period_rejected(self, rule, admin):
        start, end = last_completed_week()
        with pytest.raises(BusinessError) as exc:
            generate_payout_batch(period_start=end, period_end=start, actor=admin)
        assert exc.value.code == "INVALID_PAYOUT_PERIOD"

    def test_concurrent_generation_cannot_duplicate(self, creator_factory, rule, admin):
        """
        Simulates two payout generators racing on the same period.

        ``generate_payout_batch`` checks "does a batch already exist?" and then
        inserts. Here the competing batch already exists but that first check
        is made blind to it — the interleaving where another transaction
        commits between our check and our insert. The insert then hits the
        unique (period_start, period_end) index, and the loser must surface a
        clean PAYOUT_BATCH_ALREADY_EXISTS while rolling back its own work.
        """
        creator = creator_factory("g10@test.local")
        _earning(creator, base="100", actor=admin)
        start, end = last_completed_week()

        winner = PayoutBatch.objects.create(
            period_start=start, period_end=end,
            status=PayoutBatch.Status.READY, payout_rule_snapshot=rule.snapshot(),
        )

        real_exists, calls = QuerySet.exists, {"n": 0}

        def blind_to_the_first_check(self):
            calls["n"] += 1
            return False if calls["n"] == 1 else real_exists(self)

        with mock.patch.object(QuerySet, "exists", blind_to_the_first_check):
            with pytest.raises(BusinessError) as exc:
                generate_payout_batch(period_start=start, period_end=end, actor=admin)

        assert exc.value.code == "PAYOUT_BATCH_ALREADY_EXISTS"
        batches = PayoutBatch.objects.filter(period_start=start, period_end=end)
        assert [b.id for b in batches] == [winner.id]
        assert CreatorPayout.objects.count() == 0
        assert Earning.objects.get(creator=creator).payout_status == Earning.PayoutStatus.PENDING


@pytest.mark.django_db
class TestProcessing:
    def _ready_batch(self, creator_factory, rule, admin, **kwargs):
        creator = creator_factory(**kwargs)
        _earning(creator, base="500", actor=admin)
        s, e = last_completed_week()
        return generate_payout_batch(period_start=s, period_end=e, actor=admin), creator

    def test_process_marks_everything_paid(self, creator_factory, rule, admin):
        batch, creator = self._ready_batch(creator_factory, rule, admin,
                                           email="p1@test.local")
        batch = process_payout_batch(batch, actor=admin, failure_rate=0.0)
        assert batch.status == PayoutBatch.Status.COMPLETED
        payout = batch.payouts.get(creator=creator)
        assert payout.status == CreatorPayout.Status.PAID
        assert payout.processed_at is not None
        assert Earning.objects.filter(
            creator=creator, payout_status=Earning.PayoutStatus.PAID
        ).count() == 1

    def test_processed_batch_cannot_be_processed_twice(self, creator_factory, rule, admin):
        batch, _ = self._ready_batch(creator_factory, rule, admin, email="p2@test.local")
        process_payout_batch(batch, actor=admin, failure_rate=0.0)
        with pytest.raises(BusinessError) as exc:
            process_payout_batch(batch, actor=admin, failure_rate=0.0)
        assert exc.value.code == "PAYOUT_BATCH_ALREADY_PROCESSED"

    def test_failed_payout_records_reason_and_rolls_over(self, creator_factory, rule, admin):
        batch, creator = self._ready_batch(creator_factory, rule, admin,
                                           email="p3@test.local")
        batch = process_payout_batch(batch, actor=admin, failure_rate=1.0)
        payout = batch.payouts.get(creator=creator)
        assert payout.status == CreatorPayout.Status.FAILED
        assert payout.failure_reason
        assert payout.processed_at is not None
        earning = Earning.objects.get(creator=creator)
        assert earning.payout_status == Earning.PayoutStatus.PENDING
        assert earning.payout is None
        assert batch.status == PayoutBatch.Status.FAILED

    def test_failed_payout_can_be_repaid_next_period(self, creator_factory, rule, admin):
        batch, creator = self._ready_batch(creator_factory, rule, admin,
                                           email="p4@test.local")
        process_payout_batch(batch, actor=admin, failure_rate=1.0)
        s2 = batch.period_start + timedelta(days=7)
        e2 = min(batch.period_end + timedelta(days=7), timezone.localdate())
        s2 = e2 - timedelta(days=6)
        batch2 = generate_payout_batch(period_start=s2, period_end=e2, actor=admin)
        payout2 = batch2.payouts.get(creator=creator)
        assert payout2.net_amount == Decimal("450.00")
        batch2 = process_payout_batch(batch2, actor=admin, failure_rate=0.0)
        assert batch2.payouts.get(creator=creator).status == CreatorPayout.Status.PAID


@pytest.mark.django_db
class TestRuleChanges:
    def test_changing_rule_does_not_rewrite_history(self, creator_factory, rule, admin):
        creator = creator_factory("h1@test.local")
        _earning(creator, base="500", actor=admin)
        s, e = last_completed_week()
        batch = generate_payout_batch(period_start=s, period_end=e, actor=admin)
        process_payout_batch(batch, actor=admin, failure_rate=0.0)
        payout = batch.payouts.first()
        old_fee, old_net = payout.platform_fee, payout.net_amount
        old_earning_fee = Earning.objects.get(creator=creator).platform_fee

        rule.is_active = False
        rule.save()
        PayoutRule.objects.create(
            name="Premium 25%", platform_fee_percentage=Decimal("25.00"),
            minimum_payout=Decimal("20.00"), is_active=True,
        )
        payout.refresh_from_db()
        batch.refresh_from_db()
        assert payout.platform_fee == old_fee
        assert payout.net_amount == old_net
        assert batch.payout_rule_snapshot["platform_fee_percentage"] == "10.00"
        assert Earning.objects.get(creator=creator).platform_fee == old_earning_fee

        _earning(creator, base="100", days_ago=1, actor=admin)
        new_earning = Earning.objects.filter(creator=creator).order_by("-created_at").first()
        assert new_earning.platform_fee == Decimal("25.00")


@pytest.mark.django_db
class TestSingleActiveRule:
    def test_database_blocks_two_active_rules(self, rule):
        with pytest.raises(IntegrityError):
            PayoutRule.objects.create(
                name="Second", platform_fee_percentage=Decimal("5"),
                minimum_payout=Decimal("10"), is_active=True,
            )
