"""Tests for pushing calc sheet quantities to concentration entries."""

from types import SimpleNamespace

from utils.concentration_utils import (
    apply_calculation_entry_quantities,
    compute_submission_percentage,
)


def test_apply_calculation_entry_quantities_updates_estimated_and_submitted():
    concentration_entry = SimpleNamespace(
        estimated_quantity=100.0,
        quantity_submitted=40.0,
        submission_percentage=40.0,
        submission_breakdown=None,
    )
    calc_entry = SimpleNamespace(
        estimated_quantity=250.0,
        quantity_submitted=125.0,
        submission_breakdown={"current_drawing_no": "06", "periods": {"06": 125.0}},
    )

    apply_calculation_entry_quantities(concentration_entry, calc_entry)

    assert concentration_entry.estimated_quantity == 250.0
    assert concentration_entry.quantity_submitted == 125.0
    assert concentration_entry.submission_percentage == compute_submission_percentage(
        250.0, 125.0
    )
    assert concentration_entry.submission_breakdown == calc_entry.submission_breakdown
