"""Shared fixtures for the PayoutFlow test suite."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.creators.models import Creator
from apps.jobs.models import Job
from apps.payouts.models import PayoutRule

PASSWORD = "Test!2345pass"


@pytest.fixture(autouse=True)
def _reset_throttles():
    """
    DRF throttle counters live in the default LocMemCache, which outlives a test.
    Without this the suite is order-dependent: test_login_is_rate_limited exhausts
    the ``login`` bucket (shared by login and refresh) for everything after it.
    """
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def client_() -> APIClient:
    return APIClient()


def auth(client: APIClient, user) -> APIClient:
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def admin(db) -> User:
    return User.objects.create_superuser(
        email="admin@test.local", password=PASSWORD, name="Test Admin"
    )


@pytest.fixture
def rule(db) -> PayoutRule:
    return PayoutRule.objects.create(
        name="Test Weekly 10%",
        platform_fee_percentage=Decimal("10.00"),
        minimum_payout=Decimal("20.00"),
        payout_frequency=PayoutRule.Frequency.WEEKLY,
        is_active=True,
    )


def make_creator(email: str, name: str = "Creator", **kwargs) -> Creator:
    user = User.objects.create_user(
        email=email, password=PASSWORD, name=name, role=User.Role.CREATOR
    )
    return Creator.objects.create(user=user, display_name=kwargs.pop("display_name", name), **kwargs)


@pytest.fixture
def creator_factory(db):
    return make_creator


def make_job(creator, *, base="100.00", surge="1.00", tip="0.00",
             status=Job.Status.COMPLETED, completed_at=None, title="Job") -> Job:
    return Job.objects.create(
        creator=creator,
        title=title,
        status=status,
        base_amount=Decimal(base),
        surge_multiplier=Decimal(surge),
        tip_amount=Decimal(tip),
        completed_at=completed_at or timezone.now(),
    )


@pytest.fixture
def job_factory(db):
    return make_job


def last_week_range(today: date | None = None) -> tuple[date, date]:
    from apps.payouts.services import last_completed_week

    return last_completed_week(today or timezone.localdate())


def in_period_datetime(period: tuple[date, date] | None = None) -> datetime:
    """A timezone-aware datetime safely inside the last completed week."""
    start, _ = period or last_week_range()
    return timezone.make_aware(datetime.combine(start + timedelta(days=2), time(12, 0)))
