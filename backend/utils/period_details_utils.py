"""Per-invoice period metadata stored inside submission_breakdown.period_details."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from utils.calculation_sheet_utils import _entry_current_drawing_no


def _compute_submission_percentage(estimated: float, submitted: float) -> float:
    estimated = float(estimated or 0)
    submitted = float(submitted or 0)
    if estimated > 0:
        return (submitted / estimated) * 100.0
    return 100.0

PERIOD_DETAIL_FIELDS = (
    "internal_quantity",
    "approved_by_project_manager",
    "submission_percentage",
    "notes",
    "supervisor_notes",
    "drawing_files",
    "invoice_description",
)


def _normalize_drawing_files(value: Any) -> List[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(path) for path in value if path]
    return []


def _empty_period_detail() -> Dict[str, Any]:
    return {
        "internal_quantity": 0.0,
        "approved_by_project_manager": 0.0,
        "submission_percentage": None,
        "notes": "",
        "supervisor_notes": "",
        "drawing_files": [],
        "invoice_description": "",
    }


def _normalize_breakdown(breakdown: Any) -> Dict[str, Any]:
    if isinstance(breakdown, dict):
        return breakdown
    return {}


def normalize_period_detail(detail: Any) -> Dict[str, Any]:
    result = _empty_period_detail()
    if not isinstance(detail, dict):
        return result
    result["internal_quantity"] = float(detail.get("internal_quantity") or 0)
    result["approved_by_project_manager"] = float(
        detail.get("approved_by_project_manager") or 0
    )
    submission_percentage = detail.get("submission_percentage")
    if submission_percentage is not None:
        result["submission_percentage"] = float(submission_percentage)
    result["notes"] = str(detail.get("notes") or "")
    result["supervisor_notes"] = str(detail.get("supervisor_notes") or "")
    result["drawing_files"] = _normalize_drawing_files(detail.get("drawing_files"))
    result["invoice_description"] = str(detail.get("invoice_description") or "")
    return result


def get_period_details_map(breakdown: Any) -> Dict[str, Dict[str, Any]]:
    breakdown = _normalize_breakdown(breakdown)
    raw = breakdown.get("period_details") or {}
    if not isinstance(raw, dict):
        return {}
    return {
        str(period): normalize_period_detail(detail)
        for period, detail in raw.items()
        if period
    }


def resolve_entry_current_period(entry: Any) -> str:
    breakdown = _normalize_breakdown(getattr(entry, "submission_breakdown", None))
    return _entry_current_drawing_no(entry, breakdown)


def get_period_detail(breakdown: Any, period: str) -> Dict[str, Any]:
    if not period:
        return _empty_period_detail()
    return normalize_period_detail(get_period_details_map(breakdown).get(period))


def period_submission_percentage(
    entry: Any,
    breakdown: Any,
    period: str,
    qty: float,
) -> float:
    detail = get_period_detail(breakdown, period)
    stored = detail.get("submission_percentage")
    if stored is not None:
        return float(stored)
    estimated = float(getattr(entry, "estimated_quantity", 0) or 0)
    return _compute_submission_percentage(estimated, qty)


def merge_breakdown_preserve_period_details(
    old_breakdown: Any, new_breakdown: Any
) -> Dict[str, Any]:
    merged = dict(_normalize_breakdown(new_breakdown))
    old_details = get_period_details_map(old_breakdown)
    if old_details:
        merged["period_details"] = old_details
    return merged


def _entry_level_period_detail_snapshot(entry: Any) -> Dict[str, Any]:
    return normalize_period_detail(
        {
            "internal_quantity": getattr(entry, "internal_quantity", 0),
            "approved_by_project_manager": getattr(
                entry, "approved_by_project_manager", 0
            ),
            "submission_percentage": getattr(entry, "submission_percentage", None),
            "notes": getattr(entry, "notes", None) or "",
            "supervisor_notes": getattr(entry, "supervisor_notes", None) or "",
            "drawing_files": getattr(entry, "drawing_files", None),
            "invoice_description": getattr(entry, "invoice_description", None) or "",
        }
    )


def persist_entry_level_fields_to_period(
    entry: Any, period: str, breakdown: Any | None = None
) -> bool:
    """
    Save top-level editable fields onto a specific invoice period when that period
    does not already have stored details. Used before switching to a new invoice.

    Work description (invoice_description) is always refreshed from the top-level
    field so the outgoing invoice keeps the description that was current for it.
    Returns True when submission_breakdown was modified.
    """
    period = str(period or "").strip()
    if not period:
        return False

    breakdown = dict(_normalize_breakdown(breakdown or getattr(entry, "submission_breakdown", None)))
    if not breakdown:
        return False

    details = get_period_details_map(breakdown)
    changed = False
    incoming_desc = str(getattr(entry, "invoice_description", None) or "")

    if period not in details:
        details[period] = _entry_level_period_detail_snapshot(entry)
        changed = True
    else:
        detail = normalize_period_detail(details[period])
        if str(detail.get("invoice_description") or "") != incoming_desc:
            detail["invoice_description"] = incoming_desc
            details[period] = detail
            changed = True

    if changed:
        breakdown["period_details"] = details
        entry.submission_breakdown = breakdown
    return changed


def migrate_entry_period_details(entry: Any) -> bool:
    """
    Ensure the current invoice has a period_details row.

    - Legacy entries (no period_details yet): lift top-level fields once.
    - New invoice periods after tracking: start with empty editable fields.
    Returns True when submission_breakdown was modified.
    """
    breakdown = _normalize_breakdown(getattr(entry, "submission_breakdown", None))
    if not breakdown:
        return False

    period = resolve_entry_current_period(entry)
    if not period:
        return False

    details = get_period_details_map(breakdown)
    changed = False

    if period not in details:
        if details:
            details[period] = _empty_period_detail()
        else:
            details[period] = _entry_level_period_detail_snapshot(entry)
        changed = True
    else:
        detail = normalize_period_detail(details[period])
        legacy_files = _normalize_drawing_files(getattr(entry, "drawing_files", None))
        if legacy_files and not detail["drawing_files"]:
            detail["drawing_files"] = legacy_files
            details[period] = detail
            changed = True

    if changed:
        breakdown = dict(breakdown)
        breakdown["period_details"] = details
        entry.submission_breakdown = breakdown
    return changed


def apply_current_period_to_entry_fields(entry: Any) -> None:
    """Mirror current invoice period_details onto top-level entry fields for API compat."""
    breakdown = _normalize_breakdown(getattr(entry, "submission_breakdown", None))
    if not breakdown:
        return

    period = resolve_entry_current_period(entry)
    if not period:
        return

    detail = get_period_detail(breakdown, period)
    entry.internal_quantity = detail["internal_quantity"]
    entry.approved_by_project_manager = detail["approved_by_project_manager"]
    if detail["submission_percentage"] is not None:
        entry.submission_percentage = detail["submission_percentage"]
    entry.notes = detail["notes"] or None
    entry.supervisor_notes = detail["supervisor_notes"] or None
    entry.drawing_files = detail["drawing_files"]
    entry.invoice_description = detail["invoice_description"] or None


def set_period_detail_fields(
    entry: Any, period: str, updates: Dict[str, Any]
) -> None:
    period = str(period or "").strip()
    if not period:
        return

    breakdown = dict(_normalize_breakdown(getattr(entry, "submission_breakdown", None)))
    details = get_period_details_map(breakdown)
    # New period rows must start from top-level fields so partial updates
    # (e.g. drawing_files only) do not wipe existing internal/approved qty.
    if period in details:
        current = normalize_period_detail(details[period])
    else:
        current = _entry_level_period_detail_snapshot(entry)

    for field in PERIOD_DETAIL_FIELDS:
        if field not in updates:
            continue
        value = updates[field]
        if field == "drawing_files":
            current[field] = _normalize_drawing_files(value)
        elif field in ("notes", "supervisor_notes", "invoice_description"):
            current[field] = str(value or "")
        elif field == "submission_percentage":
            current[field] = float(value) if value is not None else None
        else:
            current[field] = float(value or 0)

    details[period] = current
    breakdown["period_details"] = details
    entry.submission_breakdown = breakdown

    if period == resolve_entry_current_period(entry):
        apply_current_period_to_entry_fields(entry)


def entry_total_internal_quantity(entry: Any) -> float:
    breakdown = getattr(entry, "submission_breakdown", None)
    details = get_period_details_map(breakdown)
    if details:
        return sum(float(d["internal_quantity"] or 0) for d in details.values())
    return float(getattr(entry, "internal_quantity", 0) or 0)


def entry_total_approved_quantity(entry: Any) -> float:
    breakdown = getattr(entry, "submission_breakdown", None)
    details = get_period_details_map(breakdown)
    if details:
        return sum(
            float(d["approved_by_project_manager"] or 0) for d in details.values()
        )
    return float(getattr(entry, "approved_by_project_manager", 0) or 0)


def entry_all_drawing_files(entry: Any) -> List[str]:
    """All drawing file paths across every invoice period plus legacy entry-level paths."""
    paths: List[str] = []
    seen: set[str] = set()

    def add(paths_to_add: Iterable[str]) -> None:
        for path in paths_to_add:
            if path and path not in seen:
                seen.add(path)
                paths.append(path)

    add(_normalize_drawing_files(getattr(entry, "drawing_files", None)))
    for detail in get_period_details_map(
        getattr(entry, "submission_breakdown", None)
    ).values():
        add(detail.get("drawing_files") or [])
    return paths


def entry_drawing_files_by_invoice(entry: Any) -> Dict[str, List[str]]:
    """Map invoice no -> drawing file paths for Fatina export without a calc sheet."""
    grouped: Dict[str, List[str]] = {}
    seen_by_period: Dict[str, set[str]] = {}

    def add(period: str, paths_to_add: Iterable[str]) -> None:
        period = str(period or "").strip()
        if not period:
            return
        bucket = grouped.setdefault(period, [])
        seen = seen_by_period.setdefault(period, set())
        for path in paths_to_add:
            if path and path not in seen:
                seen.add(path)
                bucket.append(path)

    breakdown = getattr(entry, "submission_breakdown", None)
    for period, detail in get_period_details_map(breakdown).items():
        add(period, detail.get("drawing_files") or [])

    current = resolve_entry_current_period(entry) or str(
        getattr(entry, "drawing_no", "") or ""
    ).strip()
    add(current, _normalize_drawing_files(getattr(entry, "drawing_files", None)))
    return grouped


def find_period_for_drawing_path(entry: Any, resolved_path: str) -> Optional[str]:
    for period, detail in get_period_details_map(
        getattr(entry, "submission_breakdown", None)
    ).items():
        for path in detail.get("drawing_files") or []:
            try:
                if str(Path(path).resolve()) == resolved_path:
                    return period
            except OSError:
                continue
    for path in _normalize_drawing_files(getattr(entry, "drawing_files", None)):
        try:
            if str(Path(path).resolve()) == resolved_path:
                return resolve_entry_current_period(entry) or None
        except OSError:
            continue
    return None


def hydrate_entry_period_details(entry: Any) -> None:
    """Ensure period_details exist and top-level fields reflect the current invoice."""
    migrate_entry_period_details(entry)
    apply_current_period_to_entry_fields(entry)


def iter_entry_period_rows(entry: Any) -> List[Dict[str, Any]]:
    """Past and current invoice rows with qty and editable metadata."""
    breakdown = _normalize_breakdown(getattr(entry, "submission_breakdown", None))
    if not breakdown:
        return []

    current_period = resolve_entry_current_period(entry)
    periods = breakdown.get("periods") or breakdown.get("past_months") or {}
    if not isinstance(periods, dict):
        periods = {}

    rows: List[Dict[str, Any]] = []
    for period in sorted(periods.keys(), key=lambda value: (len(value), value)):
        qty = float(periods.get(period) or 0)
        if qty == 0 and period != current_period:
            continue
        if period == current_period:
            qty = float(getattr(entry, "quantity_submitted", 0) or qty)
        detail = get_period_detail(breakdown, period)
        rows.append(
            {
                "period": period,
                "qty": qty,
                "is_current": period == current_period,
                **detail,
                "submission_percentage": period_submission_percentage(
                    entry, breakdown, period, qty
                ),
            }
        )
    return rows
