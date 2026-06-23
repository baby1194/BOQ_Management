"""Helpers for parsing and exporting calculation sheet submission breakdowns."""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd


DETAIL_START_ROW = 27  # Excel row 28 (0-based)
DETAIL_END_ROW = 100  # Excel row 100 inclusive (0-based index 99)
PERIOD_COLUMN_INDEX = 1  # Column B

_INVALID_PERIOD_STRINGS = frozenset({"nan", "none", "<na>", "nat"})


def _normalize_period_value(value) -> Optional[str]:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, float) and math.isnan(value):
        return None
    text = str(value).strip()
    if not text or text.lower() in _INVALID_PERIOD_STRINGS:
        return None
    return text


def _safe_float(value) -> float:
    if value is None:
        return 0.0
    try:
        if pd.isna(value):
            return 0.0
    except (TypeError, ValueError):
        pass
    try:
        if isinstance(value, str) and not value.strip():
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _sort_period_keys(periods: Iterable[str]) -> List[str]:
    return sorted(set(periods), key=lambda key: (len(key), key))


def collect_sheet_periods(df) -> List[str]:
    """Collect all unique non-empty column B values from detail rows 28-100."""
    periods: set[str] = set()
    row_limit = min(DETAIL_END_ROW, df.shape[0])
    for row_idx in range(DETAIL_START_ROW, row_limit):
        period = _normalize_period_value(df.iloc[row_idx, PERIOD_COLUMN_INDEX])
        if period:
            periods.add(period)
    return _sort_period_keys(periods)


def _breakdown_periods(breakdown: Optional[Dict[str, Any]]) -> Dict[str, float]:
    """Return period->qty map, supporting new and legacy breakdown shapes."""
    if not breakdown:
        return {}

    periods = breakdown.get("periods")
    if isinstance(periods, dict) and periods:
        return {str(k): float(v or 0) for k, v in periods.items()}

    merged: Dict[str, float] = {}
    past = breakdown.get("past_months") or {}
    if isinstance(past, dict):
        merged.update({str(k): float(v or 0) for k, v in past.items()})

    current_drawing_no = str(breakdown.get("current_drawing_no") or "").strip()
    if current_drawing_no and current_drawing_no not in merged:
        merged[current_drawing_no] = 0.0

    invalid = [k for k in merged if _normalize_period_value(k) is None]
    for key in invalid:
        merged.pop(key, None)

    return merged


def breakdown_period_keys(breakdown: Optional[Dict[str, Any]]) -> List[str]:
    return _sort_period_keys(_breakdown_periods(breakdown).keys())


def period_quantity(breakdown: Optional[Dict[str, Any]], period: str) -> float:
    periods = _breakdown_periods(breakdown)
    return float(periods.get(period, 0.0) or 0.0)


def compute_submission_breakdown(
    df,
    col_index: int,
    current_drawing_no: str,
    sheet_periods: Optional[List[str]] = None,
) -> Tuple[Dict[str, Any], float]:
    """
    Sum submitted quantities from detail rows 28-100 for one item column.

    Every unique column B period on the sheet gets a row (0 when no qty for this item).
    Rows with empty/invalid column B accumulate into left_submitted.
    """
    current_drawing_no = str(current_drawing_no or "").strip()
    if sheet_periods is None:
        sheet_periods = collect_sheet_periods(df)

    period_keys = list(sheet_periods)
    if current_drawing_no and current_drawing_no not in period_keys:
        period_keys = _sort_period_keys(period_keys + [current_drawing_no])

    periods = {period: 0.0 for period in period_keys}
    left_submitted = 0.0

    row_limit = min(DETAIL_END_ROW, df.shape[0])
    for row_idx in range(DETAIL_START_ROW, row_limit):
        if col_index >= df.shape[1]:
            break

        qty = _safe_float(df.iloc[row_idx, col_index])
        period = _normalize_period_value(df.iloc[row_idx, PERIOD_COLUMN_INDEX])

        if period is None:
            left_submitted += qty
        elif period in periods:
            periods[period] += qty
        else:
            # Unexpected period not seen in sheet scan; still count it.
            periods[period] = periods.get(period, 0.0) + qty

    current_submitted = float(periods.get(current_drawing_no, 0.0) or 0.0)

    breakdown = {
        "current_drawing_no": current_drawing_no,
        "periods": periods,
        "left_submitted": left_submitted,
    }
    return breakdown, current_submitted


def sorted_past_month_keys(breakdown: Optional[Dict[str, Any]]) -> List[str]:
    """Legacy helper: past periods excluding current drawing no."""
    if not breakdown:
        return []
    current = str(breakdown.get("current_drawing_no") or "").strip()
    return [
        key
        for key in breakdown_period_keys(breakdown)
        if key != current
    ]


def collect_breakdown_period_keys(entries: Iterable[Any]) -> List[str]:
    """Collect sorted period keys across concentration/calculation entries."""
    keys: set[str] = set()
    for entry in entries:
        breakdown = getattr(entry, "submission_breakdown", None) or {}
        if isinstance(breakdown, dict):
            keys.update(breakdown_period_keys(breakdown))
    return _sort_period_keys(keys)


def _entry_current_drawing_no(entry: Any, breakdown: Dict[str, Any]) -> str:
    current = str(breakdown.get("current_drawing_no") or "").strip()
    if not current:
        current = str(getattr(entry, "drawing_no", None) or "").strip()
    return current


def collect_export_past_period_keys(entries: Iterable[Any]) -> List[str]:
    """Past periods for export: all sheet periods except each entry's current month."""
    keys: set[str] = set()
    for entry in entries:
        breakdown = getattr(entry, "submission_breakdown", None) or {}
        if not isinstance(breakdown, dict):
            continue
        current = _entry_current_drawing_no(entry, breakdown)
        for period in breakdown_period_keys(breakdown):
            if period != current:
                keys.add(period)
    return _sort_period_keys(keys)


def past_month_quantity(
    breakdown: Optional[Dict[str, Any]], period: str
) -> float:
    return period_quantity(breakdown, period)


def left_submitted_quantity(breakdown: Optional[Dict[str, Any]]) -> float:
    if not breakdown:
        return 0.0
    return float(breakdown.get("left_submitted", 0.0) or 0.0)


def breakdowns_equal(
    left: Optional[Dict[str, Any]], right: Optional[Dict[str, Any]]
) -> bool:
    if not left and not right:
        return True
    if not left or not right:
        return False

    if _breakdown_periods(left) != _breakdown_periods(right):
        return False
    if float(left.get("left_submitted", 0.0) or 0.0) != float(
        right.get("left_submitted", 0.0) or 0.0
    ):
        return False
    return str(left.get("current_drawing_no") or "") == str(
        right.get("current_drawing_no") or ""
    )


CONCENTRATION_BASE_HEADERS = [
    "Description",
    "Calculation Sheet No",
    "Invoice No",
    "Estimated Quantity",
    "Submission Percentage",
    "Quantity Submitted",
    "Internal Quantity",
    "Approved by Project Manager",
    "Notes",
    "Supervisor Notes",
]

LEFT_SUBMITTED_HEADER = "Left Submitted"


def period_header_key(period: str) -> str:
    return f"QTY submitted({period})"


def period_from_export_header(header: str) -> Optional[str]:
    prefix = "QTY submitted("
    suffix = ")"
    if header.startswith(prefix) and header.endswith(suffix):
        return header[len(prefix) : -len(suffix)]
    if header.startswith("Period "):
        return header.replace("Period ", "", 1)
    return None


def is_past_period_export_header(header: str) -> bool:
    return period_from_export_header(header) is not None


def translate_past_period_header(period: str, language: str) -> str:
    if language == "he":
        return f"כמות מוגשת({period})"
    return period_header_key(period)


def _insert_past_submission_columns(
    filtered_headers: List[str],
    period_keys: List[str],
    include_left: bool,
) -> None:
    """Insert past period and optional left columns after Qty Submitted."""
    if not period_keys and not include_left:
        return

    insert_at = len(filtered_headers)
    if "Quantity Submitted" in filtered_headers:
        insert_at = filtered_headers.index("Quantity Submitted") + 1
    elif "Submission Percentage" in filtered_headers:
        insert_at = filtered_headers.index("Submission Percentage") + 1

    extras: List[str] = [period_header_key(period) for period in period_keys]
    if include_left:
        extras.append(LEFT_SUBMITTED_HEADER)

    for offset, header in enumerate(extras):
        filtered_headers.insert(insert_at + offset, header)


def filter_concentration_export_headers(
    entry_columns: Optional[Dict[str, Any]],
    entries: Iterable[Any],
) -> Tuple[List[str], List[str]]:
    """Return filtered headers and sorted past period keys for export."""
    entries_list = list(entries)
    period_keys: List[str] = []
    include_past = bool(
        entry_columns and entry_columns.get("include_past_months_submitted")
    )
    include_left = bool(
        entry_columns and entry_columns.get("include_left_submitted")
    )
    if include_past:
        period_keys = collect_export_past_period_keys(entries_list)

    if entry_columns:
        filtered_headers: List[str] = []
        if entry_columns.get("include_description", True):
            filtered_headers.append("Description")
        if entry_columns.get("include_calculation_sheet_no", True):
            filtered_headers.append("Calculation Sheet No")
        if entry_columns.get("include_drawing_no", True):
            filtered_headers.append("Invoice No")
        if entry_columns.get("include_estimated_quantity", True):
            filtered_headers.append("Estimated Quantity")
        if entry_columns.get("include_submission_percentage", True):
            filtered_headers.append("Submission Percentage")
        if entry_columns.get("include_quantity_submitted", True):
            filtered_headers.append("Quantity Submitted")
        if entry_columns.get("include_internal_quantity", True):
            filtered_headers.append("Internal Quantity")
        if entry_columns.get("include_approved_by_project_manager", True):
            filtered_headers.append("Approved by Project Manager")
        if entry_columns.get("include_notes", True):
            filtered_headers.append("Notes")
        if entry_columns.get("include_supervisor_notes", True):
            filtered_headers.append("Supervisor Notes")

        _insert_past_submission_columns(
            filtered_headers, period_keys, include_left
        )
    else:
        filtered_headers = list(CONCENTRATION_BASE_HEADERS)

    return filtered_headers, period_keys


def build_concentration_export_row_values(
    entry: Any,
    period_keys: List[str],
    notes_value: str = "",
) -> Dict[str, Any]:
    """Build header-keyed values for one concentration entry export row."""
    breakdown = getattr(entry, "submission_breakdown", None) or {}
    current_drawing_no = _entry_current_drawing_no(entry, breakdown)
    row = {
        "Description": entry.description or "",
        "Calculation Sheet No": entry.calculation_sheet_no or "",
        "Invoice No": entry.drawing_no or "",
        "Estimated Quantity": float(entry.estimated_quantity or 0),
        "Submission Percentage": float(
            getattr(entry, "submission_percentage", 100.0) or 100.0
        ),
        "Quantity Submitted": float(entry.quantity_submitted or 0),
        "Internal Quantity": float(entry.internal_quantity or 0),
        "Approved by Project Manager": float(
            entry.approved_by_project_manager or 0
        ),
        "Notes": notes_value or entry.notes or "",
        "Supervisor Notes": getattr(entry, "supervisor_notes", None) or "",
    }
    for period in period_keys:
        header = period_header_key(period)
        if period == current_drawing_no:
            row[header] = 0.0
        else:
            row[header] = period_quantity(breakdown, period)
    row[LEFT_SUBMITTED_HEADER] = left_submitted_quantity(breakdown)
    return row


def concentration_export_header_translations(language: str) -> Dict[str, str]:
    if language == "he":
        base = {
            "Description": "תיאור:",
            "Calculation Sheet No": "מס' דף חישוב",
            "Invoice No": "מס' שרטוט",
            "Estimated Quantity": "כמות מחושבת",
            "Submission Percentage": "אחוז הגשה",
            "Quantity Submitted": "כמות מוגשת",
            "Internal Quantity": "כמות פנימית",
            "Approved by Project Manager": "כמות מאושרת",
            "Notes": "הערות",
            "Supervisor Notes": "הערות מפקח",
            LEFT_SUBMITTED_HEADER: "כמות שנותרה",
        }
    else:
        base = {
            "Description": "Description:",
            "Calculation Sheet No": "Calc. Sheet No",
            "Invoice No": "Invoice No",
            "Estimated Quantity": "Est. Quantity",
            "Submission Percentage": "Percentage",
            "Quantity Submitted": "Qty Submitted",
            "Internal Quantity": "Internal Qty",
            "Approved by Project Manager": "Approved Qty",
            "Notes": "Notes",
            "Supervisor Notes": "Supervisor Notes",
            LEFT_SUBMITTED_HEADER: "Left Submitted",
        }
    return base


def format_concentration_export_row_for_pdf(
    row_values: Dict[str, Any],
    filtered_headers: List[str],
) -> List[str]:
    text_headers = {
        "Description",
        "Calculation Sheet No",
        "Invoice No",
        "Notes",
        "Supervisor Notes",
    }
    formatted: List[str] = []
    for header in filtered_headers:
        value = row_values.get(header, "")
        if header == "Submission Percentage":
            formatted.append(f"{float(value or 0):,.1f}%")
        elif header in text_headers:
            formatted.append(str(value or ""))
        else:
            formatted.append(f"{float(value or 0):,.2f}")
    return formatted


def build_concentration_export_totals_row(
    entries: Iterable[Any],
    filtered_headers: List[str],
    period_keys: List[str],
    totals_label: str,
) -> Dict[str, Any]:
    totals: Dict[str, Any] = {header: "" for header in filtered_headers}
    totals["Description"] = totals_label
    numeric_headers = [
        "Estimated Quantity",
        "Quantity Submitted",
        "Internal Quantity",
        "Approved by Project Manager",
        LEFT_SUBMITTED_HEADER,
    ] + [period_header_key(period) for period in period_keys]
    for header in numeric_headers:
        if header not in filtered_headers:
            continue
        if header == LEFT_SUBMITTED_HEADER:
            totals[header] = sum(
                left_submitted_quantity(getattr(entry, "submission_breakdown", None))
                for entry in entries
            )
        elif is_past_period_export_header(header):
            period = period_from_export_header(header)
            if not period:
                continue
            totals[header] = sum(
                period_quantity(getattr(entry, "submission_breakdown", None), period)
                for entry in entries
                if _entry_current_drawing_no(
                    entry, getattr(entry, "submission_breakdown", None) or {}
                )
                != period
            )
        elif header == "Estimated Quantity":
            totals[header] = sum(float(entry.estimated_quantity or 0) for entry in entries)
        elif header == "Quantity Submitted":
            totals[header] = sum(float(entry.quantity_submitted or 0) for entry in entries)
        elif header == "Internal Quantity":
            totals[header] = sum(float(entry.internal_quantity or 0) for entry in entries)
        elif header == "Approved by Project Manager":
            totals[header] = sum(
                float(entry.approved_by_project_manager or 0) for entry in entries
            )
    return totals
