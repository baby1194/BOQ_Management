"""Compare calculation-sheet totals with the quantities stored on BOQ items."""

from typing import Dict, List, Tuple

TOLERANCE = 0.01

SheetTotals = Dict[str, Tuple[float, float]]


def _round3(value: float) -> float:
    return round(float(value or 0), 3)


def quantity_mismatches(
    sheet_totals: SheetTotals,
    boq_totals: SheetTotals,
) -> List[dict]:
    """Rows where sheet calculated or submitted totals differ from the BOQ.

    Each map is section_number -> (calculated quantity, submitted quantity).
    Difference is sheet minus system, rounded to 3 decimals.
    A row is a mismatch when either absolute difference is at least 0.01.
    """
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
            }
        )
    return rows


def mismatches_from_db(db) -> List[dict]:
    from models import models

    sheet_totals: SheetTotals = {}
    for entry in db.query(models.CalculationEntry).all():
        calculated, submitted = sheet_totals.get(entry.section_number, (0.0, 0.0))
        sheet_totals[entry.section_number] = (
            calculated + float(entry.estimated_quantity or 0),
            submitted + float(entry.quantity_submitted or 0),
        )

    boq_totals: SheetTotals = {}
    for item in db.query(models.BOQItem).all():
        boq_totals[item.section_number] = (
            float(item.estimated_quantity or 0),
            float(item.quantity_submitted or 0),
        )
    return quantity_mismatches(sheet_totals, boq_totals)
