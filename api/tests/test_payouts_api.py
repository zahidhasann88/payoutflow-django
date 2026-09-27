"""Integration tests: payout rules, batch generation/processing and listing."""
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.jobs.models import Job
from tests.conftest import auth, in_period_datetime, make_creator, make_job


@pytest.mark.django_db
class TestPayoutAPI:
    def test_generate_and_process_via_api(self, client_, admin, rule):
        creator = make_creator("api1@test.local")
        make_job(creator, base="500", completed_at=in_period_datetime())
        from apps.earnings.services import create_earning_for_completed_job
        create_earning_for_completed_job(Job.objects.get(creator=creator), actor=admin)

        auth(client_, admin)
        r = client_.post("/api/payout-batches/generate/", {}, format="json")
        assert r.status_code == 201
        batch = r.json()
        assert batch["status"] == "READY"
        assert batch["net_amount"] == "450.00"

        r = client_.post(f"/api/payout-batches/{batch['id']}/process/",
                         {"failure_rate": 0}, format="json")
        assert r.status_code == 200
        assert r.json()["status"] == "COMPLETED"
        assert r.json()["paid_count"] == 1

        r = client_.post(f"/api/payout-batches/{batch['id']}/process/", {}, format="json")
        assert r.status_code == 409
        assert r.json()["code"] == "PAYOUT_BATCH_ALREADY_PROCESSED"

    def test_generate_duplicate_via_api(self, client_, admin, rule):
        make_creator("api2@test.local")
        auth(client_, admin)
        r1 = client_.post("/api/payout-batches/generate/", {}, format="json")
        assert r1.status_code == 201
        r2 = client_.post("/api/payout-batches/generate/", {}, format="json")
        assert r2.status_code == 409
        assert r2.json()["code"] == "PAYOUT_BATCH_ALREADY_EXISTS"

@pytest.mark.django_db
class TestPayoutRuleAPI:
    """Regression cover for the single-active-rule switch (§13)."""

    def test_activating_a_rule_deactivates_the_previous_one(self, client_, admin, rule):
        from apps.payouts.models import PayoutRule

        other = PayoutRule.objects.create(
            name="Premium 25%", platform_fee_percentage=Decimal("25.00"),
            minimum_payout=Decimal("20.00"), is_active=False,
        )
        auth(client_, admin)
        r = client_.patch(f"/api/payout-rules/{other.id}/", {"is_active": True},
                          format="json")
        assert r.status_code == 200, r.content
        other.refresh_from_db()
        rule.refresh_from_db()
        assert other.is_active is True
        assert rule.is_active is False
        assert PayoutRule.objects.filter(is_active=True).count() == 1

    def test_creating_an_active_rule_deactivates_the_previous_one(self, client_, admin, rule):
        from apps.payouts.models import PayoutRule

        auth(client_, admin)
        r = client_.post("/api/payout-rules/", {
            "name": "Launch 5%", "platform_fee_percentage": "5.00",
            "minimum_payout": "10.00", "payout_frequency": "WEEKLY",
            "is_active": True}, format="json")
        assert r.status_code == 201, r.content
        rule.refresh_from_db()
        assert rule.is_active is False
        assert PayoutRule.objects.filter(is_active=True).count() == 1

    def test_only_weekly_frequency_accepted(self, client_, admin):
        auth(client_, admin)
        r = client_.post("/api/payout-rules/", {
            "name": "Daily", "platform_fee_percentage": "5.00",
            "minimum_payout": "10.00", "payout_frequency": "DAILY"}, format="json")
        assert r.status_code == 400

    def test_fee_percentage_bounds_enforced(self, client_, admin):
        auth(client_, admin)
        r = client_.post("/api/payout-rules/", {
            "name": "Absurd", "platform_fee_percentage": "150.00",
            "minimum_payout": "10.00", "payout_frequency": "WEEKLY"}, format="json")
        assert r.status_code == 400

@pytest.mark.django_db
class TestPayoutBatchListing:
    def test_batches_listed_newest_period_first(self, client_, admin, rule):
        """The Count() annotations must not clobber the default ordering."""
        from datetime import timedelta

        from apps.payouts.models import PayoutBatch

        base = timezone.localdate() - timedelta(days=90)
        periods = []
        for week in range(4):
            start = base + timedelta(days=7 * week)
            end = start + timedelta(days=6)
            PayoutBatch.objects.create(period_start=start, period_end=end,
                                       status=PayoutBatch.Status.READY)
            periods.append(end)

        auth(client_, admin)
        r = client_.get("/api/payout-batches/")
        assert r.status_code == 200
        returned = [row["period_end"] for row in r.json()["results"]]
        assert returned == [d.isoformat() for d in sorted(periods, reverse=True)]

    def test_batch_counts_are_annotated(self, client_, admin, rule):
        creator = make_creator("cnt1@test.local")
        make_job(creator, base="500", completed_at=in_period_datetime())
        from apps.earnings.services import create_earning_for_completed_job
        from apps.payouts.services import generate_payout_batch, process_payout_batch
        create_earning_for_completed_job(Job.objects.get(creator=creator), actor=admin)
        batch = generate_payout_batch(actor=admin)

        auth(client_, admin)
        row = client_.get("/api/payout-batches/").json()["results"][0]
        assert row["payout_count"] == 1
        assert row["paid_count"] == 0
        assert row["failed_count"] == 0

        process_payout_batch(batch, actor=admin, failure_rate=0.0)
        row = client_.get("/api/payout-batches/").json()["results"][0]
        assert row["paid_count"] == 1
        assert row["failed_count"] == 0

    def test_listing_cost_does_not_grow_with_batch_count(self, client_, admin, rule):
        """
        The serializer's three counts are annotated precisely so a list of N batches
        does not cost 3N queries. Without this, reverting to obj.payouts.count()
        passes every other test while quietly restoring the N+1.
        """
        from datetime import timedelta

        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        from apps.payouts.models import PayoutBatch

        auth(client_, admin)
        base = timezone.localdate() - timedelta(days=365)

        def add_batches(count, offset):
            for week in range(count):
                start = base + timedelta(days=7 * (offset + week))
                PayoutBatch.objects.create(period_start=start,
                                           period_end=start + timedelta(days=6),
                                           status=PayoutBatch.Status.READY)

        def list_batches(expected_rows):
            r = client_.get("/api/payout-batches/")
            assert r.status_code == 200
            assert len(r.json()["results"]) == expected_rows

        add_batches(2, 0)
        with CaptureQueriesContext(connection) as few:
            list_batches(2)

        add_batches(6, 2)
        with CaptureQueriesContext(connection) as many:
            list_batches(8)

        assert len(many.captured_queries) == len(few.captured_queries), (
            f"8 batches cost {len(many.captured_queries)} queries vs "
            f"{len(few.captured_queries)} for 2 - the annotations regressed to an N+1"
        )
