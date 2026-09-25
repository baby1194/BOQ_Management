"""Helpers for contract-quantity update badges and comparisons."""

from __future__ import annotations

from typing import Any, Optional


def quantities_differ(left: Any, right: Any, epsilon: float = 1e-9) -> bool:
    try:
        return abs(float(left or 0) - float(right or 0)) > epsilon
    except (TypeError, ValueError):
        return True


def resolved_contract_quantity_for_new_update(
    *,
    original_quantity: Any,
    price: Any,
    previous_updated_quantity: Any | None,
    previous_updated_sum: Any | None = None,
) -> tuple[float, float]:
    """Seed a new contract-update row from the previous update, or from original qty."""
    if previous_updated_quantity is not None:
        qty = float(previous_updated_quantity or 0)
        if previous_updated_sum is not None:
            return qty, float(previous_updated_sum or 0)
        return qty, qty * float(price or 0)
    qty = float(original_quantity or 0)
    unit_price = float(price or 0)
    return qty, qty * unit_price


def has_changed_contract_quantity(
    *,
    original_quantity: Any,
    latest_quantity: Any | None,
    previous_quantity: Any | None,
    has_latest_row: bool,
) -> bool:
    """True when the newest contract qty differs from the quantity before it."""
    if not has_latest_row or latest_quantity is None:
        return False
    baseline = (
        previous_quantity if previous_quantity is not None else original_quantity
    )
    return quantities_differ(latest_quantity, baseline)
