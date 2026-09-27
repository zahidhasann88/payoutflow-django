"""The generate_payouts management command must be safe to run repeatedly."""
from io import StringIO

import pytest
from django.core.management import call_command

from apps.payouts.models import PayoutBatch


@pytest.mark.django_db
class TestGeneratePayoutsCommand:
    def _call(self, *args):
        out = StringIO()
        call_command("generate_payouts", *args, stdout=out)
        return out.getvalue()

    def test_repeated_runs_create_single_batch(self, rule, admin):
        first = self._call()
        assert "created" in first
        second = self._call()
        assert "already exists" in second
        assert PayoutBatch.objects.count() == 1

    def test_explicit_period(self, rule, admin):
        out = self._call("--period-start", "2026-01-05", "--period-end", "2026-01-11")
        assert "created" in out
        batch = PayoutBatch.objects.get()
        assert str(batch.period_start) == "2026-01-05"

    def test_invalid_date_format(self, rule, admin):
        from django.core.management.base import CommandError
        with pytest.raises(CommandError):
            self._call("--period-start", "not-a-date", "--period-end", "2026-01-11")
