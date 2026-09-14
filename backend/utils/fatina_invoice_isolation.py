"""Keep Fatina invoice folders isolated per item on a shared calculation sheet."""

from __future__ import annotations

from typing import Any, Iterable


def invoices_exclusive_to_other_items(
    calc_entries: Iterable[Any], section_number: str
) -> set[str]:
    """Invoices that appear only as another item's current invoice on the same sheet."""
    own: set[str] = set()
    other: set[str] = set()
    section_number = str(section_number or "").strip()
    for calc_entry in calc_entries:
        current = str(getattr(calc_entry, "current_invoice_id", "") or "").strip()
        if not current:
            continue
        if str(getattr(calc_entry, "section_number", "") or "").strip() == section_number:
            own.add(current)
        else:
            other.add(current)
    return other - own
