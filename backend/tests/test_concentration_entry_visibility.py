"""Tests for concentration entry visibility and calc sync helpers."""

from types import SimpleNamespace

from utils.concentration_utils import (
    calc_entry_is_submitted,
    filter_concentration_entries_for_export,
)


def test_filter_concentration_entries_for_export_keeps_estimated_only_rows():
    with_estimate = SimpleNamespace(estimated_quantity=120.0, quantity_submitted=0.0)
    without_estimate = SimpleNamespace(estimated_quantity=0.0, quantity_submitted=50.0)
    result = filter_concentration_entries_for_export(
        [with_estimate, without_estimate]
    )
    assert result == [with_estimate]


def test_calc_entry_is_submitted_false_without_invoice():
    entry = SimpleNamespace(
        current_invoice_id="",
        quantity_submitted=100.0,
        submission_breakdown={"periods": {"06": 100.0}},
    )
    assert calc_entry_is_submitted(entry) is False
