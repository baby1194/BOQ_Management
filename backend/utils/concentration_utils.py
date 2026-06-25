"""Helpers for concentration entry quantity calculations."""

from typing import Iterable, List, TypeVar

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
