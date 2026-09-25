from services.quantity_check import quantity_mismatches


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


def test_sheet_item_missing_from_boq_is_a_mismatch():
    rows = quantity_mismatches({"99.1": (12.5, 0.0)}, {})
    assert rows[0]["section_number"] == "99.1"
    assert rows[0]["system_calculated"] == 0.0
    assert rows[0]["calculated_diff"] == 12.5
