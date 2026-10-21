"""Compare calculation-sheet totals with the quantities stored on BOQ items."""

import logging
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from utils.calculation_sheet_utils import (
    DETAIL_START_ROW,
    FIRST_ITEM_COLUMN_INDEX,
    period_column_index,
)

TOLERANCE = 0.01

# Row 2 of an item column is that item's invoice number. The sheet invoice in
# C2 is not used. Row 5 is the section number. Detail quantities start at row 28.
# The invoice for each detail quantity is the prior column (column B when the
# sheet has one item). Row 24 is not the submitted quantity.
EXCEL_INVOICE_ROW = 2
EXCEL_SECTION_ROW = 5
EXCEL_DETAIL_START_ROW = DETAIL_START_ROW + 1

SheetTotals = Dict[str, Tuple[float, float]]
logger = logging.getLogger(__name__)


def _round3(value: float) -> float:
    return round(float(value or 0), 3)


def quantity_mismatches(
    sheet_totals: SheetTotals,
    boq_totals: SheetTotals,
    manual_sections: Optional[Iterable[str]] = None,
) -> List[dict]:
    """Rows where sheet calculated or submitted totals differ from the BOQ.

    Each map is section_number -> (calculated quantity, submitted quantity).
    Difference is sheet minus system, rounded to 3 decimals.
    A row is a mismatch when either absolute difference is at least 0.01.
    """
    manual = {section for section in (manual_sections or []) if section}
    rows = []
    for section in sorted(set(sheet_totals) | set(boq_totals)):
        sheet_calculated, sheet_submitted = sheet_totals.get(section, (0.0, 0.0))
        system_calculated, system_submitted = boq_totals.get(section, (0.0, 0.0))
        calculated_diff = _round3(sheet_calculated - system_calculated)
        submitted_diff = _round3(sheet_submitted - system_submitted)
        if abs(calculated_diff) < TOLERANCE and abs(submitted_diff) < TOLERANCE:
            continue
        rows.append(
            {
                "section_number": section,
                "sheet_calculated": _round3(sheet_calculated),
                "system_calculated": _round3(system_calculated),
                "calculated_diff": calculated_diff,
                "sheet_submitted": _round3(sheet_submitted),
                "system_submitted": _round3(system_submitted),
                "submitted_diff": submitted_diff,
                "status": "שגיאה/חריגה",
                "has_manual_entries": section in manual,
                "is_non_boq": section not in boq_totals,
            }
        )
    return rows


def _section_text(value) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, float) and value != value:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "<na>", "nat"}:
        return None
    return text


def _cell(rows: Sequence[Sequence], excel_row: int, col: int):
    index = excel_row - 1
    if index < 0 or index >= len(rows):
        return None
    line = rows[index] or ()
    if col < 0 or col >= len(line):
        return None
    return line[col]


def submitted_totals_from_rows(rows: Sequence[Sequence]) -> Dict[str, float]:
    """Sum detail quantities whose prior cell has an invoice number.

    Rows are Excel rows starting at row 1. An item column is included only when
    its own row 2 has an invoice number. C2 is ignored. Each detail quantity
    from row 28 down is added only when the invoice cell in the prior column
    is filled. A line with no invoice, and the row 24 subtotal, are left out.
    """
    from utils.quantity_utils import round_quantity

    rows = rows or ()
    width = max((len(line or ()) for line in rows), default=0)
    item_columns = []
    for col in range(FIRST_ITEM_COLUMN_INDEX, width):
        section = _section_text(_cell(rows, EXCEL_SECTION_ROW, col))
        if section:
            item_columns.append((col, section))

    item_count = len(item_columns)
    totals: Dict[str, float] = {}
    for col, section in item_columns:
        if not _section_text(_cell(rows, EXCEL_INVOICE_ROW, col)):
            continue
        invoice_col = period_column_index(col, item_count)
        quantity = 0.0
        for excel_row in range(EXCEL_DETAIL_START_ROW, len(rows) + 1):
            if not _section_text(_cell(rows, excel_row, invoice_col)):
                continue
            quantity += round_quantity(_cell(rows, excel_row, col))
        totals[section] = totals.get(section, 0.0) + quantity
    return totals


def submitted_by_section_from_workbook(path: str) -> Dict[str, float]:
    """Sum submitted detail quantities from a calculation sheet workbook."""
    from openpyxl import load_workbook

    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        if "Calculation" not in workbook.sheetnames:
            return {}
        worksheet = workbook["Calculation"]
        max_column = worksheet.max_column or None
        rows = list(
            worksheet.iter_rows(max_col=max_column, values_only=True)
        )
        return submitted_totals_from_rows(rows)
    finally:
        workbook.close()


def mismatches_from_db(db) -> List[dict]:
    from pathlib import Path

    from models import models
    from utils.concentration_utils import entry_cumulative_submitted

    calculated_by_section: Dict[str, float] = {}
    for entry in db.query(models.CalculationEntry).all():
        section = entry.section_number
        if not section:
            continue
        calculated_by_section[section] = calculated_by_section.get(
            section, 0.0
        ) + float(entry.estimated_quantity or 0)

    submitted_by_section: Dict[str, float] = {}
    for sheet in db.query(models.CalculationSheet).all():
        path = sheet.source_file_path
        if not path or not Path(path).is_file():
            continue
        try:
            file_totals = submitted_by_section_from_workbook(path)
        except Exception:
            logger.warning(
                "Could not read submitted quantities from %s",
                path,
                exc_info=True,
            )
            continue
        for section, quantity in file_totals.items():
            submitted_by_section[section] = (
                submitted_by_section.get(section, 0.0) + quantity
            )

    sheet_totals: SheetTotals = {}
    for section in set(calculated_by_section) | set(submitted_by_section):
        sheet_totals[section] = (
            calculated_by_section.get(section, 0.0),
            submitted_by_section.get(section, 0.0),
        )

    concentration_submitted: Dict[str, float] = {}
    sections_with_entries = set()
    concentration_rows = (
        db.query(
            models.BOQItem.section_number,
            models.ConcentrationEntry,
        )
        .join(
            models.ConcentrationSheet,
            models.ConcentrationSheet.boq_item_id == models.BOQItem.id,
        )
        .join(
            models.ConcentrationEntry,
            models.ConcentrationEntry.concentration_sheet_id
            == models.ConcentrationSheet.id,
        )
        .all()
    )
    for section, entry in concentration_rows:
        if not section:
            continue
        sections_with_entries.add(section)
        concentration_submitted[section] = concentration_submitted.get(
            section, 0.0
        ) + entry_cumulative_submitted(entry)

    boq_totals: SheetTotals = {}
    for item in db.query(models.BOQItem).all():
        if item.section_number in sections_with_entries:
            submitted = concentration_submitted.get(item.section_number, 0.0)
        else:
            submitted = float(item.quantity_submitted or 0)
        boq_totals[item.section_number] = (
            float(item.estimated_quantity or 0),
            submitted,
        )

    manual_sections = {
        section
        for (section,) in db.query(models.BOQItem.section_number)
        .join(
            models.ConcentrationSheet,
            models.ConcentrationSheet.boq_item_id == models.BOQItem.id,
        )
        .join(
            models.ConcentrationEntry,
            models.ConcentrationEntry.concentration_sheet_id == models.ConcentrationSheet.id,
        )
        .filter(models.ConcentrationEntry.is_manual == True)
        .distinct()
        .all()
        if section
    }
    return quantity_mismatches(sheet_totals, boq_totals, manual_sections)
