"""Shared quantity precision (concentration / calculation sheets / BOQ qty columns)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

QUANTITY_DECIMALS = 2


def round_quantity(value: Any) -> float:
    """Round a quantity half-up to the standard precision.

    1.125 becomes 1.13. Python's built-in round() would leave that as 1.12.
    """
    try:
        if value is None or isinstance(value, bool):
            return 0.0
        if isinstance(value, str):
            text = value.strip().replace(",", "")
            if not text:
                return 0.0
            number = Decimal(text)
        else:
            number = Decimal(str(value))
        if not number.is_finite():
            return 0.0
    except (TypeError, ValueError, InvalidOperation, ArithmeticError):
        return 0.0
    step = Decimal(10) ** -QUANTITY_DECIMALS
    return float(number.quantize(step, rounding=ROUND_HALF_UP))
