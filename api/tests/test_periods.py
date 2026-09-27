"""
Weekly payout period maths — pure functions, no database.

Fixed calendar dates rather than "today", so these stay deterministic on any
day of the week and in any timezone.
"""
from datetime import date

import pytest

from apps.payouts.services import last_completed_week, week_bounds


class TestWeekBounds:
    @pytest.mark.parametrize(
        "day",
        [
            date(2026, 9, 21),
            date(2026, 9, 24),
            date(2026, 9, 27),
        ],
    )
    def test_any_day_maps_to_its_monday_sunday_week(self, day):
        start, end = week_bounds(day)
        assert (start, end) == (date(2026, 9, 21), date(2026, 9, 27))
        assert start.weekday() == 0 and end.weekday() == 6

    def test_week_spans_exactly_seven_days(self):
        start, end = week_bounds(date(2026, 9, 24))
        assert (end - start).days == 6


class TestLastCompletedWeek:
    @pytest.mark.parametrize(
        ("today", "expected"),
        [
            (date(2026, 9, 24), (date(2026, 9, 14), date(2026, 9, 20))),
            (date(2026, 9, 21), (date(2026, 9, 14), date(2026, 9, 20))),
            (date(2026, 9, 27), (date(2026, 9, 14), date(2026, 9, 20))),
            (date(2026, 1, 2), (date(2025, 12, 22), date(2025, 12, 28))),
        ],
    )
    def test_returns_the_most_recent_finished_week(self, today, expected):
        assert last_completed_week(today) == expected

    def test_period_always_ends_before_today(self):
        for day in (date(2026, 3, 1), date(2026, 3, 2), date(2026, 7, 15)):
            _, end = last_completed_week(day)
            assert end < day
