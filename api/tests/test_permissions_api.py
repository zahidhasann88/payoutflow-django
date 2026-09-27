"""Integration tests: role-based access control and creator data isolation."""
from decimal import Decimal

import pytest

from tests.conftest import auth, in_period_datetime, make_creator, make_job


@pytest.mark.django_db
class TestPermissions:
    def test_creator_cannot_list_batches(self, client_, db, rule):
        creator = make_creator("perm1@test.local")
        auth(client_, creator.user)
        assert client_.get("/api/payout-batches/").status_code == 403

    def test_creator_cannot_generate_batch(self, client_, db, rule):
        creator = make_creator("perm2@test.local")
        auth(client_, creator.user)
        assert client_.post("/api/payout-batches/generate/", {}, format="json").status_code == 403

    def test_creator_cannot_view_audit_logs(self, client_, db, rule):
        creator = make_creator("perm3@test.local")
        auth(client_, creator.user)
        assert client_.get("/api/audit-logs/").status_code == 403

    def test_creator_cannot_create_payout_rule(self, client_, db, rule):
        creator = make_creator("perm4@test.local")
        auth(client_, creator.user)
        r = client_.post("/api/payout-rules/", {
            "name": "sneaky", "platform_fee_percentage": "0",
            "minimum_payout": "0", "is_active": True}, format="json")
        assert r.status_code == 403

    def test_anonymous_blocked_everywhere(self, client_, db):
        for url in ["/api/creators/", "/api/jobs/", "/api/earnings/",
                    "/api/payouts/", "/api/dashboard/admin/"]:
            assert client_.get(url).status_code in (401, 403)

    def test_creator_dashboard_denied_to_admin(self, client_, admin):
        auth(client_, admin)
        assert client_.get("/api/dashboard/creator/").status_code == 403

@pytest.mark.django_db
class TestCreatorIsolation:
    def test_jobs_scoped_to_own_creator(self, client_, db, rule):
        a = make_creator("iso1@test.local")
        b = make_creator("iso2@test.local")
        make_job(a, title="A job")
        make_job(b, title="B job")

        auth(client_, a.user)
        r = client_.get("/api/jobs/")
        titles = [j["title"] for j in r.json()["results"]]
        assert titles == ["A job"]

    def test_creator_cannot_read_other_creators_job(self, client_, db, rule):
        a = make_creator("iso3@test.local")
        b = make_creator("iso4@test.local")
        job_b = make_job(b)
        auth(client_, a.user)
        r = client_.get(f"/api/jobs/{job_b.id}/")
        assert r.status_code == 404

    def test_creator_cannot_read_other_creators_earnings(self, client_, db, rule):
        from apps.earnings.services import create_earning_for_completed_job
        a = make_creator("iso5@test.local")
        b = make_creator("iso6@test.local")
        earning_b = create_earning_for_completed_job(make_job(b), actor=None)
        auth(client_, a.user)
        assert client_.get(f"/api/earnings/{earning_b.id}/").status_code == 404
        r = client_.get("/api/earnings/")
        assert r.json()["count"] == 0

    def test_creator_payout_history_isolated(self, client_, db, rule):
        from apps.earnings.services import create_earning_for_completed_job
        from apps.payouts.services import generate_payout_batch, last_completed_week
        a = make_creator("iso7@test.local")
        b = make_creator("iso8@test.local")
        dt = in_period_datetime()
        create_earning_for_completed_job(make_job(a, base="100", completed_at=dt), actor=None)
        create_earning_for_completed_job(make_job(b, base="200", completed_at=dt), actor=None)
        s, e = last_completed_week()
        generate_payout_batch(period_start=s, period_end=e, actor=None)

        auth(client_, a.user)
        r = client_.get("/api/payouts/")
        results = r.json()["results"]
        assert len(results) == 1
        assert results[0]["creator_name"] == a.display_name
        assert Decimal(results[0]["net_amount"]) == Decimal("90.00")

    def test_creator_sees_only_self_in_creators_list(self, client_, db, rule):
        a = make_creator("iso9@test.local")
        make_creator("iso10@test.local")
        auth(client_, a.user)
        r = client_.get("/api/creators/")
        assert r.json()["count"] == 1

    def test_creator_cannot_patch_other_profile(self, client_, db, rule):
        a = make_creator("iso11@test.local")
        b = make_creator("iso12@test.local")
        auth(client_, a.user)
        r = client_.patch(f"/api/creators/{b.id}/", {"display_name": "hacked"}, format="json")
        assert r.status_code == 404
        b.refresh_from_db()
        assert b.display_name != "hacked"
