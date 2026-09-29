"""Fill a new project with non-BOQ items and the calculation sheets they come from."""

from __future__ import annotations

import copy
from typing import List

from sqlalchemy.orm import Session

from models import models
from services.calculation_sheet_sync import push_calculation_sheet_to_concentration_entries

IMPORT_NOTE = "Imported from non-BOQ calculation sheets"


def _add_boq_items(target: Session, rows: List[dict]) -> None:
    for index, row in enumerate(rows):
        item = models.BOQItem(
            display_order=index,
            serial_number=index + 1,
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


def _copy_calculation_sheets(source: Session, target: Session, sections: set[str]) -> int:
    """Copy each sheet that has one of the sections, keeping only those sections' rows."""
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
    for sheet in sheets:
        new_sheet = models.CalculationSheet(
            file_name=sheet.file_name,
            calculation_sheet_no=sheet.calculation_sheet_no,
            drawing_no=sheet.drawing_no,
            description=sheet.description,
            comment=sheet.comment,
            source_file_path=sheet.source_file_path,
        )
        target.add(new_sheet)
        target.flush()
        for entry in sheet.entries:
            if entry.section_number not in sections:
                continue
            target.add(
                models.CalculationEntry(
                    calculation_sheet_id=new_sheet.id,
                    section_number=entry.section_number,
                    current_invoice_id=entry.current_invoice_id,
                    invoice_description=entry.invoice_description,
                    estimated_quantity=entry.estimated_quantity,
                    quantity_submitted=entry.quantity_submitted,
                    submission_breakdown=copy.deepcopy(entry.submission_breakdown),
                    notes=entry.notes,
                    unit_price=entry.unit_price,
                )
            )
        push_calculation_sheet_to_concentration_entries(target, new_sheet)
    return len(sheets)


def fill_non_boq_project(source: Session, target: Session, rows: List[dict]) -> dict:
    """BOQ rows, concentration sheets, and trimmed calculation sheets in the new project."""
    sections = {row["section_number"] for row in rows}
    _add_boq_items(target, rows)
    target.flush()
    sheet_count = _copy_calculation_sheets(source, target, sections)
    return {"item_count": len(rows), "calculation_sheet_count": sheet_count}
