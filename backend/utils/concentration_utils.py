"""Helpers for concentration entry quantity calculations."""

from typing import Iterable, List, Set, Tuple, TypeVar

from utils.calculation_sheet_utils import breakdowns_equal, entry_cumulative_submitted_quantity

T = TypeVar("T")


def entry_cumulative_submitted(entry) -> float:
    """Return cumulative submitted quantity for BOQ aggregation."""
    return entry_cumulative_submitted_quantity(entry)


def filter_concentration_entries_for_export(entries: Iterable[T]) -> List[T]:
    """Exclude entries with zero estimated quantity from concentration sheet exports."""
    return [
        entry
        for entry in entries
        if float(getattr(entry, "estimated_quantity", 0) or 0) != 0
    ]


def compute_quantity_submitted(
    estimated_quantity: float, submission_percentage: float
) -> float:
    """Derive submitted quantity from estimated quantity and submission percentage."""
    return float(estimated_quantity or 0) * (float(submission_percentage or 0) / 100.0)


def compute_submission_percentage(
    estimated_quantity: float, quantity_submitted: float
) -> float:
    """Derive submission percentage from estimated quantity and submitted quantity."""
    estimated = float(estimated_quantity or 0)
    submitted = float(quantity_submitted or 0)
    if estimated > 0:
        return (submitted / estimated) * 100.0
    return 100.0


def apply_calculation_entry_quantities(
    concentration_entry, calc_entry, *, drawing_no: str | None = None
) -> None:
    """Copy estimated/submitted quantities from a calc entry and derive submission percentage."""
    estimated = float(calc_entry.estimated_quantity or 0)
    submitted = float(calc_entry.quantity_submitted or 0)
    concentration_entry.estimated_quantity = estimated
    concentration_entry.quantity_submitted = submitted
    concentration_entry.submission_percentage = compute_submission_percentage(
        estimated, submitted
    )
    concentration_entry.submission_breakdown = getattr(
        calc_entry, "submission_breakdown", None
    )
    if drawing_no is not None:
        concentration_entry.drawing_no = drawing_no


def remove_orphan_concentration_entries(db, sheet_id: int | None = None) -> Tuple[int, Set[int]]:
    """
    Delete concentration entries whose calculation_sheet_no is not in the DB.
    Returns (removed_count, affected_boq_item_ids).
    """
    from models import models

    query = db.query(models.ConcentrationEntry)
    if sheet_id is not None:
        query = query.filter(
            models.ConcentrationEntry.concentration_sheet_id == sheet_id
        )

    entries = query.all()
    if not entries:
        return 0, set()

    existing_calc_nos = {
        str(row[0]).strip()
        for row in db.query(models.CalculationSheet.calculation_sheet_no).all()
        if row[0] and str(row[0]).strip()
    }

    affected_boq_item_ids: Set[int] = set()
    removed = 0
    for entry in entries:
        calc_no = str(entry.calculation_sheet_no or "").strip()
        if not calc_no or calc_no in existing_calc_nos:
            continue

        concentration_sheet = (
            db.query(models.ConcentrationSheet)
            .filter(models.ConcentrationSheet.id == entry.concentration_sheet_id)
            .first()
        )
        if concentration_sheet:
            affected_boq_item_ids.add(concentration_sheet.boq_item_id)

        db.delete(entry)
        removed += 1

    if removed:
        db.commit()

    return removed, affected_boq_item_ids


def prune_stale_concentration_entries_for_calc_sheet(
    db,
    calculation_sheet,
    *,
    lookup_calculation_sheet_no: str | None = None,
) -> Tuple[int, Set[int]]:
    """
    Remove auto-synced concentration entries linked to this calc sheet whose section
    is no longer a submitted item on the sheet (e.g. row 2 invoice id cleared).
    Returns (removed_count, affected_boq_item_ids). Does not commit.
    """
    from models import models

    lookup_no = (
        lookup_calculation_sheet_no or calculation_sheet.calculation_sheet_no
    )
    calc_sheet_nos = {
        str(no).strip()
        for no in (lookup_no, calculation_sheet.calculation_sheet_no)
        if no and str(no).strip()
    }
    if not calc_sheet_nos:
        return 0, set()

    calculation_entries = (
        db.query(models.CalculationEntry)
        .filter(
            models.CalculationEntry.calculation_sheet_id == calculation_sheet.id
        )
        .all()
    )
    active_sections = {
        entry.section_number
        for entry in calculation_entries
        if str(getattr(entry, "current_invoice_id", None) or "").strip()
    }

    linked_entries = (
        db.query(models.ConcentrationEntry)
        .filter(models.ConcentrationEntry.calculation_sheet_no.in_(calc_sheet_nos))
        .filter(models.ConcentrationEntry.is_manual.is_(False))
        .all()
    )

    affected_boq_item_ids: Set[int] = set()
    removed = 0
    for entry in linked_entries:
        if entry.section_number in active_sections:
            continue

        concentration_sheet = (
            db.query(models.ConcentrationSheet)
            .filter(models.ConcentrationSheet.id == entry.concentration_sheet_id)
            .first()
        )
        if concentration_sheet:
            affected_boq_item_ids.add(concentration_sheet.boq_item_id)

        db.delete(entry)
        removed += 1

    return removed, affected_boq_item_ids


def concentration_entry_quantities_differ(
    concentration_entry, calc_entry, *, drawing_no: str | None = None
) -> bool:
    """Return True if applying calc entry quantities would change the concentration entry."""
    new_estimated = float(calc_entry.estimated_quantity or 0)
    new_submitted = float(calc_entry.quantity_submitted or 0)
    old_estimated = float(concentration_entry.estimated_quantity or 0)
    old_submitted = float(concentration_entry.quantity_submitted or 0)
    if old_estimated != new_estimated or old_submitted != new_submitted:
        return True
    if drawing_no is not None:
        if str(concentration_entry.drawing_no or "").strip() != str(drawing_no or "").strip():
            return True
    return not breakdowns_equal(
        getattr(concentration_entry, "submission_breakdown", None),
        getattr(calc_entry, "submission_breakdown", None),
    )
