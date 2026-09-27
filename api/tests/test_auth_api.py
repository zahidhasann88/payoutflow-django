"""Integration tests: login, token refresh and suspended-account lockout."""
import pytest

from apps.accounts.models import User
from tests.conftest import PASSWORD, auth, make_creator


@pytest.mark.django_db
class TestAuthAPI:
    def test_login_returns_tokens_and_user(self, client_, admin):
        r = client_.post("/api/auth/login/",
                         {"email": "admin@test.local", "password": PASSWORD}, format="json")
        assert r.status_code == 200
        body = r.json()
        assert body["access"] and body["refresh"]
        assert body["user"]["role"] == "ADMIN"
        assert "password" not in body["user"]

    def test_login_wrong_password(self, client_, admin):
        r = client_.post("/api/auth/login/",
                         {"email": "admin@test.local", "password": "nope"}, format="json")
        assert r.status_code == 401
        assert r.json()["code"] == "INVALID_CREDENTIALS"
        assert r.json()["success"] is False

    def test_suspended_account_cannot_login(self, client_, db):
        User.objects.create_user(email="sus@test.local", password=PASSWORD,
                                 name="Sus", role=User.Role.ADMIN,
                                 status=User.Status.SUSPENDED)
        r = client_.post("/api/auth/login/",
                         {"email": "sus@test.local", "password": PASSWORD}, format="json")
        assert r.status_code == 403
        assert r.json()["code"] == "ACCOUNT_SUSPENDED"

    def test_refresh_token(self, client_, admin):
        r = client_.post("/api/auth/login/",
                         {"email": "admin@test.local", "password": PASSWORD}, format="json")
        refresh = r.json()["refresh"]
        r2 = client_.post("/api/auth/refresh/", {"refresh": refresh}, format="json")
        assert r2.status_code == 200
        assert r2.json()["access"]

    def test_me_requires_auth(self, client_, db):
        assert client_.get("/api/auth/me/").status_code == 401

    def test_me_returns_profile(self, client_, admin):
        auth(client_, admin)
        r = client_.get("/api/auth/me/")
        assert r.status_code == 200
        assert r.json()["data"]["email"] == "admin@test.local"

    def test_login_is_rate_limited(self, client_, admin):
        for _ in range(12):
            client_.post("/api/auth/login/",
                         {"email": "admin@test.local", "password": "bad"}, format="json")
        r = client_.post("/api/auth/login/",
                         {"email": "admin@test.local", "password": "bad"}, format="json")
        assert r.status_code == 429
        assert r.json()["code"] == "THROTTLED"

@pytest.mark.django_db
class TestSuspendedAccountAccess:
    """A suspended account holding a still-valid JWT must be locked out."""

    def _suspend(self, user):
        user.status = User.Status.SUSPENDED
        user.save(update_fields=["status"])

    def test_suspended_creator_blocked_from_dashboard(self, client_, db, rule):
        creator = make_creator("susp1@test.local")
        self._suspend(creator.user)
        auth(client_, creator.user)
        r = client_.get("/api/dashboard/creator/")
        assert r.status_code == 403
        assert r.json()["code"] == "UNAUTHORIZED_ACCESS"

    def test_suspended_creator_blocked_from_financial_endpoints(self, client_, db, rule):
        creator = make_creator("susp2@test.local")
        self._suspend(creator.user)
        auth(client_, creator.user)
        for url in ["/api/jobs/", "/api/earnings/", "/api/payouts/", "/api/creators/"]:
            assert client_.get(url).status_code == 403, url

    def test_suspended_admin_blocked_from_admin_dashboard(self, client_, admin):
        self._suspend(admin)
        auth(client_, admin)
        assert client_.get("/api/dashboard/admin/").status_code == 403


@pytest.mark.django_db
class TestRefreshTokenRevocation:
    """Logout must actually end the session, not just clear cookies."""

    def _login(self, client_):
        r = client_.post("/api/auth/login/",
                         {"email": "admin@test.local", "password": PASSWORD},
                         format="json")
        assert r.status_code == 200
        return r.json()["refresh"]

    def test_logout_revokes_the_presented_refresh_token(self, client_, admin):
        refresh = self._login(client_)
        assert client_.post("/api/auth/refresh/", {"refresh": refresh},
                            format="json").status_code == 200

        fresh = self._login(client_)
        auth(client_, admin)
        r = client_.post("/api/auth/logout/", {"refresh": fresh}, format="json")
        assert r.status_code == 200
        assert r.json()["data"]["revoked_tokens"] == 1

        client_.force_authenticate(user=None)
        assert client_.post("/api/auth/refresh/", {"refresh": fresh},
                            format="json").status_code == 401

    def test_logout_without_a_token_revokes_every_session(self, client_, admin):
        first = self._login(client_)
        second = self._login(client_)

        auth(client_, admin)
        r = client_.post("/api/auth/logout/", {}, format="json")
        assert r.status_code == 200
        assert r.json()["data"]["revoked_tokens"] >= 2

        client_.force_authenticate(user=None)
        for token in (first, second):
            assert client_.post("/api/auth/refresh/", {"refresh": token},
                                format="json").status_code == 401

    def test_rotated_refresh_token_is_blacklisted(self, client_, admin):
        """ROTATE_REFRESH_TOKENS alone leaves the old token usable for its full life."""
        original = self._login(client_)
        rotated = client_.post("/api/auth/refresh/", {"refresh": original},
                               format="json").json()["refresh"]
        assert rotated != original

        assert client_.post("/api/auth/refresh/", {"refresh": original},
                            format="json").status_code == 401
        assert client_.post("/api/auth/refresh/", {"refresh": rotated},
                            format="json").status_code == 200
