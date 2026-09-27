"""Integration tests: the job lifecycle over HTTP, including who may create work."""
import pytest

from apps.accounts.models import User
from apps.jobs.models import Job
from tests.conftest import auth, make_creator, make_job


@pytest.mark.django_db
class TestJobsAPI:
    def test_admin_completes_job_and_earning_appears(self, client_, admin, rule):
        creator = make_creator("j1@test.local")
        job = make_job(creator, base="100", surge="1.5", tip="10",
                       status=Job.Status.PENDING, completed_at=None)
        auth(client_, admin)
        r = client_.post(f"/api/jobs/{job.id}/complete/", {}, format="json")
        assert r.status_code == 200
        e = client_.get("/api/earnings/").json()["results"][0]
        assert e["gross_amount"] == "160.00"
        assert e["platform_fee"] == "16.00"
        assert e["net_amount"] == "144.00"

    def test_complete_twice_conflicts(self, client_, admin, rule):
        creator = make_creator("j2@test.local")
        job = make_job(creator, status=Job.Status.PENDING, completed_at=None)
        auth(client_, admin)
        client_.post(f"/api/jobs/{job.id}/complete/", {}, format="json")
        r = client_.post(f"/api/jobs/{job.id}/complete/", {}, format="json")
        assert r.status_code == 409
        assert r.json()["code"] == "INVALID_STATUS_TRANSITION"

    def test_job_validation(self, client_, admin, rule):
        creator = make_creator("j3@test.local")
        auth(client_, admin)
        r = client_.post("/api/jobs/", {
            "creator": creator.id, "title": "x", "base_amount": "-5",
            "surge_multiplier": "1.0", "tip_amount": "0"}, format="json")
        assert r.status_code == 400
        assert r.json()["code"] == "VALIDATION_ERROR"

        r = client_.post("/api/jobs/", {
            "creator": creator.id, "title": "x", "base_amount": "5",
            "surge_multiplier": "0.5", "tip_amount": "0"}, format="json")
        assert r.status_code == 400

    def test_creator_cannot_complete_jobs(self, client_, db, rule):
        creator = make_creator("j4@test.local")
        job = make_job(creator, status=Job.Status.PENDING, completed_at=None)
        auth(client_, creator.user)
        r = client_.post(f"/api/jobs/{job.id}/complete/", {}, format="json")
        assert r.status_code == 403

    def test_creator_cannot_create_jobs(self, client_, db, rule):
        """A creator must not be able to mint their own paid work (§5)."""
        creator = make_creator("j5@test.local")
        auth(client_, creator.user)
        r = client_.post("/api/jobs/", {
            "creator": creator.id, "title": "self-assigned",
            "base_amount": "9999.00", "surge_multiplier": "1.00",
            "tip_amount": "0"}, format="json")
        assert r.status_code == 403
        assert r.json()["code"] == "UNAUTHORIZED_ACCESS"
        assert Job.objects.filter(creator=creator).count() == 0

    def test_creator_cannot_create_job_for_someone_else(self, client_, db, rule):
        a = make_creator("j6@test.local")
        b = make_creator("j7@test.local")
        auth(client_, a.user)
        r = client_.post("/api/jobs/", {
            "creator": b.id, "title": "not mine", "base_amount": "100.00",
            "surge_multiplier": "1.00", "tip_amount": "0"}, format="json")
        assert r.status_code == 403
        assert Job.objects.filter(creator=b).count() == 0

    def test_job_for_suspended_creator_rejected(self, client_, admin, rule):
        creator = make_creator("j8@test.local")
        creator.user.status = User.Status.SUSPENDED
        creator.user.save(update_fields=["status"])
        auth(client_, admin)
        r = client_.post("/api/jobs/", {
            "creator": creator.id, "title": "x", "base_amount": "100.00",
            "surge_multiplier": "1.00", "tip_amount": "0"}, format="json")
        assert r.status_code == 400
        assert r.json()["code"] == "VALIDATION_ERROR"
