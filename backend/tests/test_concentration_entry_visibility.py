"""Tests for concentration entry visibility and calc sync helpers."""

from types import SimpleNamespace

from utils.concentration_utils import (
    calc_entry_is_submitted,
    filter_concentration_entries_for_export,
)


def test_filter_concentration_entries_for_export_keeps_estimated_only_rows():
    with_estimate = SimpleNamespace(
        estimated_quantity=120.0,
        quantity_submitted=0.0,
        submission_breakdown=None,
    )
    without_estimate = SimpleNamespace(
        estimated_quantity=0.0,
        quantity_submitted=50.0,
        submission_breakdown=None,
    )
    result = filter_concentration_entries_for_export(
        [with_estimate, without_estimate]
    )
    assert result == [with_estimate]


def test_filter_concentration_entries_for_export_excludes_zero_submitted_when_est_hidden():
    submitted_row = SimpleNamespace(
        estimated_quantity=120.0,
        quantity_submitted=10.0,
        submission_breakdown={"periods": {"01": 10.0}},
    )
    zero_submitted_row = SimpleNamespace(
        estimated_quantity=80.0,
        quantity_submitted=0.0,
        submission_breakdown={"periods": {"01": 0.0}},
    )
    entry_columns = {"include_estimated_quantity": False}
    result = filter_concentration_entries_for_export(
        [submitted_row, zero_submitted_row], entry_columns
    )
    assert result == [submitted_row]


def test_filter_concentration_entries_for_export_includes_zero_submitted_when_est_shown():
    zero_submitted_row = SimpleNamespace(
        estimated_quantity=80.0,
        quantity_submitted=0.0,
        submission_breakdown=None,
    )
    entry_columns = {"include_estimated_quantity": True}
    result = filter_concentration_entries_for_export(
        [zero_submitted_row], entry_columns
    )
    assert result == [zero_submitted_row]


def test_calc_entry_is_submitted_false_without_invoice():
    entry = SimpleNamespace(
        current_invoice_id="",
        quantity_submitted=100.0,
        submission_breakdown={"periods": {"06": 100.0}},
    )
    assert calc_entry_is_submitted(entry) is False
