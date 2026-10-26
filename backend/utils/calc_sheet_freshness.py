"""Compare a calculation sheet's saved file date with the file on disk.

The check only reads file dates. It does not open the workbooks, so it can
run across a whole project without the cost of Track.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

# A save and a track can land a second apart. Ignore noise inside this window.
FILE_NEWER_TOLERANCE = timedelta(seconds=2)


def as_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def file_modified_at(path: Path) -> Optional[datetime]:
    try:
        if not path.is_file():
            return None
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    except OSError:
        return None


def recorded_system_time(sheet: Any) -> Optional[datetime]:
    """When the system last took this sheet from the file.

    source_modified_at is the file's own date at the last import or track.
    Older rows fall back to the later of the sheet's update and import dates.
    """
    stored = as_utc(getattr(sheet, "source_modified_at", None))
    if stored is not None:
        return stored
    candidates = [
        as_utc(getattr(sheet, "updated_at", None)),
        as_utc(getattr(sheet, "import_date", None)),
        as_utc(getattr(sheet, "created_at", None)),
    ]
    present = [item for item in candidates if item is not None]
    return max(present) if present else None


def remember_source_modified_at(sheet: Any, path: Optional[Path] = None) -> None:
    """Store the file date the system just read, so a later save shows up."""
    if path is None:
        text = str(getattr(sheet, "source_file_path", None) or "").strip()
        if not text:
            return
        path = Path(text)
    modified = file_modified_at(path)
    if modified is not None:
        sheet.source_modified_at = modified


def sheet_freshness(sheet: Any) -> Optional[dict]:
    """A row when the computer file is newer or missing. None when it matches."""
    path_text = str(getattr(sheet, "source_file_path", None) or "").strip()
    path = Path(path_text) if path_text else None
    file_at = file_modified_at(path) if path is not None else None
    system_at = recorded_system_time(sheet)
    status = None
    if file_at is None:
        status = "missing"
    elif system_at is None or file_at > system_at + FILE_NEWER_TOLERANCE:
        status = "newer"
    if status is None:
        return None
    return {
        "id": sheet.id,
        "calculation_sheet_no": sheet.calculation_sheet_no,
        "drawing_no": getattr(sheet, "drawing_no", None) or "",
        "file_name": getattr(sheet, "file_name", None) or "",
        "source_file_path": path_text or None,
        "status": status,
        "system_updated_at": system_at,
        "file_updated_at": file_at,
    }
