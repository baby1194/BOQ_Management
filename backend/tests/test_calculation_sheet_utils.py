"""Tests for calculation sheet submission breakdown parsing."""

import pandas as pd

from utils.calculation_sheet_utils import (
    SHARED_PERIOD_COLUMN_INDEX,
    collect_entry_periods,
    compute_submission_breakdown,
    count_calculation_sheet_items,
    period_column_index,
    read_entry_current_invoice_id,
    read_entry_submitted_invoice_id,
)


def _period_col(item_col: int, item_count: int = 2) -> int:
    return period_column_index(item_col, item_count)


def test_compute_submission_breakdown_groups_by_period():
    df = pd.DataFrame([[None] * 12 for _ in range(100)])

    col = 10
    period_col = _period_col(col)
    rows = {
        27: ("01", 460),
        28: ("01", 24),
        29: ("01", 24),
        30: ("02", 24),
        31: ("02", 24),
        32: ("03", 24),
        33: ("03", 480),
        34: ("04", 24),
        35: ("04", 24),
        36: ("05", 500),
        37: ("05", 24),
        38: ("05", 24),
        39: (None, 260),
        40: (None, 24),
    }
    for row_idx, (period, qty) in rows.items():
        df.iloc[row_idx, period_col] = period
        df.iloc[row_idx, col] = qty

    entry_periods = collect_entry_periods(df, col, item_count=2)
    breakdown, current = compute_submission_breakdown(
        df, col, "05", sheet_periods=entry_periods, item_count=2
    )

    assert current == 548.0
    assert breakdown["periods"] == {
        "01": 508.0,
        "02": 48.0,
        "03": 504.0,
        "04": 48.0,
        "05": 548.0,
    }
    assert breakdown["left_submitted"] == 284.0


def test_empty_period_column_goes_to_left_not_period():
    df = pd.DataFrame([[None] * 12 for _ in range(100)])
    col = 10
    period_col = _period_col(col)

    df.iloc[27, period_col] = "01"
    df.iloc[27, col] = 100.0
    df.iloc[28, period_col] = float("nan")
    df.iloc[28, col] = 50.0
    df.iloc[29, period_col] = None
    df.iloc[29, col] = 25.0

    entry_periods = collect_entry_periods(df, col, item_count=2)
    breakdown, current = compute_submission_breakdown(
        df, col, "01", sheet_periods=entry_periods, item_count=2
    )

    assert current == 100.0
    assert "nan" not in breakdown["periods"]
    assert breakdown["left_submitted"] == 75.0


def test_all_entry_periods_included_even_when_item_qty_is_zero():
    df = pd.DataFrame([[None] * 12 for _ in range(100)])
    col = 10
    period_col = _period_col(col)

    for row_idx, period in enumerate(["01", "02", "03"], start=27):
        df.iloc[row_idx, period_col] = period
        df.iloc[row_idx, col] = 0.0

    df.iloc[30, period_col] = "04"
    df.iloc[30, col] = 12.0

    entry_periods = collect_entry_periods(df, col, item_count=2)
    breakdown, current = compute_submission_breakdown(
        df, col, "04", sheet_periods=entry_periods, item_count=2
    )

    assert current == 12.0
    assert list(breakdown["periods"].keys()) == ["01", "02", "03", "04"]
    assert breakdown["periods"]["01"] == 0.0
    assert breakdown["periods"]["02"] == 0.0
    assert breakdown["periods"]["03"] == 0.0
    assert breakdown["periods"]["04"] == 12.0
    assert len(breakdown["periods"]) == len(entry_periods)


def test_collect_export_past_period_keys_excludes_current():
    class Entry:
        def __init__(self, breakdown, drawing_no=None):
            self.submission_breakdown = breakdown
            self.drawing_no = drawing_no

    entries = [
        Entry(
            {
                "current_drawing_no": "06",
                "periods": {
                    "01": 508.0,
                    "02": 24.0,
                    "03": 48.0,
                    "04": 504.0,
                    "05": 24.0,
                    "06": 524.0,
                },
            },
            drawing_no="06",
        )
    ]

    from utils.calculation_sheet_utils import (
        collect_export_past_period_keys,
        filter_concentration_export_headers,
        period_header_key,
    )

    past_keys = collect_export_past_period_keys(entries)
    assert past_keys == ["01", "02", "03", "04", "05"]
    assert "06" not in past_keys

    headers, period_keys = filter_concentration_export_headers(
        {
            "include_past_months_submitted": True,
            "include_quantity_submitted": True,
            "include_internal_quantity": True,
        },
        entries,
    )
    assert period_keys == past_keys
    assert headers.index("Quantity Submitted") == 5
    assert headers.index(period_header_key("01")) == 6
    assert headers.index(period_header_key("05")) == 10
    assert headers.index("Internal Quantity") == 11
    assert period_header_key("06") not in headers


def test_reads_quantities_beyond_row_100():
    df = pd.DataFrame([[None] * 12 for _ in range(150)])
    col = 10
    period_col = _period_col(col)
    df.iloc[120, period_col] = "01"
    df.iloc[120, col] = 99.0

    entry_periods = collect_entry_periods(df, col, item_count=2)
    breakdown, current = compute_submission_breakdown(
        df, col, "01", sheet_periods=entry_periods, item_count=2
    )

    assert current == 99.0
    assert breakdown["periods"]["01"] == 99.0


def test_concentration_export_totals_row_leaves_percentage_blank():
    from types import SimpleNamespace

    from utils.calculation_sheet_utils import (
        build_concentration_export_totals_row,
        format_concentration_export_row_for_pdf,
        filter_concentration_export_headers,
    )

    entries = [
        SimpleNamespace(
            description="a",
            calculation_sheet_no="1",
            drawing_no="01",
            estimated_quantity=100,
            submission_percentage=50,
            quantity_submitted=50,
            internal_quantity=10,
            approved_by_project_manager=5,
            notes="",
            submission_breakdown=None,
        ),
        SimpleNamespace(
            description="b",
            calculation_sheet_no="2",
            drawing_no="02",
            estimated_quantity=200,
            submission_percentage=75,
            quantity_submitted=150,
            internal_quantity=20,
            approved_by_project_manager=10,
            notes="",
            submission_breakdown=None,
        ),
    ]
    headers, period_keys = filter_concentration_export_headers({}, entries)
    totals = build_concentration_export_totals_row(
        entries, headers, period_keys, "TOTALS"
    )
    assert totals["Submission Percentage"] == ""

    formatted = format_concentration_export_row_for_pdf(totals, headers)
    pct_idx = headers.index("Submission Percentage")
    assert formatted[pct_idx] == ""


def test_concentration_export_pdf_formats_zero_numeric_as_empty():
    from utils.calculation_sheet_utils import format_concentration_export_row_for_pdf

    headers = [
        "Description",
        "Quantity Submitted",
        "Approved by Project Manager",
    ]
    formatted = format_concentration_export_row_for_pdf(
        {
            "Description": "DC-29",
            "Quantity Submitted": 674.8,
            "Approved by Project Manager": 0,
        },
        headers,
    )
    assert formatted[0] == "DC-29"
    assert formatted[1] == "674.80"
    assert formatted[2] == ""


def test_cumulative_submitted_quantity_excludes_left_submitted():
    breakdown = {
        "current_drawing_no": "03",
        "periods": {"01": 100.0, "02": 100.0, "03": 100.0},
        "left_submitted": 200.0,
    }
    from utils.calculation_sheet_utils import cumulative_submitted_quantity

    assert cumulative_submitted_quantity(breakdown) == 300.0


def test_entry_cumulative_submitted_quantity_falls_back_without_breakdown():
    from types import SimpleNamespace

    from utils.calculation_sheet_utils import entry_cumulative_submitted_quantity

    entry = SimpleNamespace(quantity_submitted=125.0, submission_breakdown=None)
    assert entry_cumulative_submitted_quantity(entry) == 125.0


def test_build_concentration_export_subrows():
    from types import SimpleNamespace

    from utils.calculation_sheet_utils import (
        build_concentration_export_rows_for_entry,
        build_concentration_export_totals_row,
        concentration_export_link_row_offsets,
        concentration_export_main_row_offsets,
    )

    entry = SimpleNamespace(
        description="Item A",
        calculation_sheet_no="7",
        drawing_no="06",
        estimated_quantity=1000.0,
        submission_percentage=10.0,
        quantity_submitted=100.0,
        internal_quantity=0.0,
        approved_by_project_manager=0.0,
        notes="",
        supervisor_notes="",
        submission_breakdown={
            "current_drawing_no": "06",
            "periods": {"01": 200.0, "02": 150.0, "06": 100.0},
            "left_submitted": 50.0,
        },
    )
    headers = [
        "Description",
        "Calculation Sheet No",
        "Estimated Quantity",
        "Invoice No",
        "Submission Percentage",
        "Quantity Submitted",
        "Internal Quantity",
        "Approved by Project Manager",
    ]
    entry_columns = {"include_past_months_submitted_subrows": True}

    rows = build_concentration_export_rows_for_entry(
        entry, [], headers, entry_columns
    )
    assert len(rows) == 3
    assert rows[0]["Description"] == "Item A"
    assert rows[0]["Invoice No"] == "01"
    assert rows[0]["Quantity Submitted"] == 200.0
    assert rows[0]["Submission Percentage"] == 20.0
    assert rows[0]["Estimated Quantity"] == 1000.0
    assert rows[0]["Internal Quantity"] is None
    assert rows[1]["Invoice No"] == "02"
    assert rows[1]["Description"] is None
    assert rows[1]["Estimated Quantity"] is None
    assert rows[1]["Internal Quantity"] is None
    assert rows[1]["Approved by Project Manager"] is None
    assert rows[2]["Invoice No"] == "06"
    assert rows[2]["Description"] is None
    assert rows[2]["Quantity Submitted"] == 100.0

    offsets = concentration_export_main_row_offsets([entry], entry_columns)
    assert offsets == [2]
    link_offsets = concentration_export_link_row_offsets([entry], entry_columns)
    assert link_offsets == [0]

    totals = build_concentration_export_totals_row(
        [entry],
        ["Quantity Submitted"],
        [],
        "TOTALS",
        entry_columns,
    )
    assert totals["Quantity Submitted"] == 450.0


def test_validate_calculation_sheet_header_fields_messages():
    import pytest

    from utils.calculation_sheet_utils import validate_calculation_sheet_header_fields

    with pytest.raises(ValueError, match="File test.xlsx has empty calculation no."):
        validate_calculation_sheet_header_fields("", "06", "desc", "test.xlsx")

    with pytest.raises(ValueError, match="File test.xlsx has empty invoice no."):
        validate_calculation_sheet_header_fields("7", "", "desc", "test.xlsx")


def test_read_entry_current_invoice_id_from_column_row_2():
    df = pd.DataFrame([[None] * 12 for _ in range(100)])
    col = 10
    df.iloc[1, col] = "07"
    assert read_entry_current_invoice_id(df, col, "06") == "07"


def test_read_entry_current_invoice_id_falls_back_to_sheet_c2():
    df = pd.DataFrame([[None] * 12 for _ in range(100)])
    col = 10
    assert read_entry_current_invoice_id(df, col, "06") == "06"


def test_read_entry_submitted_invoice_id_requires_row_2():
    df = pd.DataFrame([[None] * 12 for _ in range(100)])
    col = 10
    assert read_entry_submitted_invoice_id(df, col) is None

    df.iloc[1, col] = "07"
    assert read_entry_submitted_invoice_id(df, col) == "07"


def test_calc_entry_is_submitted_requires_invoice_and_quantity():
    from types import SimpleNamespace

    from utils.concentration_utils import calc_entry_is_submitted

    assert calc_entry_is_submitted(
        SimpleNamespace(current_invoice_id=None, quantity_submitted=100.0)
    ) is False
    assert calc_entry_is_submitted(
        SimpleNamespace(
            current_invoice_id="06",
            quantity_submitted=50.0,
            submission_breakdown=None,
        )
    ) is True


def test_compute_submission_breakdown_uses_per_entry_invoice_id():
    df = pd.DataFrame([[None] * 12 for _ in range(100)])
    col = 10
    period_col = _period_col(col)
    df.iloc[27, period_col] = "05"
    df.iloc[27, col] = 100.0
    df.iloc[28, period_col] = "06"
    df.iloc[28, col] = 50.0

    entry_periods = collect_entry_periods(df, col, item_count=2)
    breakdown, current = compute_submission_breakdown(
        df, col, "06", sheet_periods=entry_periods, item_count=2
    )

    assert current == 50.0
    assert breakdown["current_drawing_no"] == "06"
    assert breakdown["periods"]["05"] == 100.0
    assert breakdown["periods"]["06"] == 50.0


def test_each_item_uses_its_own_prior_column_for_periods():
    df = pd.DataFrame([[None] * 14 for _ in range(100)])

    col_a = 10
    period_col_a = _period_col(col_a)
    df.iloc[27, period_col_a] = "01"
    df.iloc[27, col_a] = 100.0
    df.iloc[28, period_col_a] = "02"
    df.iloc[28, col_a] = 50.0

    col_b = 12
    period_col_b = _period_col(col_b)
    df.iloc[27, period_col_b] = "03"
    df.iloc[27, col_b] = 200.0
    df.iloc[28, period_col_b] = "04"
    df.iloc[28, col_b] = 75.0

    breakdown_a, current_a = compute_submission_breakdown(
        df, col_a, "02", item_count=2
    )
    breakdown_b, current_b = compute_submission_breakdown(
        df, col_b, "04", item_count=2
    )

    assert current_a == 50.0
    assert breakdown_a["periods"] == {"01": 100.0, "02": 50.0}
    assert current_b == 75.0
    assert breakdown_b["periods"] == {"03": 200.0, "04": 75.0}


def test_single_item_uses_column_b_for_periods():
    df = pd.DataFrame([[None] * 12 for _ in range(100)])
    col = 10
    period_col = SHARED_PERIOD_COLUMN_INDEX

    df.iloc[27, period_col] = "01"
    df.iloc[27, col] = 100.0
    df.iloc[28, period_col] = "02"
    df.iloc[28, col] = 50.0

    entry_periods = collect_entry_periods(df, col, item_count=1)
    breakdown, current = compute_submission_breakdown(
        df, col, "02", sheet_periods=entry_periods, item_count=1
    )

    assert current == 50.0
    assert breakdown["periods"] == {"01": 100.0, "02": 50.0}


def test_count_calculation_sheet_items():
    df = pd.DataFrame([[None] * 14 for _ in range(10)])
    df.iloc[4, 10] = "A"
    assert count_calculation_sheet_items(df) == 1

    df.iloc[4, 12] = "B"
    assert count_calculation_sheet_items(df) == 2
