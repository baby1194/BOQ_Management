"""Fill a project with non-BOQ items and the calculation sheets they come from."""

from __future__ import annotations

import copy
from typing import List, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import models
from services.calculation_sheet_sync import push_calculation_sheet_to_concentration_entries

IMPORT_NOTE = "Imported from non-BOQ calculation sheets"
EXCEPTIONAL_STRUCTURE = 99


def _fill_missing_entry_systems(db: Session) -> bool:
    """Read Excel row 4 once for entries that have never stored a system code."""
    from pathlib import Path

    from services.excel_service import ExcelService

    empty_sections = {
        (item.section_number or "").strip()
        for item in db.query(models.BOQItem).all()
        if not (item.system or "").strip()
    }
    empty_sections.discard("")
    if not empty_sections:
        return False
    pending = [
        entry
        for entry in db.query(models.CalculationEntry).all()
        if entry.system is None and (entry.section_number or "").strip() in empty_sections
    ]
    if not pending:
        return False
    by_sheet: dict[int, list] = {}
    updated = False
    for entry in pending:
        by_sheet.setdefault(entry.calculation_sheet_id, []).append(entry)

    reader = ExcelService()
    for sheet_id, entries in by_sheet.items():
        sheet = db.query(models.CalculationSheet).filter(models.CalculationSheet.id == sheet_id).first()
        systems: dict[str, str] = {}
        path = Path(sheet.source_file_path) if sheet and sheet.source_file_path else None
        if path and path.is_file():
            try:
                data = reader.read_calculation_sheet_data(str(path))
                for row in data.get("entries") or []:
                    section = (row.get("section_number") or "").strip()
                    system = (row.get("system") or "").strip()
                    if section and system and section not in systems:
                        systems[section] = system
            except Exception:
                systems = {}
        for entry in entries:
            entry.system = systems.get((entry.section_number or "").strip(), "") or ""
            updated = True
    return updated


def sync_boq_fields_from_calculation_entries(db: Session) -> bool:
    """Fill an empty system and a missing submitted price from the calculation sheet.

    Submitted price is written once. Later edits to the BOQ price leave it as imported.
    Items brought in from non-BOQ sheets get structure 99 and cell C3 as the system
    when those cells are still empty. A main-project upload is left as it was read.
    """
    entries_changed = _fill_missing_entry_systems(db)
    by_section: dict[str, dict] = {}
    for entry in db.query(models.CalculationEntry).all():
        section = (entry.section_number or "").strip()
        if not section:
            continue
        slot = by_section.setdefault(section, {"price": None, "system": None})
        if slot["price"] is None and entry.unit_price is not None:
            slot["price"] = float(entry.unit_price)
        system = (entry.system or "").strip()
        if system and not slot["system"]:
            slot["system"] = system

    imported_sections = {
        (item.section_number or "").strip()
        for item in db.query(models.BOQItem).all()
        if item.notes == IMPORT_NOTE and (item.section_number or "").strip()
    }
    c3_by_section = _system_by_section_from_c3(db, imported_sections)

    changed = False
    for item in db.query(models.BOQItem).all():
        section = (item.section_number or "").strip()
        slot = by_section.get(section)
        from_non_boq = item.notes == IMPORT_NOTE
        if from_non_boq and item.structure is None:
            item.structure = EXCEPTIONAL_STRUCTURE
            changed = True
        if from_non_boq and not (item.system or "").strip() and c3_by_section.get(section):
            item.system = c3_by_section[section]
            changed = True
        if not slot:
            continue
        if item.submitted_price is None and slot["price"] is not None:
            item.submitted_price = slot["price"]
            changed = True
        if (
            not from_non_boq
            and not (item.system or "").strip()
            and slot["system"]
        ):
            item.system = slot["system"]
            changed = True
    if changed or entries_changed:
        db.commit()
    return changed or entries_changed


def _system_by_section_from_c3(source: Session, sections: set[str]) -> dict[str, str]:
    """Cell C3 of the calculation sheet, the first sheet number that has the section."""
    if not sections:
        return {}
    rows = (
        source.query(
            models.CalculationEntry.section_number,
            models.CalculationSheet.description,
        )
        .join(
            models.CalculationSheet,
            models.CalculationEntry.calculation_sheet_id == models.CalculationSheet.id,
        )
        .filter(models.CalculationEntry.section_number.in_(sections))
        .order_by(
            models.CalculationSheet.calculation_sheet_no.asc(),
            models.CalculationEntry.id.asc(),
        )
        .all()
    )
    found: dict[str, str] = {}
    for section, description in rows:
        text = (description or "").strip()
        if section and text and section not in found:
            found[section] = text
    return found


def _add_boq_items(
    target: Session,
    rows: List[dict],
    start_order: int = 0,
    start_serial: int = 1,
    systems: dict[str, str] | None = None,
) -> None:
    systems = systems or {}
    for offset, row in enumerate(rows):
        item = models.BOQItem(
            display_order=start_order + offset,
            serial_number=start_serial + offset,
            section_number=row["section_number"],
            description=row["description"],
            unit=row["unit"],
            original_contract_quantity=row["quantity"],
            price=row["price"],
            submitted_price=row["price"],
            structure=EXCEPTIONAL_STRUCTURE,
            system=systems.get(row["section_number"]) or None,
            total_contract_sum=row["total"],
            estimated_quantity=row["quantity"],
            total_estimate=row["total"],
            notes=IMPORT_NOTE,
        )
        target.add(item)
        target.flush()
        target.add(
            models.ConcentrationSheet(
                boq_item_id=item.id,
                sheet_name=f"Concentration Sheet - {item.section_number}",
            )
        )


def _next_item_indexes(target: Session) -> Tuple[int, int]:
    max_order = target.query(func.max(models.BOQItem.display_order)).scalar()
    max_serial = target.query(func.max(models.BOQItem.serial_number)).scalar()
    start_order = 0 if max_order is None else int(max_order) + 1
    start_serial = 1 if max_serial is None else int(max_serial) + 1
    return start_order, start_serial


def _clone_calculation_entry(sheet_id: int, entry: models.CalculationEntry) -> models.CalculationEntry:
    return models.CalculationEntry(
        calculation_sheet_id=sheet_id,
        section_number=entry.section_number,
        current_invoice_id=entry.current_invoice_id,
        invoice_description=entry.invoice_description,
        item_description=entry.item_description,
        estimated_quantity=entry.estimated_quantity,
        quantity_submitted=entry.quantity_submitted,
        submission_breakdown=copy.deepcopy(entry.submission_breakdown),
        notes=entry.notes,
        unit_price=entry.unit_price,
        system=entry.system,
    )


def _copy_calculation_sheets(source: Session, target: Session, sections: set[str]) -> int:
    """Copy each sheet that has one of the sections, keeping only those sections' rows.

    A sheet number that already exists in the target keeps its current rows.
    Only the missing sections are added to it.
    """
    if not sections:
        return 0
    sheets = (
        source.query(models.CalculationSheet)
        .join(
            models.CalculationEntry,
            models.CalculationEntry.calculation_sheet_id == models.CalculationSheet.id,
        )
        .filter(models.CalculationEntry.section_number.in_(sections))
        .distinct()
        .order_by(models.CalculationSheet.calculation_sheet_no.asc())
        .all()
    )
    touched = 0
    for sheet in sheets:
        existing_sheet = (
            target.query(models.CalculationSheet)
            .filter(models.CalculationSheet.calculation_sheet_no == sheet.calculation_sheet_no)
            .first()
        )
        if existing_sheet is None:
            dest = models.CalculationSheet(
                file_name=sheet.file_name,
                calculation_sheet_no=sheet.calculation_sheet_no,
                drawing_no=sheet.drawing_no,
                description=sheet.description,
                comment=sheet.comment,
                source_file_path=sheet.source_file_path,
            )
            target.add(dest)
            target.flush()
            present: set[str] = set()
            created = True
        else:
            dest = existing_sheet
            present = {
                row[0]
                for row in target.query(models.CalculationEntry.section_number)
                .filter(models.CalculationEntry.calculation_sheet_id == dest.id)
                .all()
            }
            created = False
        added = False
        for entry in sheet.entries:
            if entry.section_number not in sections or entry.section_number in present:
                continue
            target.add(_clone_calculation_entry(dest.id, entry))
            present.add(entry.section_number)
            added = True
        if created or added:
            target.flush()
            push_calculation_sheet_to_concentration_entries(target, dest)
            touched += 1
    return touched


def fill_non_boq_project(source: Session, target: Session, rows: List[dict]) -> dict:
    """BOQ rows, concentration sheets, and trimmed calculation sheets in the new project."""
    sections = {row["section_number"] for row in rows}
    _add_boq_items(target, rows, systems=_system_by_section_from_c3(source, sections))
    target.flush()
    sheet_count = _copy_calculation_sheets(source, target, sections)
    return {"item_count": len(rows), "calculation_sheet_count": sheet_count}


def add_non_boq_items_to_project(source: Session, target: Session, rows: List[dict]) -> dict:
    """Append items that are not already in the target. Existing rows stay as they are."""
    existing = {
        row[0]
        for row in target.query(models.BOQItem.section_number).all()
        if row[0]
    }
    fresh = [row for row in rows if row["section_number"] not in existing]
    skipped = [row["section_number"] for row in rows if row["section_number"] in existing]
    if not fresh:
        return {
            "item_count": 0,
            "skipped_count": len(skipped),
            "skipped_sections": skipped,
            "calculation_sheet_count": 0,
            "added_sections": [],
        }
    start_order, start_serial = _next_item_indexes(target)
    _add_boq_items(
        target,
        fresh,
        start_order,
        start_serial,
        systems=_system_by_section_from_c3(
            source, {row["section_number"] for row in fresh}
        ),
    )
    target.flush()
    sheet_count = _copy_calculation_sheets(
        source, target, {row["section_number"] for row in fresh}
    )
    return {
        "item_count": len(fresh),
        "skipped_count": len(skipped),
        "skipped_sections": skipped,
        "calculation_sheet_count": sheet_count,
        "added_sections": [row["section_number"] for row in fresh],
    }
