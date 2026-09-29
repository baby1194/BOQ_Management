"""Which calculation sheets contain a contract system's section numbers."""

from typing import Iterable, List, Sequence, Tuple


def sheet_ids_for_system(
    boq_rows: Iterable[Tuple[str, str]],
    entry_rows: Iterable[Tuple[int, str]],
    system_name: str,
) -> List[int]:
    target = (system_name or "").strip().casefold()
    if not target:
        return []
    sections = {
        (section or "").strip()
        for section, system in boq_rows
        if section and (system or "").strip().casefold() == target
    }
    if not sections:
        return []
    found = {
        sheet_id
        for sheet_id, section in entry_rows
        if sheet_id is not None and (section or "").strip() in sections
    }
    return sorted(found)


def load_sheet_ids_for_system(db, system_name: str) -> List[int]:
    from models import models

    boq_rows: Sequence[Tuple[str, str]] = (
        db.query(models.BOQItem.section_number, models.BOQItem.system).all()
    )
    entry_rows: Sequence[Tuple[int, str]] = db.query(
        models.CalculationEntry.calculation_sheet_id,
        models.CalculationEntry.section_number,
    ).all()
    return sheet_ids_for_system(boq_rows, entry_rows, system_name)
