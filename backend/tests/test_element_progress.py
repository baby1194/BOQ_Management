from services.element_progress import items_for_element


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
