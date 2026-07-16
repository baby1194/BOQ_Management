from types import SimpleNamespace

from utils.concentration_utils import calc_sheet_nos_submitted_equals_approved


def test_calc_sheet_nos_submitted_equals_approved_matches_equal_totals():
    entries = [
        SimpleNamespace(
            calculation_sheet_no="20/1",
            quantity_submitted=100.0,
            approved_by_project_manager=100.0,
            submission_breakdown=None,
        ),
        SimpleNamespace(
            calculation_sheet_no="20/2",
            quantity_submitted=50.0,
            approved_by_project_manager=25.0,
            submission_breakdown=None,
        ),
    ]

    assert calc_sheet_nos_submitted_equals_approved(entries) == {"20/1"}


def test_concentration_sheet_cumulative_submitted_equals_approved():
    from utils.concentration_utils import (
        concentration_sheet_cumulative_submitted_equals_approved,
    )

    fully_approved = [
        SimpleNamespace(
            calculation_sheet_no="20/1",
            quantity_submitted=100.0,
            approved_by_project_manager=60.0,
            submission_breakdown=None,
        ),
        SimpleNamespace(
            calculation_sheet_no="20/2",
            quantity_submitted=50.0,
            approved_by_project_manager=90.0,
            submission_breakdown=None,
        ),
    ]
    partially_approved = [
        SimpleNamespace(
            calculation_sheet_no="20/1",
            quantity_submitted=100.0,
            approved_by_project_manager=50.0,
            submission_breakdown=None,
        ),
    ]

    assert concentration_sheet_cumulative_submitted_equals_approved(fully_approved)
    assert not concentration_sheet_cumulative_submitted_equals_approved(
        partially_approved
    )


def test_calc_sheet_nos_not_submitted_from_concentration_entries():
    from utils.concentration_utils import calc_sheet_nos_not_submitted

    entries = [
        SimpleNamespace(
            calculation_sheet_no="20/1",
            drawing_no="03",
        ),
        SimpleNamespace(
            calculation_sheet_no="20/2",
            drawing_no=None,
        ),
        SimpleNamespace(
            calculation_sheet_no="20/3",
            drawing_no="",
        ),
    ]

    assert calc_sheet_nos_not_submitted(entries) == {"20/2", "20/3"}


def test_calc_sheet_nos_to_skip_for_selective_export_combines_rules():
    from utils.concentration_utils import calc_sheet_nos_to_skip_for_selective_export

    entries = [
        SimpleNamespace(
            calculation_sheet_no="20/1",
            drawing_no="03",
            quantity_submitted=100.0,
            approved_by_project_manager=100.0,
            submission_breakdown=None,
        ),
        SimpleNamespace(
            calculation_sheet_no="20/2",
            drawing_no=None,
            quantity_submitted=50.0,
            approved_by_project_manager=10.0,
            submission_breakdown=None,
        ),
        SimpleNamespace(
            calculation_sheet_no="20/3",
            drawing_no="04",
            quantity_submitted=50.0,
            approved_by_project_manager=10.0,
            submission_breakdown=None,
        ),
    ]

    assert calc_sheet_nos_to_skip_for_selective_export(entries) == {
        "20/1",
        "20/2",
    }


def test_calc_sheet_nos_submitted_equals_approved_sums_multiple_entries_per_sheet():
    entries = [
        SimpleNamespace(
            calculation_sheet_no="20/3",
            quantity_submitted=30.0,
            approved_by_project_manager=10.0,
            submission_breakdown=None,
        ),
        SimpleNamespace(
            calculation_sheet_no="20/3",
            quantity_submitted=20.0,
            approved_by_project_manager=40.0,
            submission_breakdown=None,
        ),
    ]

    assert calc_sheet_nos_submitted_equals_approved(entries) == {"20/3"}


def test_copy_drawing_files_to_fatina_includes_all_periods(monkeypatch):
    from routers.file_import import copy_concentration_entry_drawing_files_to_fatina

    copied_paths: list[list[str]] = []

    def fake_copy(section_number, calculation_sheet_no, paths):
        copied_paths.append(list(paths))
        return len(paths)

    monkeypatch.setattr(
        "fatina_paths.copy_files_to_calc_sheet_dir",
        fake_copy,
    )

    entry = SimpleNamespace(
        calculation_sheet_no="20/1",
        drawing_files=["C:/uploads/current.pdf"],
        submission_breakdown={
            "current_drawing_no": "02",
            "period_details": {
                "01": {"drawing_files": ["C:/uploads/past-period.pdf"]},
                "02": {"drawing_files": ["C:/uploads/current.pdf"]},
            },
        },
    )

    count = copy_concentration_entry_drawing_files_to_fatina(
        db=None,
        section_number="Section A",
        entries=[entry],
    )

    assert count == 2
    assert copied_paths == [
        ["C:/uploads/current.pdf", "C:/uploads/past-period.pdf"],
    ]


def test_copy_drawing_files_to_fatina_skips_when_only_subrow_has_files(monkeypatch):
    from routers.file_import import copy_concentration_entry_drawing_files_to_fatina

    copied_paths: list[list[str]] = []

    def fake_copy(section_number, calculation_sheet_no, paths):
        copied_paths.append(list(paths))
        return len(paths)

    monkeypatch.setattr(
        "fatina_paths.copy_files_to_calc_sheet_dir",
        fake_copy,
    )

    entry = SimpleNamespace(
        calculation_sheet_no="20/1",
        drawing_files=[],
        submission_breakdown={
            "current_drawing_no": "02",
            "period_details": {
                "01": {"drawing_files": ["C:/uploads/past-only.pdf"]},
            },
        },
    )

    count = copy_concentration_entry_drawing_files_to_fatina(
        db=None,
        section_number="Section A",
        entries=[entry],
    )

    assert count == 1
    assert copied_paths == [["C:/uploads/past-only.pdf"]]
