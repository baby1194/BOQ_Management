"""Tests for pushing calc sheet quantities to concentration entries."""

from types import SimpleNamespace

from utils.concentration_utils import (
    apply_calculation_entry_quantities,
    apply_edited_submission_quantity,
    compute_submission_percentage,
)


def _period_entry(**overrides):
    entry = SimpleNamespace(
        is_manual=False,
        drawing_no="10",
        estimated_quantity=24.43,
        quantity_submitted=24.43,
        submission_percentage=0.0,
        internal_quantity=0.0,
        approved_by_project_manager=0.0,
        notes="",
        supervisor_notes="",
        drawing_files=[],
        invoice_description="",
        submission_breakdown={
            "current_drawing_no": "10",
            "periods": {"10": 24.43},
            "left_submitted": 0.0,
            "period_details": {
                "10": {
                    "internal_quantity": 0.0,
                    "approved_by_project_manager": 0.0,
                    "submission_percentage": 0.0,
                    "notes": "",
                    "supervisor_notes": "",
                    "drawing_files": [],
                    "invoice_description": "",
                }
            },
        },
    )
    for key, value in overrides.items():
        setattr(entry, key, value)
    return entry


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

    expected_percentage = compute_submission_percentage(250.0, 125.0)
    assert concentration_entry.estimated_quantity == 250.0
    assert concentration_entry.quantity_submitted == 125.0
    assert concentration_entry.submission_percentage == expected_percentage
    breakdown = concentration_entry.submission_breakdown
    assert breakdown["current_drawing_no"] == "06"
    assert breakdown["periods"] == {"06": 125.0}
    assert breakdown["period_details"]["06"]["submission_percentage"] == expected_percentage


def test_track_replaces_stale_zero_percentage_after_quantity_returns():
    concentration_entry = _period_entry()
    calc_entry = SimpleNamespace(
        estimated_quantity=24.43,
        quantity_submitted=24.43,
        submission_breakdown={
            "current_drawing_no": "10",
            "periods": {"10": 24.43},
            "left_submitted": 0.0,
        },
    )

    apply_calculation_entry_quantities(
        concentration_entry, calc_entry, drawing_no="10"
    )

    assert concentration_entry.quantity_submitted == 24.43
    assert concentration_entry.submission_percentage == 100.0
    assert (
        concentration_entry.submission_breakdown["period_details"]["10"][
            "submission_percentage"
        ]
        == 100.0
    )
    assert (
        concentration_entry.submission_breakdown["period_details"]["10"][
            "approved_by_project_manager"
        ]
        == 0.0
    )


def test_approved_qty_save_keeps_submitted_qty_when_percentage_is_unchanged():
    entry = _period_entry(approved_by_project_manager=12.0)
    entry.submission_breakdown["period_details"]["10"][
        "approved_by_project_manager"
    ] = 12.0

    apply_edited_submission_quantity(
        entry,
        editing_current_period=True,
        estimated_in_update=False,
        percentage_in_update=True,
        old_estimated=24.43,
        old_percentage=0.0,
    )

    assert entry.quantity_submitted == 24.43
    assert entry.approved_by_project_manager == 12.0
    assert entry.submission_percentage == 100.0


def test_changing_percentage_rebuilds_submitted_quantity():
    entry = _period_entry(
        submission_percentage=50.0,
        quantity_submitted=24.43,
    )

    apply_edited_submission_quantity(
        entry,
        editing_current_period=True,
        estimated_in_update=False,
        percentage_in_update=True,
        old_estimated=24.43,
        old_percentage=100.0,
    )

    assert abs(entry.quantity_submitted - (24.43 * 0.5)) < 1e-6


def test_zero_estimate_save_keeps_carried_submitted_quantity():
    entry = _period_entry(
        estimated_quantity=0.0,
        quantity_submitted=24.43,
        submission_percentage=100.0,
    )

    apply_edited_submission_quantity(
        entry,
        editing_current_period=True,
        estimated_in_update=False,
        percentage_in_update=True,
        old_estimated=0.0,
        old_percentage=100.0,
    )

    assert entry.quantity_submitted == 24.43


def test_past_period_edit_does_not_change_current_submitted_quantity():
    entry = _period_entry()

    apply_edited_submission_quantity(
        entry,
        editing_current_period=False,
        estimated_in_update=False,
        percentage_in_update=True,
        old_estimated=24.43,
        old_percentage=0.0,
    )

    assert entry.quantity_submitted == 24.43
    assert entry.submission_percentage == 0.0
