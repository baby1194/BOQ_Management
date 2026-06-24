"""Track calculation-sheet section numbers that are not in the BOQ list."""

from __future__ import annotations

import logging
from typing import Dict, Iterable, List

from sqlalchemy.orm import Session

from models import models

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
