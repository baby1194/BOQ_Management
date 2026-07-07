from types import SimpleNamespace

from utils.concentration_utils import calc_sheet_nos_submitted_equals_approved


def test_calc_sheet_nos_submitted_equals_approved_matches_equal_totals():
    entries = [
        SimpleNamespace(
            calculation_sheet_no="20/1",
            quantity_submitted=100.0,
            approved_by_project_manager=100.0,
            submission_breakdown=None,
        ),
        SimpleNamespace(
            calculation_sheet_no="20/2",
            quantity_submitted=50.0,
            approved_by_project_manager=25.0,
            submission_breakdown=None,
        ),
    ]

    assert calc_sheet_nos_submitted_equals_approved(entries) == {"20/1"}


def test_calc_sheet_nos_submitted_equals_approved_sums_multiple_entries_per_sheet():
    entries = [
        SimpleNamespace(
            calculation_sheet_no="20/3",
            quantity_submitted=30.0,
            approved_by_project_manager=10.0,
            submission_breakdown=None,
        ),
        SimpleNamespace(
            calculation_sheet_no="20/3",
            quantity_submitted=20.0,
            approved_by_project_manager=40.0,
            submission_breakdown=None,
        ),
    ]

    assert calc_sheet_nos_submitted_equals_approved(entries) == {"20/3"}
