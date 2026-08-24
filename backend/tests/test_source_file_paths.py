"""Tests for calculation-sheet source file location detection."""

from types import SimpleNamespace

from utils.source_file_paths import (
    collect_missing_source_locations,
    detect_moved_source_locations,
    merge_location_changes,
    normalize_source_file_path,
    source_paths_differ,
)


def test_source_paths_differ_normalizes_slashes_and_case():
    assert not source_paths_differ(
        r"D:\Projects\Calc\sheet.xlsx",
        r"d:/Projects/Calc/sheet.xlsx",
    )
    assert source_paths_differ(
        r"D:\Projects\Old\sheet.xlsx",
        r"D:\Projects\New\sheet.xlsx",
    )


def test_detect_moved_source_locations_by_filename():
    sheets = [
        SimpleNamespace(
            calculation_sheet_no="12",
            drawing_no="03",
            file_name="sheet.xlsx",
            source_file_path=r"D:\Projects\Old\sheet.xlsx",
        )
    ]
    changes = detect_moved_source_locations(
        sheets, [r"D:\Projects\New\sheet.xlsx"]
    )
    assert len(changes) == 1
    assert changes[0]["calculation_sheet_no"] == "12"
    assert changes[0]["reason"] == "moved"
    assert normalize_source_file_path(changes[0]["new_path"]).endswith(
        "sheet.xlsx"
    )


def test_detect_moved_source_locations_ignores_same_path():
    path = r"D:\Projects\Calc\sheet.xlsx"
    sheets = [
        SimpleNamespace(
            calculation_sheet_no="12",
            drawing_no="03",
            file_name="sheet.xlsx",
            source_file_path=path,
        )
    ]
    assert detect_moved_source_locations(sheets, [path]) == []


def test_collect_missing_source_locations():
    sheets = [
        SimpleNamespace(
            calculation_sheet_no="8",
            drawing_no="01",
            source_file_path=r"D:\missing\does-not-exist.xlsx",
        ),
        SimpleNamespace(
            calculation_sheet_no="9",
            drawing_no="02",
            source_file_path=None,
        ),
    ]
    missing = collect_missing_source_locations(sheets)
    assert {item["calculation_sheet_no"] for item in missing} == {"8", "9"}
    assert all(item["reason"] == "missing" for item in missing)


def test_merge_prefers_moved_over_missing():
    merged = merge_location_changes(
        [
            {
                "calculation_sheet_no": "12",
                "drawing_no": "03",
                "previous_path": r"D:\Old\sheet.xlsx",
                "new_path": None,
                "reason": "missing",
            }
        ],
        [
            {
                "calculation_sheet_no": "12",
                "drawing_no": "03",
                "previous_path": r"D:\Old\sheet.xlsx",
                "new_path": r"D:\New\sheet.xlsx",
                "reason": "moved",
            }
        ],
    )
    assert len(merged) == 1
    assert merged[0]["reason"] == "moved"
    assert merged[0]["new_path"] == r"D:\New\sheet.xlsx"
