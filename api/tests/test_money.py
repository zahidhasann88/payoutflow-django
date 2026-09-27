"""Unit tests for the pure financial calculation layer (Decimal only)."""
from decimal import Decimal

import pytest

from apps.core.money import calculate_earning_amounts, to_money


def amounts(base, surge, tip, fee, adj="0"):
    return calculate_earning_amounts(
        Decimal(base), Decimal(surge), Decimal(tip), Decimal(fee), Decimal(adj)
    )


class TestRounding:
    def test_to_money_half_up(self):
        assert to_money(Decimal("1.005")) == Decimal("1.01")
        assert to_money(Decimal("1.004")) == Decimal("1.00")

    def test_no_floats_in_output(self):
        result = amounts("100", "1.5", "10", "10")
        assert all(isinstance(v, Decimal) for v in result.values())


class TestCalculation:
    def test_spec_example(self):
        """The exact example from the project spec."""
        r = amounts("500", "1.15", "40", "10", adj="-5")
        assert r["surge_amount"] == Decimal("575.00")
        assert r["gross_amount"] == Decimal("615.00")
        assert r["platform_fee"] == Decimal("61.50")
        assert r["net_amount"] == Decimal("548.50")

    def test_simple_500_no_surge(self):
        r = amounts("500", "1.00", "0", "10")
        assert r["gross_amount"] == Decimal("500.00")
        assert r["platform_fee"] == Decimal("50.00")
        assert r["net_amount"] == Decimal("450.00")

    def test_surge_then_tips_order(self):
        """Tips are added AFTER the surge calculation, not surged themselves."""
        r = amounts("100", "1.50", "20", "10")
        assert r["surge_amount"] == Decimal("150.00")
        assert r["gross_amount"] == Decimal("170.00")
        assert r["platform_fee"] == Decimal("17.00")

    def test_fee_rounding_half_up(self):
        r = amounts("100.05", "1.00", "0", "10")
        assert r["platform_fee"] == Decimal("10.01")
        assert r["net_amount"] == Decimal("90.04")

    def test_components_stay_consistent(self):
        """gross == surge + tip and net == gross - fee + adj, exactly."""
        for base, surge, tip, fee, adj in [
            ("99.99", "1.33", "7.77", "12.5", "-3.33"),
            ("0.01", "2.00", "0.01", "33.33", "0"),
            ("1234.56", "1.75", "55.50", "7.25", "10.10"),
        ]:
            r = amounts(base, surge, tip, fee, adj)
            assert r["gross_amount"] == r["surge_amount"] + r["tip_amount"]
            assert r["net_amount"] == (
                r["gross_amount"] - r["platform_fee"] + r["adjustment_amount"]
            )

    def test_zero_fee(self):
        r = amounts("200", "1.00", "0", "0")
        assert r["platform_fee"] == Decimal("0.00")
        assert r["net_amount"] == Decimal("200.00")


class TestValidation:
    def test_negative_base_rejected(self):
        with pytest.raises(ValueError):
            amounts("-1", "1", "0", "10")

    def test_negative_tip_rejected(self):
        with pytest.raises(ValueError):
            amounts("10", "1", "-5", "10")

    def test_surge_below_one_rejected(self):
        with pytest.raises(ValueError):
            amounts("10", "0.5", "0", "10")

    def test_fee_out_of_range_rejected(self):
        with pytest.raises(ValueError):
            amounts("10", "1", "0", "101")
        with pytest.raises(ValueError):
            amounts("10", "1", "0", "-1")
