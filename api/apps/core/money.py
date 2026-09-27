from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
ZERO = Decimal("0.00")
ONE_HUNDRED = Decimal("100")


def to_money(value: Decimal | int | str) -> Decimal:
    """Quantize any Decimal-compatible value to 2dp using ROUND_HALF_UP."""
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_earning_amounts(
    base_amount: Decimal,
    surge_multiplier: Decimal,
    tip_amount: Decimal,
    fee_percentage: Decimal,
    adjustment_amount: Decimal = ZERO,
) -> dict[str, Decimal]:
    """
    Pure calculation of earning amounts. No DB access — easy to unit test.

    Returns every component as a 2dp Decimal.
    """
    base_amount = to_money(base_amount)
    tip_amount = to_money(tip_amount)
    adjustment_amount = to_money(adjustment_amount)
    surge_multiplier = Decimal(str(surge_multiplier))
    fee_percentage = Decimal(str(fee_percentage))

    if base_amount < 0 or tip_amount < 0:
        raise ValueError("base_amount and tip_amount must not be negative")
    if surge_multiplier < Decimal("1"):
        raise ValueError("surge_multiplier must be >= 1.00")
    if fee_percentage < 0 or fee_percentage > ONE_HUNDRED:
        raise ValueError("fee_percentage must be between 0 and 100")

    surge_amount = to_money(base_amount * surge_multiplier)
    gross_amount = to_money(surge_amount + tip_amount)
    platform_fee = to_money(gross_amount * fee_percentage / ONE_HUNDRED)
    net_amount = to_money(gross_amount - platform_fee + adjustment_amount)

    return {
        "base_amount": base_amount,
        "surge_amount": surge_amount,
        "tip_amount": tip_amount,
        "gross_amount": gross_amount,
        "platform_fee": platform_fee,
        "adjustment_amount": adjustment_amount,
        "net_amount": net_amount,
    }
