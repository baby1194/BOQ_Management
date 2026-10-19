from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import models
from services.non_boq_project_copy import (
    add_non_boq_items_to_project,
    fill_non_boq_project,
)


def _session():
    engine = create_engine("sqlite://")
    models.Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _sheet(db, number, entries):
    sheet = models.CalculationSheet(
        file_name=f"{number}.xlsx",
        calculation_sheet_no=number,
        drawing_no="D1",
        description=f"Sheet {number}",
        source_file_path=f"C:/sheets/{number}.xlsx",
    )
    db.add(sheet)
    db.flush()
    for section, quantity in entries:
        db.add(
            models.CalculationEntry(
                calculation_sheet_id=sheet.id,
                section_number=section,
                estimated_quantity=quantity,
                unit_price=40.0,
            )
        )


def test_new_project_gets_only_non_boq_rows_of_mixed_sheets():
    source = _session()
    _sheet(source, "CS-1", [("01.01.0001", 5.0), ("99.01.0001", 3.0)])
    _sheet(source, "CS-2", [("01.01.0001", 7.0)])
    source.commit()

    target = _session()
    rows = [
        {
            "section_number": "99.01.0001",
            "description": "Extra",
            "unit": "יח'",
            "quantity": 3.0,
            "price": 40.0,
            "total": 120.0,
        }
    ]
    result = fill_non_boq_project(source, target, rows)
    target.commit()

    assert result == {"item_count": 1, "calculation_sheet_count": 1}
    sheets = target.query(models.CalculationSheet).all()
    assert [s.calculation_sheet_no for s in sheets] == ["CS-1"]
    assert sheets[0].source_file_path == "C:/sheets/CS-1.xlsx"
    assert [e.section_number for e in sheets[0].entries] == ["99.01.0001"]

    concentration = target.query(models.ConcentrationEntry).all()
    assert len(concentration) == 1
    assert concentration[0].calculation_sheet_no == "CS-1"
    assert concentration[0].estimated_quantity == 3.0


def _row(section, description, quantity, price):
    return {
        "section_number": section,
        "description": description,
        "unit": "יח'",
        "quantity": quantity,
        "price": price,
        "total": round(quantity * price, 2),
    }


def test_add_to_existing_project_appends_items_and_merges_sheets():
    source = _session()
    _sheet(source, "CS-1", [("99.01.0001", 3.0), ("99.01.0002", 4.0)])
    _sheet(source, "CS-2", [("99.01.0002", 1.5)])
    source.commit()

    target = _session()
    fill_non_boq_project(source, target, [_row("99.01.0001", "First", 3.0, 40.0)])
    target.commit()

    result = add_non_boq_items_to_project(
        source,
        target,
        [
            _row("99.01.0001", "Should stay the first text", 9.0, 1.0),
            _row("99.01.0002", "Second", 5.5, 10.0),
        ],
    )
    target.commit()

    assert result["item_count"] == 1
    assert result["skipped_count"] == 1
    assert result["added_sections"] == ["99.01.0002"]
    assert result["calculation_sheet_count"] == 2

    items = (
        target.query(models.BOQItem)
        .order_by(models.BOQItem.display_order.asc())
        .all()
    )
    assert [item.section_number for item in items] == ["99.01.0001", "99.01.0002"]
    assert items[0].description == "First"
    assert items[0].price == 40.0
    assert items[1].description == "Second"
    assert items[1].serial_number == 2

    sheets = {
        sheet.calculation_sheet_no: sheet
        for sheet in target.query(models.CalculationSheet).all()
    }
    assert set(sheets) == {"CS-1", "CS-2"}
    assert sorted(entry.section_number for entry in sheets["CS-1"].entries) == [
        "99.01.0001",
        "99.01.0002",
    ]
    assert [entry.section_number for entry in sheets["CS-2"].entries] == ["99.01.0002"]

    first_concentration = (
        target.query(models.ConcentrationSheet)
        .filter(models.ConcentrationSheet.boq_item_id == items[0].id)
        .one()
    )
    first_entries = (
        target.query(models.ConcentrationEntry)
        .filter(models.ConcentrationEntry.concentration_sheet_id == first_concentration.id)
        .all()
    )
    assert [entry.section_number for entry in first_entries] == ["99.01.0001"]

    second_concentration = (
        target.query(models.ConcentrationSheet)
        .filter(models.ConcentrationSheet.boq_item_id == items[1].id)
        .one()
    )
    second_entries = (
        target.query(models.ConcentrationEntry)
        .filter(models.ConcentrationEntry.concentration_sheet_id == second_concentration.id)
        .all()
    )
    assert sorted(entry.calculation_sheet_no for entry in second_entries) == ["CS-1", "CS-2"]


def test_add_to_existing_project_skips_when_every_item_is_already_there():
    source = _session()
    _sheet(source, "CS-1", [("99.01.0001", 3.0)])
    source.commit()

    target = _session()
    fill_non_boq_project(source, target, [_row("99.01.0001", "First", 3.0, 40.0)])
    target.commit()

    result = add_non_boq_items_to_project(
        source, target, [_row("99.01.0001", "Other", 8.0, 5.0)]
    )
    target.commit()

    assert result["item_count"] == 0
    assert result["skipped_count"] == 1
    items = target.query(models.BOQItem).all()
    assert len(items) == 1
    assert items[0].description == "First"
    assert target.query(models.CalculationSheet).count() == 1
