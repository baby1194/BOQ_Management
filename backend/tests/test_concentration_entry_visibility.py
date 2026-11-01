"""Tests for concentration entry visibility and calc sync helpers."""

from types import SimpleNamespace

from utils.concentration_utils import (
    calc_entry_is_submitted,
    filter_concentration_entries_for_export,
)


def test_filter_keeps_submitted_when_estimated_is_zero():
    with_estimate = SimpleNamespace(
        estimated_quantity=120.0,
        quantity_submitted=0.0,
        submission_breakdown=None,
    )
    submitted_without_estimate = SimpleNamespace(
        estimated_quantity=0.0,
        quantity_submitted=50.0,
        submission_breakdown=None,
    )
    empty = SimpleNamespace(
        estimated_quantity=0.0,
        quantity_submitted=0.0,
        submission_breakdown=None,
    )
    result = filter_concentration_entries_for_export(
        [with_estimate, submitted_without_estimate, empty]
    )
    assert result == [with_estimate, submitted_without_estimate]


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


def test_zero_estimate_with_uninvoiced_quantity_is_kept():
    uninvoiced = SimpleNamespace(
        estimated_quantity=0.0,
        quantity_submitted=0.0,
        submission_breakdown={"periods": {}, "left_submitted": 1041.47},
    )
    result = filter_concentration_entries_for_export([uninvoiced])
    assert result == [uninvoiced]


def test_sync_puts_zero_estimate_submitted_quantity_on_the_concentration_sheet():
    from unittest.mock import MagicMock

    from utils.concentration_utils import sync_calc_entry_to_concentration

    calc_entry = SimpleNamespace(
        section_number="1.2.3",
        estimated_quantity=0.0,
        quantity_submitted=1041.47,
        current_invoice_id=None,
        invoice_description=None,
        notes=None,
        submission_breakdown={
            "current_drawing_no": "",
            "periods": {},
            "left_submitted": 1041.47,
        },
    )
    calculation_sheet = SimpleNamespace(
        calculation_sheet_no="32/3/8",
        description="temporary item",
    )
    boq_item = SimpleNamespace(id=7)
    concentration_sheet = SimpleNamespace(id=20, boq_item_id=7)
    db = MagicMock()

    def query_side_effect(model):
        name = getattr(model, "__name__", str(model))
        query = MagicMock()
        if name.endswith("BOQItem"):
            query.filter.return_value.first.return_value = boq_item
            return query
        if name.endswith("ConcentrationSheet"):
            query.filter.return_value.first.return_value = concentration_sheet
            return query
        if name.endswith("ConcentrationEntry"):
            query.filter.return_value.first.return_value = None
            return query
        raise AssertionError(f"Unexpected query model: {model}")

    db.query.side_effect = query_side_effect

    result = sync_calc_entry_to_concentration(db, calc_entry, calculation_sheet)

    assert result == 7
    added = db.add.call_args[0][0]
    assert added.estimated_quantity == 0
    assert added.quantity_submitted == 1041.47
    assert added.calculation_sheet_no == "32/3/8"


def test_sync_keeps_existing_row_when_estimated_is_zero_and_there_is_no_invoice():
    from unittest.mock import MagicMock

    from utils.concentration_utils import sync_calc_entry_to_concentration

    calc_entry = SimpleNamespace(
        section_number="1.2.3",
        estimated_quantity=0.0,
        quantity_submitted=0.0,
        current_invoice_id="",
        invoice_description=None,
        notes=None,
        submission_breakdown={
            "current_drawing_no": "",
            "periods": {},
            "left_submitted": 4.0,
        },
    )
    calculation_sheet = SimpleNamespace(
        calculation_sheet_no="32/3/8",
        description="temporary item",
    )
    existing = SimpleNamespace(
        id=5,
        concentration_sheet_id=20,
        section_number="1.2.3",
        calculation_sheet_no="32/3/8",
        estimated_quantity=0.0,
        quantity_submitted=0.0,
        submission_percentage=0.0,
        submission_breakdown=None,
        drawing_no="",
        invoice_description=None,
        is_manual=False,
        description="",
        notes=None,
    )
    boq_item = SimpleNamespace(id=7)
    concentration_sheet = SimpleNamespace(id=20, boq_item_id=7)
    db = MagicMock()

    def query_side_effect(model):
        name = getattr(model, "__name__", str(model))
        query = MagicMock()
        if name.endswith("BOQItem"):
            query.filter.return_value.first.return_value = boq_item
            return query
        if name.endswith("ConcentrationSheet"):
            query.filter.return_value.first.return_value = concentration_sheet
            return query
        if name.endswith("ConcentrationEntry"):
            query.filter.return_value.first.return_value = existing
            return query
        raise AssertionError(f"Unexpected query model: {model}")

    db.query.side_effect = query_side_effect

    result = sync_calc_entry_to_concentration(db, calc_entry, calculation_sheet)

    assert result == 7
    assert existing.estimated_quantity == 0
    assert existing.quantity_submitted == 4.0
    db.add.assert_not_called()


def test_calc_entry_is_submitted_false_without_invoice():
    entry = SimpleNamespace(
        current_invoice_id="",
        quantity_submitted=100.0,
        submission_breakdown={"periods": {"06": 100.0}},
    )
    assert calc_entry_is_submitted(entry) is False
