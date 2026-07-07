"""Helpers for concentration entry quantity calculations."""

from typing import Iterable, List, Optional, Set, Tuple, TypeVar

from utils.calculation_sheet_utils import breakdowns_equal, entry_cumulative_submitted_quantity
from utils.period_details_utils import (
    apply_current_period_to_entry_fields,
    merge_breakdown_preserve_period_details,
    migrate_entry_period_details,
    persist_entry_level_fields_to_period,
    resolve_entry_current_period,
)

T = TypeVar("T")


def entry_cumulative_submitted(entry) -> float:
    """Return cumulative submitted quantity for BOQ aggregation."""
    return entry_cumulative_submitted_quantity(entry)


def filter_concentration_entries_for_export(
    entries: Iterable[T],
    entry_columns: Optional[dict] = None,
) -> List[T]:
    """Filter concentration entries for PDF/Excel export.

    When Estimated Quantity is included (default), exclude rows with zero estimated qty.
    When Estimated Quantity is excluded, exclude rows with zero submitted qty instead.
    """
    include_estimated = True
    if entry_columns is not None:
        include_estimated = entry_columns.get("include_estimated_quantity", True)

    filtered: List[T] = []
    for entry in entries:
        estimated = float(getattr(entry, "estimated_quantity", 0) or 0)
        submitted = entry_cumulative_submitted(entry)
        if include_estimated:
            if estimated != 0:
                filtered.append(entry)
        elif submitted != 0:
            filtered.append(entry)
    return filtered


def calc_sheet_nos_submitted_equals_approved(entries: Iterable[T]) -> Set[str]:
    """Return calc sheet numbers whose total submitted qty equals total approved qty."""
    from utils.period_details_utils import entry_total_approved_quantity

    totals: dict[str, dict[str, float]] = {}
    for entry in entries:
        calc_no = str(getattr(entry, "calculation_sheet_no", "") or "").strip()
        if not calc_no:
            continue
        bucket = totals.setdefault(calc_no, {"submitted": 0.0, "approved": 0.0})
        bucket["submitted"] += entry_cumulative_submitted_quantity(entry)
        bucket["approved"] += entry_total_approved_quantity(entry)

    skip: Set[str] = set()
    for calc_no, bucket in totals.items():
        if round(bucket["submitted"], 2) == round(bucket["approved"], 2):
            skip.add(calc_no)
    return skip


def concentration_sheet_cumulative_submitted_equals_approved(
    entries: Iterable[T],
) -> bool:
    """True when total submitted qty equals total approved qty across all entries."""
    from utils.period_details_utils import entry_total_approved_quantity

    total_submitted = 0.0
    total_approved = 0.0
    for entry in entries:
        total_submitted += entry_cumulative_submitted_quantity(entry)
        total_approved += entry_total_approved_quantity(entry)
    return round(total_submitted, 2) == round(total_approved, 2)


def calc_entry_is_submitted(calc_entry) -> bool:
    """True when a calc entry has an invoice id and non-zero submitted quantity."""
    if not str(getattr(calc_entry, "current_invoice_id", None) or "").strip():
        return False
    return entry_cumulative_submitted_quantity(calc_entry) > 0


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
    old_breakdown = getattr(concentration_entry, "submission_breakdown", None)
    outgoing_period = (
        str(concentration_entry.drawing_no or "").strip()
        or resolve_entry_current_period(concentration_entry)
    )
    if outgoing_period:
        persist_entry_level_fields_to_period(
            concentration_entry, outgoing_period, old_breakdown
        )
        old_breakdown = getattr(concentration_entry, "submission_breakdown", None)

    new_breakdown = getattr(calc_entry, "submission_breakdown", None)
    concentration_entry.submission_breakdown = merge_breakdown_preserve_period_details(
        old_breakdown, new_breakdown
    )
    if drawing_no is not None:
        concentration_entry.drawing_no = drawing_no
    migrate_entry_period_details(concentration_entry)
    apply_current_period_to_entry_fields(concentration_entry)


def apply_calculation_entry_estimated_only(
    concentration_entry, calc_entry
) -> None:
    """Sync estimated quantity only; clear submitted fields (no invoice / not submitted)."""
    estimated = float(calc_entry.estimated_quantity or 0)
    concentration_entry.estimated_quantity = estimated
    concentration_entry.quantity_submitted = 0.0
    concentration_entry.submission_percentage = 0.0
    concentration_entry.submission_breakdown = None
    concentration_entry.drawing_no = None


def sync_calc_entry_to_concentration(
    db,
    calc_entry,
    calculation_sheet,
    *,
    lookup_calculation_sheet_no: str | None = None,
) -> Optional[int]:
    """
    Sync one calculation entry to its concentration entry (create or update).
    Returns the affected boq_item_id when a concentration entry was synced.
    """
    from models import models

    lookup_no = lookup_calculation_sheet_no or calculation_sheet.calculation_sheet_no
    sheet_no = calculation_sheet.calculation_sheet_no

    boq_item = (
        db.query(models.BOQItem)
        .filter(models.BOQItem.section_number == calc_entry.section_number)
        .first()
    )
    if not boq_item:
        return None

    concentration_sheet = (
        db.query(models.ConcentrationSheet)
        .filter(models.ConcentrationSheet.boq_item_id == boq_item.id)
        .first()
    )
    if not concentration_sheet:
        return None

    concentration_entry = None
    for calc_no in {lookup_no, sheet_no}:
        concentration_entry = (
            db.query(models.ConcentrationEntry)
            .filter(
                models.ConcentrationEntry.concentration_sheet_id
                == concentration_sheet.id,
                models.ConcentrationEntry.section_number == calc_entry.section_number,
                models.ConcentrationEntry.calculation_sheet_no == calc_no,
            )
            .first()
        )
        if concentration_entry:
            break

    submitted = calc_entry_is_submitted(calc_entry)
    estimated = float(calc_entry.estimated_quantity or 0)

    if concentration_entry:
        if getattr(concentration_entry, "is_manual", False):
            return None
        if submitted:
            invoice_id = str(calc_entry.current_invoice_id or "").strip()
            apply_calculation_entry_quantities(
                concentration_entry, calc_entry, drawing_no=invoice_id
            )
        else:
            apply_calculation_entry_estimated_only(concentration_entry, calc_entry)
        concentration_entry.calculation_sheet_no = sheet_no
        concentration_entry.description = calculation_sheet.description
        concentration_entry.is_manual = False
        if calc_entry.notes:
            concentration_entry.notes = calc_entry.notes
        return boq_item.id

    if estimated <= 0 and not submitted:
        return None

    submitted_qty = float(calc_entry.quantity_submitted or 0) if submitted else 0.0
    invoice_id = (
        str(calc_entry.current_invoice_id or "").strip() if submitted else None
    )
    new_entry = models.ConcentrationEntry(
        concentration_sheet_id=concentration_sheet.id,
        section_number=calc_entry.section_number,
        description=calculation_sheet.description,
        calculation_sheet_no=sheet_no,
        drawing_no=invoice_id,
        estimated_quantity=estimated,
        quantity_submitted=submitted_qty,
        submission_percentage=compute_submission_percentage(
            estimated, submitted_qty
        ),
        submission_breakdown=(
            getattr(calc_entry, "submission_breakdown", None) if submitted else None
        ),
        internal_quantity=0.0,
        approved_by_project_manager=0.0,
        notes=calc_entry.notes
        or f"Auto-synced from calculation sheet {sheet_no}",
        is_manual=False,
    )
    db.add(new_entry)
    return boq_item.id


def remove_orphan_concentration_entries(db, sheet_id: int | None = None) -> Tuple[int, Set[int]]:
    """
    Delete auto-synced concentration entries whose calculation_sheet_no is not in the DB.
    Manual entries are kept even when the calculation sheet number is unknown.
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
        if getattr(entry, "is_manual", False):
            continue
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
    is no longer on the calculation sheet at all.
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
    active_sections = {entry.section_number for entry in calculation_entries}

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

    if removed:
        db.flush()

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
