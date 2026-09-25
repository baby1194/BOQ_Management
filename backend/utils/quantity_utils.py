"""Shared quantity precision (concentration / calculation sheets / BOQ qty columns)."""

from __future__ import annotations

from typing import Any

QUANTITY_DECIMALS = 2


def round_quantity(value: Any) -> float:
    """Round a quantity to the standard display/storage precision."""
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        return 0.0
    return round(number, QUANTITY_DECIMALS)
