"""Helpers for concentration entry quantity calculations."""


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
    concentration_entry, calc_entry
) -> None:
    """Copy estimated/submitted quantities from a calc entry and derive submission percentage."""
    estimated = float(calc_entry.estimated_quantity or 0)
    submitted = float(calc_entry.quantity_submitted or 0)
    concentration_entry.estimated_quantity = estimated
    concentration_entry.quantity_submitted = submitted
    concentration_entry.submission_percentage = compute_submission_percentage(
        estimated, submitted
    )
