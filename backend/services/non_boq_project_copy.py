"""Fill a project with non-BOQ items and the calculation sheets they come from."""

from __future__ import annotations

import copy
from typing import List, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import models
from services.calculation_sheet_sync import push_calculation_sheet_to_concentration_entries

IMPORT_NOTE = "Imported from non-BOQ calculation sheets"


def _add_boq_items(
    target: Session,
    rows: List[dict],
    start_order: int = 0,
    start_serial: int = 1,
) -> None:
    for offset, row in enumerate(rows):
        item = models.BOQItem(
            display_order=start_order + offset,
            serial_number=start_serial + offset,
            section_number=row["section_number"],
            description=row["description"],
            unit=row["unit"],
            original_contract_quantity=row["quantity"],
            price=row["price"],
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
    _add_boq_items(target, rows)
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
            "calculation_sheet_count": 0,
            "added_sections": [],
        }
    start_order, start_serial = _next_item_indexes(target)
    _add_boq_items(target, fresh, start_order, start_serial)
    target.flush()
    sheet_count = _copy_calculation_sheets(
        source, target, {row["section_number"] for row in fresh}
    )
    return {
        "item_count": len(fresh),
        "skipped_count": len(skipped),
        "calculation_sheet_count": sheet_count,
        "added_sections": [row["section_number"] for row in fresh],
    }
