"""Prompts for a sub-project when a transferred non-BOQ quantity, price, or sheet changes."""

from sqlalchemy.orm import sessionmaker

from database.database import get_project_engine, init_project_database
from models import models
from services.non_boq_project_copy import fill_non_boq_project
from services.subproject_calc_sync import (
    apply_subproject_calc_updates,
    delete_sheets_from_subprojects,
    diff_transferred_sections,
    find_subproject_sheet_copies,
)


def _session():
    from sqlalchemy import create_engine

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
    for section, quantity, price in entries:
        db.add(
            models.CalculationEntry(
                calculation_sheet_id=sheet.id,
                section_number=section,
                estimated_quantity=quantity,
                quantity_submitted=1.0,
                unit_price=price,
                current_invoice_id="01",
            )
        )
    return sheet


def _row(section, quantity, price):
    return {
        "section_number": section,
        "description": section,
        "unit": "יח'",
        "quantity": quantity,
        "price": price,
        "total": round(quantity * price, 2),
    }


def test_diff_reports_quantity_and_price_only_for_transferred_items(monkeypatch):
    monkeypatch.setattr(
        "services.subproject_calc_sync.project_registry.get_project",
        lambda project_id: {"id": project_id, "name": "Extra A"} if project_id == "child" else None,
    )
    db = _session()
    _sheet(
        db,
        "CS-1",
        [("99.01.0001", 3.0, 40.0), ("01.01.0001", 5.0, 10.0), ("99.01.0002", 2.0, 7.0)],
    )
    db.add(models.NonBoqItem(section_number="99.01.0001", moved_to_project_id="child"))
    db.add(models.NonBoqItem(section_number="99.01.0002", moved_to_project_id="child"))
    db.add(models.NonBoqItem(section_number="99.01.0003", moved_to_project_id="missing"))
    db.commit()

    before = [
        {"section_number": "99.01.0001", "estimated_quantity": 3.0, "quantity_submitted": 1.0, "unit_price": 40.0, "submission_breakdown": None},
        {"section_number": "01.01.0001", "estimated_quantity": 5.0, "quantity_submitted": 1.0, "unit_price": 10.0, "submission_breakdown": None},
        {"section_number": "99.01.0002", "estimated_quantity": 2.0, "quantity_submitted": 1.0, "unit_price": 7.0, "submission_breakdown": None},
    ]
    after = [
        {"section_number": "99.01.0001", "estimated_quantity": 8.0, "quantity_submitted": 1.0, "unit_price": 80.0, "submission_breakdown": None},
        {"section_number": "01.01.0001", "estimated_quantity": 9.0, "quantity_submitted": 4.0, "unit_price": 15.0, "submission_breakdown": None},
        {"section_number": "99.01.0002", "estimated_quantity": 2.0, "quantity_submitted": 1.0, "unit_price": 7.0, "submission_breakdown": None},
        {"section_number": "99.01.0003", "estimated_quantity": 4.0, "quantity_submitted": 0.0, "unit_price": 5.0, "submission_breakdown": None},
    ]

    changes = diff_transferred_sections(db, "CS-1", "CS-1", before, after)
    assert [row["section_number"] for row in changes] == ["99.01.0001"]
    change = changes[0]
    assert change["project_name"] == "Extra A"
    assert change["quantity_changed"] is True
    assert change["price_changed"] is True
    assert change["old_estimated_quantity"] == 3.0
    assert change["new_estimated_quantity"] == 8.0
    assert change["old_price"] == 40.0
    assert change["new_price"] == 80.0


def test_removing_a_section_is_a_quantity_change_and_not_a_price_change(monkeypatch):
    monkeypatch.setattr(
        "services.subproject_calc_sync.project_registry.get_project",
        lambda project_id: {"id": project_id, "name": "Extra A"},
    )
    db = _session()
    db.add(models.NonBoqItem(section_number="99.01.0001", moved_to_project_id="child"))
    db.commit()
    before = [
        {"section_number": "99.01.0001", "estimated_quantity": 3.0, "quantity_submitted": 1.0, "unit_price": 40.0, "submission_breakdown": None},
    ]
    changes = diff_transferred_sections(db, "CS-1", "CS-1", before, [])
    assert len(changes) == 1
    assert changes[0]["quantity_changed"] is True
    assert changes[0]["price_changed"] is False
    assert changes[0]["new_estimated_quantity"] == 0.0


def _use_temp_registry(tmp_path, monkeypatch):
    from database import project_registry

    monkeypatch.setattr(project_registry, "DATABASE_DIR", tmp_path)
    monkeypatch.setattr(project_registry, "PROJECTS_DIR", tmp_path / "projects")
    monkeypatch.setattr(project_registry, "REGISTRY_FILE", tmp_path / "projects.json")


def _open(project_id):
    init_project_database(project_id)
    return sessionmaker(bind=get_project_engine(project_id))()


def test_apply_can_update_quantity_without_changing_price_and_then_the_price(tmp_path, monkeypatch):
    from database import project_registry

    _use_temp_registry(tmp_path, monkeypatch)
    parent = project_registry.create_project_entry("Main")
    child = project_registry.create_project_entry("Extra A", source_project_id=parent["id"])

    source = _open(parent["id"])
    _sheet(source, "CS-1", [("99.01.0001", 3.0, 40.0)])
    source.add(models.NonBoqItem(section_number="99.01.0001", moved_to_project_id=child["id"]))
    source.commit()
    target = _open(child["id"])
    fill_non_boq_project(source, target, [_row("99.01.0001", 3.0, 40.0)])
    target.commit()
    source.close()
    target.close()

    source = _open(parent["id"])
    entry = source.query(models.CalculationEntry).one()
    entry.estimated_quantity = 8.0
    entry.quantity_submitted = 2.0
    entry.unit_price = 80.0
    source.commit()

    choice = {
        "project_id": child["id"],
        "calculation_sheet_no": "CS-1",
        "previous_calculation_sheet_no": "CS-1",
        "section_number": "99.01.0001",
        "update_quantity": True,
        "update_price": False,
    }
    result = apply_subproject_calc_updates(source, [choice])
    assert result["updated"] == 1
    assert result["errors"] == []

    target = _open(child["id"])
    copied = target.query(models.CalculationEntry).one()
    item = target.query(models.BOQItem).one()
    concentration = target.query(models.ConcentrationEntry).one()
    assert copied.estimated_quantity == 8.0
    assert copied.quantity_submitted == 2.0
    assert copied.unit_price == 40.0
    assert item.price == 40.0
    assert item.submitted_price == 40.0
    assert item.estimated_quantity == 8.0
    assert item.total_estimate == 320.0
    assert concentration.estimated_quantity == 8.0
    target.close()

    choice["update_quantity"] = False
    choice["update_price"] = True
    result = apply_subproject_calc_updates(source, [choice])
    assert result["updated"] == 1
    source.close()

    target = _open(child["id"])
    copied = target.query(models.CalculationEntry).one()
    item = target.query(models.BOQItem).one()
    assert copied.estimated_quantity == 8.0
    assert copied.unit_price == 80.0
    assert item.price == 80.0
    assert item.submitted_price == 80.0
    assert item.estimated_quantity == 8.0
    assert item.total_estimate == 640.0
    target.close()


def test_delete_asks_only_about_the_linked_subproject_and_keeps_its_boq_item(tmp_path, monkeypatch):
    from database import project_registry

    _use_temp_registry(tmp_path, monkeypatch)
    parent = project_registry.create_project_entry("Main")
    child = project_registry.create_project_entry("Extra A", source_project_id=parent["id"])
    other = project_registry.create_project_entry("Other job")

    source = _open(parent["id"])
    _sheet(source, "CS-1", [("99.01.0001", 3.0, 40.0)])
    source.add(models.NonBoqItem(section_number="99.01.0001", moved_to_project_id=child["id"]))
    source.commit()

    target = _open(child["id"])
    fill_non_boq_project(source, target, [_row("99.01.0001", 3.0, 40.0)])
    target.commit()
    target.close()

    unrelated = _open(other["id"])
    _sheet(unrelated, "CS-1", [("99.01.0001", 3.0, 40.0)])
    unrelated.commit()
    unrelated.close()

    copies = find_subproject_sheet_copies(source, parent["id"], ["CS-1"])
    assert copies == [
        {
            "project_id": child["id"],
            "project_name": "Extra A",
            "calculation_sheet_no": "CS-1",
        }
    ]

    result = delete_sheets_from_subprojects(source, parent["id"], ["CS-1"])
    assert result["deleted"] == 1
    assert result["errors"] == []
    source.close()

    target = _open(child["id"])
    assert target.query(models.CalculationSheet).count() == 0
    assert target.query(models.ConcentrationEntry).count() == 0
    item = target.query(models.BOQItem).one()
    assert item.section_number == "99.01.0001"
    assert item.estimated_quantity == 0.0
    target.close()

    unrelated = _open(other["id"])
    assert unrelated.query(models.CalculationSheet).count() == 1
    unrelated.close()
