"""Tests for concentration entry visibility and calc sync helpers."""

from types import SimpleNamespace

from utils.concentration_utils import (
    calc_entry_is_submitted,
    filter_concentration_entries_for_table,
)


def test_filter_concentration_entries_for_table_hides_zero_submitted():
    visible = SimpleNamespace(
        quantity_submitted=25.0,
        submission_breakdown=None,
    )
    hidden = SimpleNamespace(
        quantity_submitted=0.0,
        submission_breakdown=None,
    )
    result = filter_concentration_entries_for_table([visible, hidden])
    assert result == [visible]


def test_calc_entry_is_submitted_false_without_invoice():
    entry = SimpleNamespace(
        current_invoice_id="",
        quantity_submitted=100.0,
        submission_breakdown={"periods": {"06": 100.0}},
    )
    assert calc_entry_is_submitted(entry) is False
