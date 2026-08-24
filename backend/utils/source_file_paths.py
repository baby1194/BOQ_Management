"""Compare and detect moved or missing calculation-sheet source files."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


def normalize_source_file_path(path: Optional[str]) -> str:
    """Return a comparable absolute path (case-normalized on Windows)."""
    if not path or not str(path).strip():
        return ""
    raw = str(path).strip().strip('"')
    try:
        return os.path.normcase(str(Path(raw).expanduser().resolve()))
    except Exception:
        return os.path.normcase(os.path.normpath(raw.replace("/", os.sep)))


def source_paths_differ(old_path: Optional[str], new_path: Optional[str]) -> bool:
    old_normalized = normalize_source_file_path(old_path)
    new_normalized = normalize_source_file_path(new_path)
    if not old_normalized or not new_normalized:
        return False
    return old_normalized != new_normalized


def is_source_file_missing(path: Optional[str]) -> bool:
    if not path or not str(path).strip():
        return True
    try:
        return not Path(str(path).strip()).is_file()
    except Exception:
        return True


def build_location_change(
    *,
    calculation_sheet_no: str,
    drawing_no: str = "",
    previous_path: Optional[str] = None,
    new_path: Optional[str] = None,
    reason: str,
) -> Dict[str, Any]:
    return {
        "calculation_sheet_no": calculation_sheet_no or "",
        "drawing_no": drawing_no or "",
        "previous_path": previous_path,
        "new_path": new_path,
        "reason": reason,
    }


def _sheet_filenames(sheet: Any) -> set[str]:
    names: set[str] = set()
    file_name = getattr(sheet, "file_name", None)
    if file_name:
        names.add(Path(str(file_name)).name.lower())
    source_file_path = getattr(sheet, "source_file_path", None)
    if source_file_path:
        names.add(Path(str(source_file_path)).name.lower())
    return names


def detect_moved_source_locations(
    existing_sheets: Iterable[Any],
    new_file_paths: Iterable[str],
) -> List[Dict[str, Any]]:
    """
    Flag already-imported sheets whose saved path differs from a newly listed file
    with the same file name (typical after a folder move).
    """
    new_by_name: Dict[str, List[str]] = {}
    for path_str in new_file_paths:
        if not path_str:
            continue
        new_by_name.setdefault(Path(str(path_str)).name.lower(), []).append(str(path_str))

    changes: List[Dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for sheet in existing_sheets:
        sheet_no = str(getattr(sheet, "calculation_sheet_no", "") or "")
        drawing_no = str(getattr(sheet, "drawing_no", "") or "")
        previous_path = getattr(sheet, "source_file_path", None)
        for name in _sheet_filenames(sheet):
            for new_path in new_by_name.get(name, []):
                if not source_paths_differ(previous_path, new_path):
                    continue
                key = (sheet_no, normalize_source_file_path(new_path))
                if key in seen:
                    continue
                seen.add(key)
                changes.append(
                    build_location_change(
                        calculation_sheet_no=sheet_no,
                        drawing_no=drawing_no,
                        previous_path=previous_path,
                        new_path=new_path,
                        reason="moved",
                    )
                )
    return changes


def collect_missing_source_locations(existing_sheets: Iterable[Any]) -> List[Dict[str, Any]]:
    """Sheets whose saved source file is unset or no longer on disk."""
    changes: List[Dict[str, Any]] = []
    for sheet in existing_sheets:
        previous_path = getattr(sheet, "source_file_path", None)
        if not is_source_file_missing(previous_path):
            continue
        changes.append(
            build_location_change(
                calculation_sheet_no=str(getattr(sheet, "calculation_sheet_no", "") or ""),
                drawing_no=str(getattr(sheet, "drawing_no", "") or ""),
                previous_path=previous_path,
                new_path=None,
                reason="missing",
            )
        )
    return changes


def merge_location_changes(*groups: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate location-change records, preferring moved over missing for the same sheet."""
    by_sheet: Dict[str, Dict[str, Any]] = {}
    extras: List[Dict[str, Any]] = []
    for group in groups:
        for change in group:
            sheet_no = str(change.get("calculation_sheet_no") or "")
            if not sheet_no:
                extras.append(change)
                continue
            existing = by_sheet.get(sheet_no)
            if existing is None:
                by_sheet[sheet_no] = change
                continue
            if existing.get("reason") == "missing" and change.get("reason") == "moved":
                by_sheet[sheet_no] = change
    return list(by_sheet.values()) + extras
