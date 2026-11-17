"""Linked subproject totals are the live BOQ sums, not the parent's old exception snapshot."""

from sqlalchemy.orm import sessionmaker

from database.database import get_project_engine, init_project_database
from models import models
from services.project_rollup import linked_subproject_totals, loose_exception_items


def _boq(section, estimate, submitted, contract=0.0, approved=0.0, est_qty=0.0, sub_qty=0.0):
    return models.BOQItem(
        section_number=section,
        description=section,
        unit="u",
        original_contract_quantity=0,
        price=1,
        total_contract_sum=contract,
        total_estimate=estimate,
        total_submitted=submitted,
        approved_signed_total=approved,
        estimated_quantity=est_qty,
        quantity_submitted=sub_qty,
        internal_total=0,
        approved_signed_quantity=0,
    )


def _fill(project_id, items, sheets=0):
    init_project_database(project_id)
    db = sessionmaker(bind=get_project_engine(project_id))()
    try:
        for item in items:
            db.add(item)
            db.flush()
            db.add(
                models.ConcentrationSheet(
                    boq_item_id=item.id,
                    sheet_name=f"sheet {item.section_number}",
                )
            )
        for index in range(sheets):
            db.add(
                models.CalculationSheet(
                    file_name=f"{index}.xlsx",
                    calculation_sheet_no=str(index + 1),
                    drawing_no=str(index + 1),
                    description="calc",
                )
            )
        db.commit()
    finally:
        db.close()


def test_parent_totals_add_linked_subprojects_and_skip_other_projects(tmp_path, monkeypatch):
    from database import project_registry

    monkeypatch.setattr(project_registry, "DATABASE_DIR", tmp_path)
    monkeypatch.setattr(project_registry, "PROJECTS_DIR", tmp_path / "projects")
    monkeypatch.setattr(project_registry, "REGISTRY_FILE", tmp_path / "projects.json")

    parent = project_registry.create_project_entry("KVISH 40")
    first = project_registry.create_project_entry("Extra A", source_project_id=parent["id"])
    second = project_registry.create_project_entry("Extra B", source_project_id=parent["id"])
    by_move = project_registry.create_project_entry("Extra C")
    unrelated = project_registry.create_project_entry("Other job")

    _fill(parent["id"], [_boq("parent", 175.0, 63.0, contract=221.0)])
    _fill(
        first["id"],
        [_boq("a", 1_086_077.40, 1_086_077.40)],
        sheets=2,
    )
    _fill(
        second["id"],
        [_boq("b", 9_372_734.59, 3_902_428.84, approved=10)],
        sheets=1,
    )
    _fill(by_move["id"], [_boq("c", 14_145_803.04, 14_145_701.57, est_qty=4, sub_qty=3)])
    _fill(unrelated["id"], [_boq("nope", 999_999, 999_999)])

    parent_db = sessionmaker(bind=get_project_engine(parent["id"]))()
    try:
        parent_db.add(models.NonBoqItem(section_number="c", moved_to_project_id=by_move["id"]))
        parent_db.commit()
        totals = linked_subproject_totals(parent_db, parent["id"])
    finally:
        parent_db.close()

    assert set(totals["project_ids"]) == {first["id"], second["id"], by_move["id"]}
    assert totals["boq_count"] == 3
    assert totals["concentration_count"] == 3
    assert totals["items_with_concentration"] == 3
    assert totals["calculation_count"] == 3
    assert totals["total_estimate"] == 1_086_077.40 + 9_372_734.59 + 14_145_803.04
    assert totals["total_submitted"] == 1_086_077.40 + 3_902_428.84 + 14_145_701.57
    assert totals["total_approved"] == 10
    assert totals["total_contract"] == 0
    assert totals["estimated_qty"] == 4
    assert totals["submitted_qty"] == 3


def test_moved_exception_is_not_added_again_on_top_of_its_subproject():
    rolled = {"child"}
    items = [
        {"section_number": "moved", "moved_to_project_id": "child", "removed_at": None, "quantity": 10, "price": 5},
        {"section_number": "still-here", "moved_to_project_id": None, "removed_at": None, "quantity": 2, "price": 3},
        {"section_number": "gone", "moved_to_project_id": None, "removed_at": "2026-01-01", "quantity": 100, "price": 100},
        {"section_number": "missing-project", "moved_to_project_id": "deleted", "removed_at": None, "quantity": 1, "price": 8},
    ]
    kept = [item["section_number"] for item in loose_exception_items(items, rolled)]
    assert kept == ["still-here", "missing-project"]
