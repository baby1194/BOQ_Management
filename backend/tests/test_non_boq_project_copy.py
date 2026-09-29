from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import models
from services.non_boq_project_copy import fill_non_boq_project


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
