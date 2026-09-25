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

    copied_calc: list[list[str]] = []
    copied_invoice: list[tuple[str, str, list[str]]] = []

    def fake_copy_calc(section_number, calculation_sheet_no, paths):
        copied_calc.append(list(paths))
        return len(paths)

    def fake_copy_invoice(section_number, invoice_no, paths):
        copied_invoice.append((section_number, invoice_no, list(paths)))
        return len(paths)

    monkeypatch.setattr(
        "fatina_paths.copy_files_to_calc_sheet_dir",
        fake_copy_calc,
    )
    monkeypatch.setattr(
        "fatina_paths.copy_files_to_invoice_dir",
        fake_copy_invoice,
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

    assert count == 4
    assert copied_calc == [
        ["C:/uploads/current.pdf", "C:/uploads/past-period.pdf"],
    ]
    assert copied_invoice == [
        ("Section A", "01", ["C:/uploads/past-period.pdf"]),
        ("Section A", "02", ["C:/uploads/current.pdf"]),
    ]


def test_copy_drawing_files_to_fatina_skips_when_only_subrow_has_files(monkeypatch):
    from routers.file_import import copy_concentration_entry_drawing_files_to_fatina

    copied_calc: list[list[str]] = []
    copied_invoice: list[tuple[str, str, list[str]]] = []

    def fake_copy_calc(section_number, calculation_sheet_no, paths):
        copied_calc.append(list(paths))
        return len(paths)

    def fake_copy_invoice(section_number, invoice_no, paths):
        copied_invoice.append((section_number, invoice_no, list(paths)))
        return len(paths)

    monkeypatch.setattr(
        "fatina_paths.copy_files_to_calc_sheet_dir",
        fake_copy_calc,
    )
    monkeypatch.setattr(
        "fatina_paths.copy_files_to_invoice_dir",
        fake_copy_invoice,
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

    assert count == 2
    assert copied_calc == [["C:/uploads/past-only.pdf"]]
    assert copied_invoice == [
        ("Section A", "01", ["C:/uploads/past-only.pdf"]),
    ]


def test_fatina_invoice_folder_name():
    from fatina_paths import fatina_invoice_folder_name

    assert fatina_invoice_folder_name("05") == "05_m"
    assert fatina_invoice_folder_name(" 06 ") == "06_m"


def test_copy_drawing_files_to_fatina_copies_to_invoice_folder_when_no_calc_sheet_no(
    monkeypatch,
):
    from routers.file_import import copy_concentration_entry_drawing_files_to_fatina

    copied_calc: list[tuple[str, str, list[str]]] = []
    copied_invoice: list[tuple[str, str, list[str]]] = []

    def fake_copy_calc(section_number, calculation_sheet_no, paths):
        copied_calc.append((section_number, calculation_sheet_no, list(paths)))
        return len(paths)

    def fake_copy_invoice(section_number, invoice_no, paths):
        copied_invoice.append((section_number, invoice_no, list(paths)))
        return len(paths)

    monkeypatch.setattr("fatina_paths.copy_files_to_calc_sheet_dir", fake_copy_calc)
    monkeypatch.setattr("fatina_paths.copy_files_to_invoice_dir", fake_copy_invoice)

    entry = SimpleNamespace(
        calculation_sheet_no="",
        drawing_files=["C:/uploads/a.pdf"],
        submission_breakdown={
            "current_drawing_no": "01",
            "period_details": {
                "01": {"drawing_files": ["C:/uploads/b.pdf"]},
                "05": {"drawing_files": ["C:/uploads/c.pdf"]},
            },
        },
    )

    count = copy_concentration_entry_drawing_files_to_fatina(
        db=None,
        section_number="Section A",
        entries=[entry],
    )

    assert count == 3
    assert copied_calc == []
    assert copied_invoice == [
        ("Section A", "01", ["C:/uploads/b.pdf", "C:/uploads/a.pdf"]),
        ("Section A", "05", ["C:/uploads/c.pdf"]),
    ]


def test_copy_drawing_files_to_fatina_copies_to_both_when_calc_and_invoice(
    monkeypatch,
):
    from routers.file_import import copy_concentration_entry_drawing_files_to_fatina

    copied_calc: list[tuple[str, str, list[str]]] = []
    copied_invoice: list[tuple[str, str, list[str]]] = []

    def fake_copy_calc(section_number, calculation_sheet_no, paths):
        copied_calc.append((section_number, calculation_sheet_no, list(paths)))
        return len(paths)

    def fake_copy_invoice(section_number, invoice_no, paths):
        copied_invoice.append((section_number, invoice_no, list(paths)))
        return len(paths)

    monkeypatch.setattr("fatina_paths.copy_files_to_calc_sheet_dir", fake_copy_calc)
    monkeypatch.setattr("fatina_paths.copy_files_to_invoice_dir", fake_copy_invoice)

    entry = SimpleNamespace(
        calculation_sheet_no="20/1",
        drawing_no="05",
        drawing_files=["C:/uploads/a.pdf"],
        submission_breakdown={
            "current_drawing_no": "05",
            "period_details": {
                "05": {"drawing_files": ["C:/uploads/a.pdf"]},
            },
        },
    )

    count = copy_concentration_entry_drawing_files_to_fatina(
        db=None,
        section_number="Section A",
        entries=[entry],
    )

    assert count == 2
    assert copied_calc == [("Section A", "20/1", ["C:/uploads/a.pdf"])]
    assert copied_invoice == [("Section A", "05", ["C:/uploads/a.pdf"])]


def test_copy_drawing_files_to_fatina_calc_only_when_no_invoice(monkeypatch):
    from routers.file_import import copy_concentration_entry_drawing_files_to_fatina

    copied_calc: list[tuple[str, str, list[str]]] = []
    copied_invoice: list[tuple[str, str, list[str]]] = []

    def fake_copy_calc(section_number, calculation_sheet_no, paths):
        copied_calc.append((section_number, calculation_sheet_no, list(paths)))
        return len(paths)

    def fake_copy_invoice(section_number, invoice_no, paths):
        copied_invoice.append((section_number, invoice_no, list(paths)))
        return len(paths)

    monkeypatch.setattr("fatina_paths.copy_files_to_calc_sheet_dir", fake_copy_calc)
    monkeypatch.setattr("fatina_paths.copy_files_to_invoice_dir", fake_copy_invoice)

    entry = SimpleNamespace(
        calculation_sheet_no="20/1",
        drawing_no="",
        drawing_files=["C:/uploads/a.pdf"],
        submission_breakdown=None,
    )

    count = copy_concentration_entry_drawing_files_to_fatina(
        db=None,
        section_number="Section A",
        entries=[entry],
    )

    assert count == 1
    assert copied_calc == [("Section A", "20/1", ["C:/uploads/a.pdf"])]
    assert copied_invoice == []


def test_invoice_numbers_for_calculation_sheet():
    from utils.period_details_utils import invoice_numbers_for_calculation_sheet

    entries = [
        SimpleNamespace(
            calculation_sheet_no="20/1",
            drawing_no="05",
            current_invoice_id=None,
            submission_breakdown={
                "current_drawing_no": "05",
                "periods": {"04": 1.0, "05": 2.0},
            },
        ),
        SimpleNamespace(
            calculation_sheet_no="20/2",
            drawing_no="06",
            current_invoice_id=None,
            submission_breakdown=None,
        ),
        SimpleNamespace(
            calculation_sheet_no="20/1",
            drawing_no="",
            current_invoice_id=None,
            submission_breakdown=None,
        ),
    ]

    assert invoice_numbers_for_calculation_sheet(entries, "20/1") == ["05", "04"]
    assert invoice_numbers_for_calculation_sheet(entries, "20/2") == ["06"]
    assert invoice_numbers_for_calculation_sheet(entries, "20/3") == []
    assert invoice_numbers_for_calculation_sheet([], "20/1") == []


def test_mirror_concentration_sheet_to_fatina_invoice(tmp_path, monkeypatch):
    from fatina_paths import (
        FATINA_INVOICE_BASE_DIR,
        mirror_concentration_sheet_to_fatina_invoice,
    )

    invoice_root = tmp_path / "Fatina Invoice"
    monkeypatch.setattr(
        "fatina_paths.fatina_invoice_root",
        lambda base_dir=None: invoice_root,
    )

    src = tmp_path / "40.01.001.pdf"
    src.write_bytes(b"%PDF-test")

    assert mirror_concentration_sheet_to_fatina_invoice("40.01.001", src)
    dest = invoice_root / "40.01.001" / "40.01.001.pdf"
    assert dest.is_file()
    assert dest.read_bytes() == b"%PDF-test"
    # Default import path constant unchanged (sanity)
    assert FATINA_INVOICE_BASE_DIR.name == "Fatina Invoice"
