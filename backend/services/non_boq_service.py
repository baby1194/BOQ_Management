"""Track calculation-sheet section numbers that are not in the BOQ list."""

from __future__ import annotations

import logging
from typing import Dict, Iterable, List

from sqlalchemy.orm import Session

from models import models


def get_calculation_sheet_nos_by_section(
    db: Session,
    section_numbers: Iterable[str],
) -> dict[str, list[str]]:
    """Map section numbers to distinct calculation sheet numbers from calc entries."""
    normalized = {
        n for n in (_normalize_section_number(s) for s in section_numbers) if n
    }
    if not normalized:
        return {}

    rows = (
        db.query(
            models.CalculationEntry.section_number,
            models.CalculationSheet.calculation_sheet_no,
        )
        .join(
            models.CalculationSheet,
            models.CalculationEntry.calculation_sheet_id == models.CalculationSheet.id,
        )
        .filter(models.CalculationEntry.section_number.in_(normalized))
        .order_by(models.CalculationSheet.calculation_sheet_no.asc())
        .all()
    )

    result: dict[str, set[str]] = {section: set() for section in normalized}
    for section_number, calc_sheet_no in rows:
        key = _normalize_section_number(section_number)
        if key and calc_sheet_no:
            result.setdefault(key, set()).add(str(calc_sheet_no).strip())

    return {key: sorted(values) for key, values in result.items()}


def build_non_boq_export_rows(items: Iterable[Dict]) -> list[dict]:
    """Flatten non-BOQ items into export rows with No, item_no, and calc_sheet_no."""
    rows: list[dict] = []
    row_no = 1
    for item in items:
        section_number = item.get("section_number", "")
        sheet_nos = item.get("calculation_sheet_nos") or []
        if not sheet_nos:
            rows.append(
                {
                    "no": row_no,
                    "item_no": section_number,
                    "calc_sheet_no": "",
                }
            )
            row_no += 1
            continue
        for calc_sheet_no in sheet_nos:
            rows.append(
                {
                    "no": row_no,
                    "item_no": section_number,
                    "calc_sheet_no": calc_sheet_no,
                }
            )
            row_no += 1
    return rows


def list_non_boq_items_with_calc_sheets(db: Session) -> list[dict]:
    """Return non-BOQ items enriched with related calculation sheet numbers."""
    items = (
        db.query(models.NonBoqItem)
        .order_by(models.NonBoqItem.section_number.asc())
        .all()
    )
    sheet_nos_by_section = get_calculation_sheet_nos_by_section(
        db,
        [item.section_number for item in items],
    )
    return [
        {
            "id": item.id,
            "section_number": item.section_number,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "calculation_sheet_nos": sheet_nos_by_section.get(item.section_number, []),
        }
        for item in items
    ]

logger = logging.getLogger(__name__)


def _normalize_section_number(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def register_non_boq_items_from_calculation_entries(
    db: Session,
    entries: Iterable[Dict],
) -> int:
    """
    Add section numbers from calc sheet entries that are not in the BOQ list.
    Returns the number of newly registered items.
    """
    section_numbers: set[str] = set()
    for entry in entries:
        section_number = _normalize_section_number(entry.get("section_number"))
        if section_number:
            section_numbers.add(section_number)

    if not section_numbers:
        return 0

    existing_boq = {
        row[0]
        for row in db.query(models.BOQItem.section_number)
        .filter(models.BOQItem.section_number.in_(section_numbers))
        .all()
    }
    missing_from_boq = section_numbers - existing_boq
    if not missing_from_boq:
        return 0

    existing_non_boq = {
        row[0]
        for row in db.query(models.NonBoqItem.section_number)
        .filter(models.NonBoqItem.section_number.in_(missing_from_boq))
        .all()
    }

    added = 0
    for section_number in sorted(missing_from_boq):
        if section_number in existing_non_boq:
            continue
        db.add(models.NonBoqItem(section_number=section_number))
        added += 1

    if added:
        logger.info("Registered %s new non-BOQ item(s): %s", added, sorted(missing_from_boq))
    return added


def remove_non_boq_item_by_section(db: Session, section_number: str) -> bool:
    """Remove a section from the non-BOQ list (e.g. after adding to BOQ)."""
    normalized = _normalize_section_number(section_number)
    if not normalized:
        return False

    deleted = (
        db.query(models.NonBoqItem)
        .filter(models.NonBoqItem.section_number == normalized)
        .delete()
    )
    return deleted > 0
