"""Helpers for concentration entry quantity calculations."""


def compute_quantity_submitted(
    estimated_quantity: float, submission_percentage: float
) -> float:
    """Derive submitted quantity from estimated quantity and submission percentage."""
    return float(estimated_quantity or 0) * (float(submission_percentage or 0) / 100.0)
