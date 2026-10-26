"""Shared quantity precision (concentration / calculation sheets / BOQ qty columns)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

QUANTITY_DECIMALS = 2


def _as_decimal(value: Any) -> Decimal:
    if value is None or isinstance(value, bool):
        return Decimal("0")
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        if not text:
            return Decimal("0")
        return Decimal(text)
    if isinstance(value, int):
        return Decimal(value)
    # Excel stores 0.835 as a binary float that can stringify to
    # 0.8349999999999999. Snap that dust before the decimal steps.
    return Decimal(str(value)).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)


def round_quantity(value: Any) -> float:
    """Round a quantity half-up to the standard two decimals.

    The sheet often shows three decimals (0.835). Round that shown third
    decimal first, then to two places, so 0.8345 and 0.835 both become 0.84.
    A direct two-decimal round of 0.8345 would stay 0.83.
    """
    try:
        number = _as_decimal(value)
        if not number.is_finite():
            return 0.0
        number = number.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
        number = number.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (TypeError, ValueError, InvalidOperation, ArithmeticError):
        return 0.0
    return float(number)


def sum_quantities(values) -> float:
    """Add quantities on exact cents. A float sum can drift by 0.01."""
    total = Decimal("0")
    for value in values:
        total += Decimal(str(round_quantity(value)))
    return float(total)


def boq_has_non_zero_psq(submitted: Any, approved: Any) -> bool:
    """True when submitted and approved differ on the printed two decimals.

    Extra digits must not keep an item whose PDF shows the same quantity twice.
    """
    submitted_qty = round_quantity(submitted)
    return submitted_qty > 0 and submitted_qty != round_quantity(approved)
