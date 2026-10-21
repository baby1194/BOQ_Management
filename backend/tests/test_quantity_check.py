from openpyxl import Workbook

from services.quantity_check import (
    submitted_by_section_from_workbook,
    submitted_totals_from_rows,
    quantity_mismatches,
)


def test_matching_totals_are_omitted():
    sheets = {"1.02.01.0736": (590.224, 342.224)}
    boq = {"1.02.01.0736": (590.224, 342.224)}
    assert quantity_mismatches(sheets, boq) == []


def test_reports_calculated_and_submitted_gaps():
    sheets = {"1.1": (10.0, 4.0), "1.2": (3.0, 3.0)}
    boq = {"1.1": (8.0, 4.0), "1.2": (3.0, 1.0)}
    rows = quantity_mismatches(sheets, boq)
    by_section = {row["section_number"]: row for row in rows}
    assert by_section["1.1"]["calculated_diff"] == 2.0
    assert by_section["1.1"]["submitted_diff"] == 0.0
    assert by_section["1.2"]["submitted_diff"] == 2.0
    assert by_section["1.1"]["status"] == "שגיאה/חריגה"


def test_difference_under_one_hundredth_is_ok():
    sheets = {"1.1": (10.004, 5.0)}
    boq = {"1.1": (10.0, 5.0)}
    assert quantity_mismatches(sheets, boq) == []


def test_manual_badge_follows_the_boq_item():
    rows = quantity_mismatches(
        {"1.08.10.3296": (10.0, 1.0)},
        {"1.08.10.3296": (8.0, 1.0)},
        manual_sections={"1.08.10.3296"},
    )
    assert rows[0]["has_manual_entries"] is True


def _rows():
    return [None] * 12, [None] * 12, [None] * 12


def test_submitted_total_is_row_24_not_the_detail_lines():
    section_row, submitted_row, invoice_row = _rows()
    section_row[9] = "1.02.01.0610"
    section_row[10] = "1.02.01.0610"
    submitted_row[9] = 77.23
    submitted_row[10] = 10
    invoice_row[9] = "05"
    invoice_row[10] = "06"
    assert submitted_totals_from_rows(section_row, submitted_row, invoice_row) == {
        "1.02.01.0610": 87.23
    }


def test_item_without_invoice_number_is_left_out():
    section_row, submitted_row, invoice_row = _rows()
    section_row[9] = "1.02.01.0610"
    section_row[10] = "1.02.01.0641"
    submitted_row[9] = 77.23
    submitted_row[10] = 10
    invoice_row[9] = "05"
    assert submitted_totals_from_rows(section_row, submitted_row, invoice_row) == {
        "1.02.01.0610": 77.23
    }


def test_single_item_uses_the_sheet_invoice_number():
    section_row, submitted_row, invoice_row = _rows()
    invoice_row[2] = "07"
    section_row[9] = "1.02.01.0610"
    submitted_row[9] = 12.5
    assert submitted_totals_from_rows(section_row, submitted_row, invoice_row) == {
        "1.02.01.0610": 12.5
    }


def test_sheet_invoice_is_not_copied_onto_other_items():
    section_row, submitted_row, invoice_row = _rows()
    invoice_row[2] = "07"
    section_row[9] = "1.1"
    section_row[10] = "1.2"
    submitted_row[9] = 5
    submitted_row[10] = 6
    assert submitted_totals_from_rows(section_row, submitted_row, invoice_row) == {}


def test_workbook_submitted_quantity_reads_excel_row_24(tmp_path):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Calculation"
    worksheet.cell(row=2, column=10, value="05")
    worksheet.cell(row=5, column=10, value="1.02.01.0641")
    worksheet.cell(row=6, column=10, value=411.94)
    worksheet.cell(row=24, column=10, value=217.05)
    worksheet.cell(row=28, column=10, value=999)
    worksheet.cell(row=2, column=11, value="06")
    worksheet.cell(row=5, column=11, value="1.02.01.0671")
    worksheet.cell(row=24, column=11, value=8.5)
    worksheet.cell(row=5, column=12, value="1.02.01.0999")
    worksheet.cell(row=24, column=12, value=50)
    path = tmp_path / "sheet.xlsx"
    workbook.save(path)

    assert submitted_by_section_from_workbook(str(path)) == {
        "1.02.01.0641": 217.05,
        "1.02.01.0671": 8.5,
    }


def test_sheet_item_missing_from_boq_is_a_mismatch():
    rows = quantity_mismatches({"99.1": (12.5, 0.0)}, {})
    assert rows[0]["section_number"] == "99.1"
    assert rows[0]["system_calculated"] == 0.0
    assert rows[0]["calculated_diff"] == 12.5
    assert rows[0]["is_non_boq"] is True
