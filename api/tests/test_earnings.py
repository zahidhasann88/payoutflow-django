"""Earning creation, job completion flow and adjustments."""
from decimal import Decimal

import pytest

from apps.core.exceptions import BusinessError
from apps.earnings.models import Adjustment, Earning
from apps.earnings.services import add_adjustment, create_earning_for_completed_job
from apps.jobs.models import Job
from apps.jobs.services import complete_job
from tests.conftest import make_job


@pytest.mark.django_db
class TestEarningCreation:
    def test_completed_job_creates_correct_earning(self, creator_factory, rule, admin):
        creator = creator_factory("c1@test.local")
        job = make_job(creator, base="500", surge="1.15", tip="40",
                       status=Job.Status.PENDING, completed_at=None)
        job = complete_job(job=job, actor=admin)

        earning = Earning.objects.get(job=job)
        assert earning.surge_amount == Decimal("575.00")
        assert earning.gross_amount == Decimal("615.00")
        assert earning.platform_fee == Decimal("61.50")
        assert earning.net_amount == Decimal("615.00") - Decimal("61.50")
        assert earning.fee_percentage_applied == Decimal("10.00")
        assert earning.payout_status == Earning.PayoutStatus.PENDING
        assert job.completed_at is not None

    def test_uncompleted_job_cannot_create_earning(self, creator_factory, rule, admin):
        creator = creator_factory("c2@test.local")
        job = make_job(creator, status=Job.Status.IN_PROGRESS, completed_at=None)
        with pytest.raises(BusinessError) as exc:
            create_earning_for_completed_job(job, actor=admin)
        assert exc.value.code == "JOB_NOT_COMPLETED"

    def test_double_completion_rejected(self, creator_factory, rule, admin):
        creator = creator_factory("c3@test.local")
        job = make_job(creator, status=Job.Status.PENDING, completed_at=None)
        complete_job(job=job, actor=admin)
        with pytest.raises(BusinessError) as exc:
            complete_job(job=job, actor=admin)
        assert exc.value.code == "INVALID_STATUS_TRANSITION"
        assert Earning.objects.filter(job=job).count() == 1

    def test_cancelled_job_cannot_be_completed(self, creator_factory, rule, admin):
        creator = creator_factory("c4@test.local")
        job = make_job(creator, status=Job.Status.CANCELLED, completed_at=None)
        with pytest.raises(BusinessError) as exc:
            complete_job(job=job, actor=admin)
        assert exc.value.code == "INVALID_STATUS_TRANSITION"

    def test_no_active_rule_means_zero_fee(self, creator_factory, admin):
        creator = creator_factory("c5@test.local")
        job = make_job(creator, base="100", surge="1.00", tip="0")
        earning = create_earning_for_completed_job(job, actor=admin)
        assert earning.platform_fee == Decimal("0.00")
        assert earning.net_amount == Decimal("100.00")


@pytest.mark.django_db
class TestAdjustments:
    def test_negative_adjustment_updates_net(self, creator_factory, rule, admin):
        creator = creator_factory("c6@test.local")
        job = make_job(creator, base="615", surge="1.00", tip="0")
        earning = create_earning_for_completed_job(job, actor=admin)
        before = earning.net_amount

        adjustment = add_adjustment(earning=earning, amount=Decimal("-5.00"),
                                    reason="refund", actor=admin)
        earning.refresh_from_db()
        assert isinstance(adjustment, Adjustment)
        assert earning.adjustment_amount == Decimal("-5.00")
        assert earning.net_amount == before - Decimal("5.00")

    def test_positive_adjustment_allowed(self, creator_factory, rule, admin):
        creator = creator_factory("c7@test.local")
        earning = create_earning_for_completed_job(
            make_job(creator, base="100"), actor=admin)
        add_adjustment(earning=earning, amount=Decimal("25.00"),
                       reason="bonus", actor=admin)
        earning.refresh_from_db()
        assert earning.net_amount == Decimal("90.00") + Decimal("25.00")

    def test_adjustment_cannot_make_net_negative(self, creator_factory, rule, admin):
        creator = creator_factory("c8@test.local")
        earning = create_earning_for_completed_job(
            make_job(creator, base="10"), actor=admin)
        with pytest.raises(BusinessError):
            add_adjustment(earning=earning, amount=Decimal("-50.00"),
                           reason="too much", actor=admin)

    def test_adjustments_stacked(self, creator_factory, rule, admin):
        creator = creator_factory("c9@test.local")
        earning = create_earning_for_completed_job(
            make_job(creator, base="100"), actor=admin)
        add_adjustment(earning=earning, amount=Decimal("-5.00"), reason="r1", actor=admin)
        add_adjustment(earning=earning, amount=Decimal("-2.50"), reason="r2", actor=admin)
        earning.refresh_from_db()
        assert earning.adjustment_amount == Decimal("-7.50")
        assert earning.net_amount == Decimal("90.00") - Decimal("7.50")
