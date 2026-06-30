"""Tests for preserving manually created concentration entries during sync/purge."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from utils.concentration_utils import (
    remove_orphan_concentration_entries,
    sync_calc_entry_to_concentration,
)


def test_remove_orphan_concentration_entries_keeps_manual_rows():
    manual_entry = SimpleNamespace(
        id=1,
        concentration_sheet_id=10,
        calculation_sheet_no="MISSING-SHEET",
        is_manual=True,
    )
    auto_entry = SimpleNamespace(
        id=2,
        concentration_sheet_id=10,
        calculation_sheet_no="MISSING-SHEET",
        is_manual=False,
    )

    db = MagicMock()
    entry_query = MagicMock()
    entry_query.filter.return_value = entry_query
    entry_query.all.return_value = [manual_entry, auto_entry]

    calc_no_query = MagicMock()
    calc_no_query.all.return_value = [("KNOWN-SHEET",)]

    sheet_query = MagicMock()
    concentration_sheet = SimpleNamespace(boq_item_id=99)
    sheet_query.filter.return_value.first.return_value = concentration_sheet

    def query_side_effect(model):
        name = getattr(model, "__name__", str(model))
        if name.endswith("ConcentrationEntry"):
            return entry_query
        if name.endswith("CalculationSheet") or "CalculationSheet" in name:
            return calc_no_query
        if name.endswith("ConcentrationSheet"):
            return sheet_query
        raise AssertionError(f"Unexpected query model: {model}")

    db.query.side_effect = query_side_effect

    removed, affected = remove_orphan_concentration_entries(db, sheet_id=10)

    assert removed == 1
    assert affected == {99}
    db.delete.assert_called_once_with(auto_entry)


def test_sync_calc_entry_to_concentration_skips_manual_match():
    calc_entry = SimpleNamespace(
        section_number="1.2.3",
        estimated_quantity=100.0,
        quantity_submitted=50.0,
        current_invoice_id="06",
        notes="calc notes",
        submission_breakdown=None,
    )
    calculation_sheet = SimpleNamespace(
        calculation_sheet_no="CS-001",
        description="Calc sheet",
    )
    manual_entry = SimpleNamespace(
        id=5,
        concentration_sheet_id=20,
        section_number="1.2.3",
        calculation_sheet_no="CS-001",
        estimated_quantity=25.0,
        quantity_submitted=10.0,
        submission_percentage=40.0,
        is_manual=True,
    )
    boq_item = SimpleNamespace(id=7)
    concentration_sheet = SimpleNamespace(id=20, boq_item_id=7)

    db = MagicMock()

    def query_side_effect(model):
        name = getattr(model, "__name__", str(model))
        if name.endswith("BOQItem"):
            q = MagicMock()
            q.filter.return_value.first.return_value = boq_item
            return q
        if name.endswith("ConcentrationSheet"):
            q = MagicMock()
            q.filter.return_value.first.return_value = concentration_sheet
            return q
        if name.endswith("ConcentrationEntry"):
            q = MagicMock()
            q.filter.return_value.first.return_value = manual_entry
            return q
        raise AssertionError(f"Unexpected query model: {model}")

    db.query.side_effect = query_side_effect

    result = sync_calc_entry_to_concentration(db, calc_entry, calculation_sheet)

    assert result is None
    assert manual_entry.estimated_quantity == 25.0
    assert manual_entry.is_manual is True
