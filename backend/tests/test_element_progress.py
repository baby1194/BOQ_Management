from openpyxl import load_workbook
from io import BytesIO

from services.element_progress import (
    element_names_from_entries,
    items_for_element,
    mentions,
    rows_for_words,
    split_search_words,
    word_items_workbook,
)

CLIENT_ENTRIES = {
    "1.02.01.0736": [
        {
            "description": "DC-36",
            "invoice_description": "יציקת תקרה DC-36 קומה 1",
            "calculation_sheet_no": "17",
            "estimated_quantity": 12.5,
            "quantity_submitted": 12.5,
        },
        {
            "description": "DC-02",
            "invoice_description": "יציקת תקרה DC - 02",
            "calculation_sheet_no": "21",
            "estimated_quantity": 8,
            "quantity_submitted": 0,
        },
    ]
}


def test_element_names_come_from_description_and_work_description():
    entries = [entry for rows in CLIENT_ENTRIES.values() for entry in rows]
    entries.append({"description": "1.02.01.0736", "invoice_description": "invoice 05"})
    assert element_names_from_entries(entries) == ["DC-02", "DC-36"]


def test_codes_match_whole_names_only():
    assert mentions("wall DC-36 north", "DC-36")
    assert mentions("wall dc - 36", "DC-36")
    assert not mentions("wall DC-360", "DC-36")
    assert not mentions("wall DC-36", "DC-3")


def test_element_quantities_come_from_its_own_rows():
    boq = [
        {
            "section_number": "1.02.01.0736",
            "description": "Concrete slab",
            "contract_quantity": 30,
            "quantity_submitted": 12.5,
        }
    ]
    dc36 = items_for_element("DC-36", boq, CLIENT_ENTRIES)
    assert dc36[0]["quantity_submitted"] == 12.5
    assert dc36[0]["submitted"] is True
    assert dc36[0]["calculation_sheet_nos"] == ["17"]
    dc02 = items_for_element("DC-02", boq, CLIENT_ENTRIES)
    assert dc02[0]["estimated_quantity"] == 8
    assert dc02[0]["submitted"] is False


def test_splits_submitted_and_not_submitted_for_one_element():
    boq = [
        {
            "section_number": "1.1",
            "description": "Concrete wall DC-36",
            "contract_quantity": 10,
            "quantity_submitted": 4,
        },
        {
            "section_number": "1.2",
            "description": "Formwork for DC-36",
            "contract_quantity": 8,
            "quantity_submitted": 0,
        },
        {
            "section_number": "2.1",
            "description": "Drainage channel",
            "contract_quantity": 3,
            "quantity_submitted": 3,
        },
    ]
    rows = items_for_element("DC-36", boq, {})
    assert [row["section_number"] for row in rows] == ["1.1", "1.2"]
    assert rows[0]["submitted"] is True
    assert rows[1]["submitted"] is False


def test_typed_words_list_the_section_numbers_connected_to_each_word():
    assert split_search_words(" RW-18 / DC-50 / rails / RW-18 ") == ["RW-18", "DC-50", "rails"]
    boq = [
        {"section_number": "1.02.01.0010", "description": "Concrete for RW-18", "contract_quantity": 1},
        {"section_number": "1.02.01.0041", "description": "Formwork", "contract_quantity": 1},
        {"section_number": "9.1", "description": "Steel rails along the road", "contract_quantity": 1},
    ]
    entries = {
        "1.02.01.0041": [{"description": "DC-50 wall", "invoice_description": ""}],
    }
    rows = rows_for_words("RW-18 / DC-50 / rails / missing", boq, entries)
    by_word = {}
    for row in rows:
        by_word.setdefault(row["word"], []).append(row["section_number"])
    assert by_word["RW-18"] == ["1.02.01.0010"]
    assert by_word["DC-50"] == ["1.02.01.0041"]
    assert by_word["rails"] == ["9.1"]
    assert by_word["missing"] == [""]

    book = load_workbook(BytesIO(word_items_workbook(rows, "en")))
    sheet = book.active
    assert [cell.value for cell in sheet[1]] == ["Word", "Section number", "Description"]
    assert sheet["A2"].value == "RW-18"
    assert sheet["B2"].value == "1.02.01.0010"


def test_links_an_item_through_a_drawing_name_on_the_entry():
    boq = [
        {
            "section_number": "3.1",
            "description": "Cast in place",
            "contract_quantity": 5,
            "quantity_submitted": 1,
        }
    ]
    entries = {"3.1": [{"description": "see plan W-12", "invoice_description": "", "drawing_no": "07"}]}
    rows = items_for_element("Wall 4", boq, entries, drawing_names=["W-12"])
    assert rows[0]["section_number"] == "3.1"
