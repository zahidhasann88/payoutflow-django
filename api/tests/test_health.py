"""The health endpoint gates the Docker HEALTHCHECK and Compose's service_healthy."""
from unittest.mock import patch

import pytest


@pytest.mark.django_db
class TestHealth:
    def test_reports_ok_when_the_database_answers(self, client_):
        r = client_.get("/api/health/")
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert body["status"] == "ok"
        assert body["database"] == "ok"

    def test_needs_no_authentication(self, client_):
        assert client_.get("/api/health/").status_code == 200

    def test_reports_503_when_the_database_is_unreachable(self, client_):
        """
        A static 200 would let the container report healthy while unable to serve,
        and Compose would start the frontend against a dead backend.
        """
        with patch("apps.core.views.connection.cursor",
                   side_effect=OSError("connection refused")):
            r = client_.get("/api/health/")
        assert r.status_code == 503
        body = r.json()
        assert body["success"] is False
        assert body["status"] == "unavailable"
        assert body["database"] == "unreachable"
