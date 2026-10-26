"""Shared quantity precision (concentration / calculation sheets / BOQ qty columns)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

QUANTITY_DECIMALS = 2


def round_quantity(value: Any) -> float:
    """Round a quantity half-up to the standard precision.

    1.125 becomes 1.13. Python's built-in round() would leave that as 1.12.
    A calculation-sheet float a hair under 0.835 is the same shown value and
    becomes 0.84, not 0.83.
    """
    try:
        if value is None or isinstance(value, bool):
            return 0.0
        if isinstance(value, str):
            text = value.strip().replace(",", "")
            if not text:
                return 0.0
            number = Decimal(text)
        elif isinstance(value, int):
            number = Decimal(value)
        else:
            # Excel stores 0.835 as a binary float that can stringify to
            # 0.8349999999999999. Snap that dust before the two-decimal step.
            number = Decimal(str(value)).quantize(
                Decimal("0.00000001"), rounding=ROUND_HALF_UP
            )
        if not number.is_finite():
            return 0.0
    except (TypeError, ValueError, InvalidOperation, ArithmeticError):
        return 0.0
    step = Decimal(10) ** -QUANTITY_DECIMALS
    return float(number.quantize(step, rounding=ROUND_HALF_UP))


def boq_has_non_zero_psq(submitted: Any, approved: Any) -> bool:
    """True when submitted and approved differ on the printed two decimals.

    Extra digits must not keep an item whose PDF shows the same quantity twice.
    """
    submitted_qty = round_quantity(submitted)
    return submitted_qty > 0 and submitted_qty != round_quantity(approved)
