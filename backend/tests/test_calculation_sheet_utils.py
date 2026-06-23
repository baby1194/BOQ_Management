"""Tests for calculation sheet submission breakdown parsing."""

import pandas as pd

from utils.calculation_sheet_utils import (
    collect_sheet_periods,
    compute_submission_breakdown,
)


def test_compute_submission_breakdown_groups_by_period():
    df = pd.DataFrame([[None] * 12 for _ in range(100)])

    col = 10
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
        df.iloc[row_idx, 1] = period
        df.iloc[row_idx, col] = qty

    sheet_periods = collect_sheet_periods(df)
    breakdown, current = compute_submission_breakdown(
        df, col, "05", sheet_periods=sheet_periods
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


def test_nan_column_b_goes_to_left_not_period():
    df = pd.DataFrame([[None] * 12 for _ in range(100)])
    col = 10

    df.iloc[27, 1] = "01"
    df.iloc[27, col] = 100.0
    df.iloc[28, 1] = float("nan")
    df.iloc[28, col] = 50.0
    df.iloc[29, 1] = None
    df.iloc[29, col] = 25.0

    sheet_periods = collect_sheet_periods(df)
    breakdown, current = compute_submission_breakdown(
        df, col, "01", sheet_periods=sheet_periods
    )

    assert current == 100.0
    assert "nan" not in breakdown["periods"]
    assert breakdown["left_submitted"] == 75.0


def test_all_sheet_periods_included_even_when_item_qty_is_zero():
    df = pd.DataFrame([[None] * 12 for _ in range(100)])
    col = 10

    for row_idx, period in enumerate(["01", "02", "03"], start=27):
        df.iloc[row_idx, 1] = period
        df.iloc[row_idx, col] = 0.0

    df.iloc[30, 1] = "04"
    df.iloc[30, col] = 12.0

    sheet_periods = collect_sheet_periods(df)
    breakdown, current = compute_submission_breakdown(
        df, col, "04", sheet_periods=sheet_periods
    )

    assert current == 12.0
    assert list(breakdown["periods"].keys()) == ["01", "02", "03", "04"]
    assert breakdown["periods"]["01"] == 0.0
    assert breakdown["periods"]["02"] == 0.0
    assert breakdown["periods"]["03"] == 0.0
    assert breakdown["periods"]["04"] == 12.0
    assert len(breakdown["periods"]) == len(sheet_periods)


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
