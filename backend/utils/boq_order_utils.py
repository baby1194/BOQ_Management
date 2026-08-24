"""BOQ row ordering helpers — keep display_order aligned with serial_number."""

from __future__ import annotations

from typing import Iterable, List, Sequence, TypeVar

from sqlalchemy.orm import Session

from models import models

T = TypeVar("T")


def boq_item_serial_sort_key(item: models.BOQItem) -> tuple:
    """Sort key: serial_number ascending, nulls last, then id."""
    sn = item.serial_number
    if sn is None:
        return (1, 0, item.id)
    return (0, int(sn), item.id)


def boq_item_display_sort_key(item: models.BOQItem) -> tuple:
    """Sort key used by the BOQ table and exports."""
    return (item.display_order, item.id)


def sync_display_orders_by_serial_number(db: Session) -> None:
    """Reassign display_order so rows follow serial_number (nulls last)."""
    items = db.query(models.BOQItem).all()
    items.sort(key=boq_item_serial_sort_key)
    for idx, item in enumerate(items):
        item.display_order = idx


def sort_boq_items_by_display_order(items: Sequence[models.BOQItem]) -> List[models.BOQItem]:
    return sorted(items, key=boq_item_display_sort_key)


def sort_concentration_sheets_by_boq_order(
    sheets: Sequence[models.ConcentrationSheet],
    db: Session,
) -> List[models.ConcentrationSheet]:
    """Order concentration sheets to match BOQ table row order."""
    if not sheets:
        return []

    boq_ids = {sheet.boq_item_id for sheet in sheets}
    boq_items = (
        db.query(models.BOQItem)
        .filter(models.BOQItem.id.in_(boq_ids))
        .all()
    )
    boq_by_id = {item.id: item for item in boq_items}

    def sheet_sort_key(sheet: models.ConcentrationSheet) -> tuple:
        boq = boq_by_id.get(sheet.boq_item_id)
        if boq is None:
            return (999_999, sheet.id)
        return boq_item_display_sort_key(boq)

    return sorted(sheets, key=sheet_sort_key)
