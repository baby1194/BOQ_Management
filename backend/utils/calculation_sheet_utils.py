"""Helpers for parsing and exporting calculation sheet submission breakdowns."""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd


DETAIL_START_ROW = 27  # Excel row 28 (0-based)
INVOICE_ID_ROW = 1  # Excel row 2 (0-based)
SECTION_NUMBER_ROW = 4  # Excel row 5 (0-based)
SHARED_PERIOD_COLUMN_INDEX = 1  # Column B — past invoices when the sheet has one item
FIRST_ITEM_COLUMN_INDEX = 4


def period_column_index(item_col_index: int, item_count: int) -> int:
    """Past submission invoice column: column B for a single item, prior column otherwise."""
    if item_count <= 1:
        return SHARED_PERIOD_COLUMN_INDEX
    return item_col_index - 1


def count_calculation_sheet_items(df, start_col: int = FIRST_ITEM_COLUMN_INDEX) -> int:
    """Count item columns with a non-empty section number in row 5."""
    count = 0
    for col_index in range(start_col, df.shape[1]):
        section_number = df.iloc[SECTION_NUMBER_ROW, col_index]
        if pd.notna(section_number) and str(section_number).strip():
            count += 1
    return count

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


def _cell_has_value(value) -> bool:
    if value is None:
        return False
    try:
        if pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass
    if isinstance(value, float) and math.isnan(value):
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True


def _row_has_any_value(row) -> bool:
    for value in row:
        if _cell_has_value(value):
            return True
    return False


def get_detail_row_end_exclusive(df) -> int:
    """
    Exclusive end row index for detail scanning (from Excel row 28 onward).
    Uses the last row in the sheet that contains any non-empty cell.
    """
    end = DETAIL_START_ROW
    for row_idx in range(DETAIL_START_ROW, df.shape[0]):
        if _row_has_any_value(df.iloc[row_idx]):
            end = row_idx + 1
    return max(end, DETAIL_START_ROW + 1)


def validate_calculation_sheet_header_fields(
    calculation_sheet_no: str,
    drawing_no: str,
    description: str,
    file_name: str,
) -> None:
    if not calculation_sheet_no:
        raise ValueError(f"File {file_name} has empty calculation no.")
    if not drawing_no:
        raise ValueError(f"File {file_name} has empty invoice no.")
    if not description:
        raise ValueError(f"File {file_name} has empty description.")


def _sort_period_keys(periods: Iterable[str]) -> List[str]:
    return sorted(set(periods), key=lambda key: (len(key), key))


def collect_entry_periods(df, col_index: int, item_count: int = 1) -> List[str]:
    """Collect unique non-empty past invoice ids for an item (row 28+)."""
    period_col = period_column_index(col_index, item_count)
    if period_col < 0 or period_col >= df.shape[1]:
        return []

    periods: set[str] = set()
    row_limit = get_detail_row_end_exclusive(df)
    for row_idx in range(DETAIL_START_ROW, row_limit):
        period = _normalize_period_value(df.iloc[row_idx, period_col])
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


def read_entry_submitted_invoice_id(df, col_index: int) -> Optional[str]:
    """Read item invoice id from row 2 only; None means the item was not submitted."""
    if col_index < df.shape[1]:
        cell = df.iloc[INVOICE_ID_ROW, col_index]
        if pd.notna(cell):
            text = str(cell).strip()
            if text and text.lower() not in _INVALID_PERIOD_STRINGS:
                return text
    return None


def read_entry_current_invoice_id(
    df, col_index: int, sheet_drawing_no: str = ""
) -> str:
    """Read current invoice id from row 2 of an item column; fall back to sheet C2."""
    submitted = read_entry_submitted_invoice_id(df, col_index)
    if submitted:
        return submitted
    return str(sheet_drawing_no or "").strip()


def resolve_calc_entry_current_invoice_id(
    calc_entry: Any, calculation_sheet: Any | None = None
) -> str:
    """Resolve the active invoice id for a calculation entry."""
    current = str(getattr(calc_entry, "current_invoice_id", None) or "").strip()
    if not current:
        breakdown = getattr(calc_entry, "submission_breakdown", None) or {}
        if isinstance(breakdown, dict):
            current = str(breakdown.get("current_drawing_no") or "").strip()
    if not current and calculation_sheet is not None:
        current = str(getattr(calculation_sheet, "drawing_no", None) or "").strip()
    return current


def compute_submission_breakdown(
    df,
    col_index: int,
    current_drawing_no: str,
    sheet_periods: Optional[List[str]] = None,
    item_count: int = 1,
) -> Tuple[Dict[str, Any], float]:
    """
    Sum submitted quantities from detail rows (row 28 through last sheet row with data).

    Past invoice ids come from column B when the sheet has one item, otherwise from
    the column immediately before the item column. Every unique period for this item
    gets a row (0 when no qty). Rows with empty/invalid invoice ids accumulate into
    left_submitted.
    """
    current_drawing_no = str(current_drawing_no or "").strip()
    period_col = period_column_index(col_index, item_count)
    if sheet_periods is None:
        sheet_periods = collect_entry_periods(df, col_index, item_count)

    period_keys = list(sheet_periods)
    if current_drawing_no and current_drawing_no not in period_keys:
        period_keys = _sort_period_keys(period_keys + [current_drawing_no])

    periods = {period: 0.0 for period in period_keys}
    left_submitted = 0.0

    row_limit = get_detail_row_end_exclusive(df)
    for row_idx in range(DETAIL_START_ROW, row_limit):
        if col_index >= df.shape[1]:
            break

        qty = _safe_float(df.iloc[row_idx, col_index])
        period = None
        if 0 <= period_col < df.shape[1]:
            period = _normalize_period_value(df.iloc[row_idx, period_col])

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
    current = str(getattr(entry, "current_invoice_id", None) or "").strip()
    if not current:
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


def cumulative_submitted_quantity(breakdown: Optional[Dict[str, Any]]) -> float:
    """Sum all invoice-period quantities; excludes left_submitted."""
    periods = _breakdown_periods(breakdown)
    return float(sum(float(value or 0) for value in periods.values()))


def entry_cumulative_submitted_quantity(entry: Any) -> float:
    """Cumulative submitted qty for an entry, falling back to quantity_submitted."""
    breakdown = getattr(entry, "submission_breakdown", None)
    if isinstance(breakdown, dict) and breakdown:
        cumulative = cumulative_submitted_quantity(breakdown)
        if cumulative > 0:
            return cumulative
    return float(getattr(entry, "quantity_submitted", 0) or 0)


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

SUBROW_MERGE_HEADERS = (
    "Description",
    "Calculation Sheet No",
    "Estimated Quantity",
)

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
    from utils.period_details_utils import (
        get_period_detail,
        period_submission_percentage,
        resolve_entry_current_period,
    )

    breakdown = getattr(entry, "submission_breakdown", None) or {}
    current_drawing_no = _entry_current_drawing_no(entry, breakdown)
    current_detail = get_period_detail(breakdown, current_drawing_no)
    current_qty = float(entry.quantity_submitted or 0)
    row = {
        "Description": entry.description or "",
        "Calculation Sheet No": entry.calculation_sheet_no or "",
        "Invoice No": entry.drawing_no or "",
        "Estimated Quantity": float(entry.estimated_quantity or 0),
        "Submission Percentage": period_submission_percentage(
            entry, breakdown, current_drawing_no, current_qty
        ),
        "Quantity Submitted": current_qty,
        "Internal Quantity": float(current_detail.get("internal_quantity") or 0),
        "Approved by Project Manager": float(
            current_detail.get("approved_by_project_manager") or 0
        ),
        "Notes": notes_value or current_detail.get("notes") or entry.notes or "",
        "Supervisor Notes": current_detail.get("supervisor_notes")
        or getattr(entry, "supervisor_notes", None)
        or "",
    }
    for period in period_keys:
        header = period_header_key(period)
        if period == current_drawing_no:
            row[header] = 0.0
        else:
            row[header] = period_quantity(breakdown, period)
    row[LEFT_SUBMITTED_HEADER] = left_submitted_quantity(breakdown)
    return row


def get_past_period_subrows_for_export(entry: Any) -> List[Tuple[str, float]]:
    """Past invoice periods and quantities for subrow export (excludes current period)."""
    breakdown = getattr(entry, "submission_breakdown", None) or {}
    if not isinstance(breakdown, dict):
        return []

    current = _entry_current_drawing_no(entry, breakdown)
    rows: List[Tuple[str, float]] = []
    for period in breakdown_period_keys(breakdown):
        if period == current:
            continue
        qty = period_quantity(breakdown, period)
        if qty == 0:
            continue
        rows.append((period, qty))
    return rows


def _export_submission_percentage(estimated: float, submitted: float) -> float:
    estimated = float(estimated or 0)
    submitted = float(submitted or 0)
    if estimated > 0:
        return (submitted / estimated) * 100.0
    return 100.0


def build_concentration_export_subrow_values(
    entry: Any,
    period: str,
    qty: float,
    filtered_headers: List[str],
) -> Dict[str, Any]:
    """One past-invoice subrow aligned with concentration entry table columns."""
    from utils.period_details_utils import get_period_detail, period_submission_percentage

    detail = get_period_detail(getattr(entry, "submission_breakdown", None), period)
    row: Dict[str, Any] = {header: None for header in filtered_headers}
    if "Invoice No" in filtered_headers:
        row["Invoice No"] = period
    if "Submission Percentage" in filtered_headers:
        row["Submission Percentage"] = period_submission_percentage(
            entry, getattr(entry, "submission_breakdown", None), period, qty
        )
    if "Quantity Submitted" in filtered_headers:
        row["Quantity Submitted"] = float(qty)
    if "Internal Quantity" in filtered_headers:
        row["Internal Quantity"] = float(detail.get("internal_quantity") or 0)
    if "Approved by Project Manager" in filtered_headers:
        row["Approved by Project Manager"] = float(
            detail.get("approved_by_project_manager") or 0
        )
    if "Notes" in filtered_headers:
        row["Notes"] = detail.get("notes") or ""
    if "Supervisor Notes" in filtered_headers:
        row["Supervisor Notes"] = detail.get("supervisor_notes") or ""
    return row


def _apply_subrow_merge_column_values(
    rows: List[Dict[str, Any]], filtered_headers: List[str]
) -> None:
    """Keep shared values on the first row only; clear merge columns on follow-up rows."""
    if len(rows) <= 1:
        return

    main_row = rows[-1]
    for header in SUBROW_MERGE_HEADERS:
        if header not in filtered_headers:
            continue
        shared_value = main_row.get(header, "")
        rows[0][header] = shared_value
        for row in rows[1:]:
            row[header] = None


def build_concentration_export_rows_for_entry(
    entry: Any,
    period_keys: List[str],
    filtered_headers: List[str],
    entry_columns: Optional[Dict[str, Any]] = None,
    notes_value: str = "",
) -> List[Dict[str, Any]]:
    """Main entry row plus optional past-invoice subrows placed before it."""
    rows: List[Dict[str, Any]] = []
    if entry_columns and entry_columns.get("include_past_months_submitted_subrows"):
        for period, qty in get_past_period_subrows_for_export(entry):
            rows.append(
                build_concentration_export_subrow_values(
                    entry, period, qty, filtered_headers
                )
            )
    rows.append(
        build_concentration_export_row_values(entry, period_keys, notes_value)
    )
    if entry_columns and entry_columns.get("include_past_months_submitted_subrows"):
        _apply_subrow_merge_column_values(rows, filtered_headers)
    return rows


def build_all_concentration_export_rows(
    entries: Iterable[Any],
    period_keys: List[str],
    filtered_headers: List[str],
    entry_columns: Optional[Dict[str, Any]] = None,
    notes_getter=None,
) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    for entry in entries:
        notes = notes_getter(entry) if notes_getter else (getattr(entry, "notes", None) or "")
        result.extend(
            build_concentration_export_rows_for_entry(
                entry, period_keys, filtered_headers, entry_columns, notes
            )
        )
    return result


def concentration_export_main_row_offsets(
    entries: Iterable[Any],
    entry_columns: Optional[Dict[str, Any]],
) -> List[int]:
    """0-based index of each main entry row within the expanded export row list."""
    offsets: List[int] = []
    offset = 0
    include_subrows = bool(
        entry_columns and entry_columns.get("include_past_months_submitted_subrows")
    )
    for entry in entries:
        if include_subrows:
            offset += len(get_past_period_subrows_for_export(entry))
        offsets.append(offset)
        offset += 1
    return offsets


def concentration_export_entry_row_groups(
    entries: Iterable[Any],
    entry_columns: Optional[Dict[str, Any]],
) -> List[Tuple[int, int]]:
    """Inclusive start/end indices for each entry block in the flat export row list."""
    groups: List[Tuple[int, int]] = []
    idx = 0
    include_subrows = bool(
        entry_columns and entry_columns.get("include_past_months_submitted_subrows")
    )
    for entry in entries:
        row_count = 1
        if include_subrows:
            row_count += len(get_past_period_subrows_for_export(entry))
        start = idx
        end = idx + row_count - 1
        groups.append((start, end))
        idx += row_count
    return groups


def concentration_export_merge_column_indices(
    filtered_headers: List[str],
) -> List[int]:
    return [
        filtered_headers.index(header)
        for header in SUBROW_MERGE_HEADERS
        if header in filtered_headers
    ]


def apply_concentration_export_subrow_merges(
    worksheet,
    data_start_row_1based: int,
    groups: List[Tuple[int, int]],
    merge_column_indices: List[int],
) -> None:
    """Merge shared description/calc sheet/est qty cells across subrow blocks."""
    if not groups or not merge_column_indices:
        return

    for start, end in groups:
        if start >= end:
            continue
        for col_index in merge_column_indices:
            worksheet.merge_cells(
                start_row=data_start_row_1based + start,
                end_row=data_start_row_1based + end,
                start_column=col_index + 1,
                end_column=col_index + 1,
            )


def add_concentration_export_subrow_pdf_spans(
    table_style,
    groups: List[Tuple[int, int]],
    merge_column_indices: List[int],
    data_row_offset: int = 1,
) -> None:
    """Apply PDF table SPANs for merged subrow columns."""
    if not groups or not merge_column_indices:
        return

    for start, end in groups:
        if start >= end:
            continue
        for col_idx in merge_column_indices:
            table_style.add(
                "SPAN",
                (col_idx, data_row_offset + start),
                (col_idx, data_row_offset + end),
            )
            table_style.add(
                "VALIGN",
                (col_idx, data_row_offset + start),
                (col_idx, data_row_offset + end),
                "TOP",
            )


def translated_merge_column_indices(
    filtered_headers: List[str],
    headers_translations: Dict[str, str],
    current_headers: List[str],
) -> List[int]:
    indices: List[int] = []
    for header in SUBROW_MERGE_HEADERS:
        if header not in filtered_headers:
            continue
        translated = headers_translations.get(header, header)
        indices.append(current_headers.index(translated))
    return indices


def concentration_export_link_row_offsets(
    entries: Iterable[Any],
    entry_columns: Optional[Dict[str, Any]],
) -> List[int]:
    """Row index (within export data rows) that holds the calc sheet no link cell."""
    return [start for start, _ in concentration_export_entry_row_groups(entries, entry_columns)]


def concentration_export_header_translations(language: str) -> Dict[str, str]:
    if language == "he":
        base = {
            "Description": "תיאור:",
            "Calculation Sheet No": "מס' דף חישוב",
            "Invoice No": "חן מס'",
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
            if value in ("", None):
                formatted.append("")
            else:
                formatted.append(f"{float(value):,.1f}%")
        elif header in text_headers:
            formatted.append(str(value or ""))
        elif value in ("", None):
            formatted.append("")
        else:
            formatted.append(f"{float(value or 0):,.2f}")
    return formatted


def build_concentration_export_totals_row(
    entries: Iterable[Any],
    filtered_headers: List[str],
    period_keys: List[str],
    totals_label: str,
    entry_columns: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    totals: Dict[str, Any] = {header: "" for header in filtered_headers}
    totals["Description"] = totals_label
    if "Submission Percentage" in filtered_headers:
        totals["Submission Percentage"] = ""
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
            if entry_columns and entry_columns.get(
                "include_past_months_submitted_subrows"
            ):
                totals[header] = sum(
                    entry_cumulative_submitted_quantity(entry) for entry in entries
                )
            else:
                totals[header] = sum(
                    float(entry.quantity_submitted or 0) for entry in entries
                )
        elif header == "Internal Quantity":
            from utils.period_details_utils import entry_total_internal_quantity

            totals[header] = sum(
                entry_total_internal_quantity(entry) for entry in entries
            )
        elif header == "Approved by Project Manager":
            from utils.period_details_utils import entry_total_approved_quantity

            totals[header] = sum(
                entry_total_approved_quantity(entry) for entry in entries
            )
    return totals
