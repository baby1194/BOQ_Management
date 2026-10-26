"""File-date check for calculation sheets. No workbook is opened."""

import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from utils.calc_sheet_freshness import remember_source_modified_at, sheet_freshness


def _sheet(path, **overrides):
    values = {
        "id": 7,
        "calculation_sheet_no": "32/7/10",
        "drawing_no": "10",
        "file_name": "sheet.xlsx",
        "source_file_path": str(path) if path else None,
        "source_modified_at": None,
        "updated_at": None,
        "import_date": None,
        "created_at": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _touch(path, when: datetime) -> None:
    path.write_bytes(b"x")
    stamp = when.timestamp()
    os.utime(path, (stamp, stamp))


def test_a_file_saved_after_the_system_copy_is_listed(tmp_path):
    path = tmp_path / "sheet.xlsx"
    _touch(path, datetime.now(timezone.utc))
    sheet = _sheet(
        path,
        source_modified_at=datetime.now(timezone.utc) - timedelta(days=1),
        updated_at=datetime.now(timezone.utc),
    )

    item = sheet_freshness(sheet)

    assert item["status"] == "newer"
    assert item["calculation_sheet_no"] == "32/7/10"


def test_a_matching_file_date_is_not_listed(tmp_path):
    path = tmp_path / "sheet.xlsx"
    saved = datetime.now(timezone.utc) - timedelta(hours=2)
    _touch(path, saved)
    sheet = _sheet(path, source_modified_at=saved)

    assert sheet_freshness(sheet) is None


def test_a_missing_file_is_listed(tmp_path):
    sheet = _sheet(tmp_path / "gone.xlsx", import_date=datetime.now(timezone.utc))

    item = sheet_freshness(sheet)

    assert item["status"] == "missing"
    assert item["file_updated_at"] is None


def test_without_a_stored_file_date_a_later_system_update_counts_as_current(tmp_path):
    path = tmp_path / "sheet.xlsx"
    _touch(path, datetime.now(timezone.utc) - timedelta(days=3))
    sheet = _sheet(path, updated_at=datetime.now(timezone.utc) - timedelta(days=1))

    assert sheet_freshness(sheet) is None


def test_remember_stores_the_file_date(tmp_path):
    path = tmp_path / "sheet.xlsx"
    path.write_bytes(b"x")
    sheet = _sheet(path)

    remember_source_modified_at(sheet, path)

    assert sheet.source_modified_at is not None
    assert sheet_freshness(sheet) is None
