from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import models
from services import non_boq_service
from services.non_boq_service import (
    delete_section_from_database,
    reconcile_missing_non_boq_items,
)


def _session():
    engine = create_engine("sqlite://")
    models.Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _sheet(db, number):
    sheet = models.CalculationSheet(
        file_name=f"{number}.xlsx",
        calculation_sheet_no=number,
        drawing_no="D1",
        description=number,
    )
    db.add(sheet)
    db.flush()
    return sheet


def test_removed_section_is_marked_and_deleted_from_the_sub_project(monkeypatch):
    source = _session()
    target = _session()
    sheet = _sheet(source, "32/7/1")
    source.add(
        models.CalculationEntry(
            calculation_sheet_id=sheet.id,
            section_number="99.41.01.1340",
            estimated_quantity=1.0,
        )
    )
    source.add(
        models.NonBoqItem(
            section_number="99.41.01.1340",
            moved_to_project_id="proj",
            source_sheet_nos="32/7/1",
        )
    )
    item = models.BOQItem(
        display_order=0,
        section_number="99.41.01.1340",
        description="Cancelled",
        unit="m",
        original_contract_quantity=1,
        price=2,
        total_contract_sum=2,
    )
    target.add(item)
    target.flush()
    target.add(
        models.ConcentrationSheet(boq_item_id=item.id, sheet_name="Concentration")
    )
    target.add(
        models.CalculationEntry(
            calculation_sheet_id=_sheet(target, "32/7/1").id,
            section_number="99.41.01.1340",
        )
    )
    source.commit()
    target.commit()

    source.query(models.CalculationEntry).delete()
    source.commit()

    monkeypatch.setattr(
        non_boq_service.project_registry,
        "list_projects",
        lambda: [{"id": "proj", "name": "Extras"}],
    )
    monkeypatch.setattr(
        non_boq_service.project_registry,
        "get_project",
        lambda project_id: {"id": project_id, "name": "Extras"},
    )

    def fake_delete(project_id, section_number):
        assert project_id == "proj"
        delete_section_from_database(target, section_number)
        target.commit()
        return True

    monkeypatch.setattr(non_boq_service, "delete_section_from_linked_project", fake_delete)

    notices, changed = reconcile_missing_non_boq_items(source)
    source.commit()

    assert changed is True
    row = source.query(models.NonBoqItem).one()
    assert row.removed_at is not None
    assert row.removed_from_project is True
    assert row.source_sheet_nos == "32/7/1"
    assert "99.41.01.1340" in notices[0]
    assert "Extras" in notices[0]
    assert target.query(models.BOQItem).count() == 0
    assert target.query(models.ConcentrationSheet).count() == 0
    assert target.query(models.CalculationEntry).count() == 0
    assert target.query(models.CalculationSheet).count() == 0


def test_section_still_on_a_sheet_keeps_the_sheet_number(monkeypatch):
    source = _session()
    sheet = _sheet(source, "26/1")
    source.add(
        models.CalculationEntry(
            calculation_sheet_id=sheet.id,
            section_number="99.18.02.1180",
        )
    )
    source.add(models.NonBoqItem(section_number="99.18.02.1180"))
    source.commit()

    monkeypatch.setattr(non_boq_service.project_registry, "list_projects", lambda: [])
    notices, changed = reconcile_missing_non_boq_items(source)

    row = source.query(models.NonBoqItem).one()
    assert notices == []
    assert changed is True
    assert row.removed_at is None
    assert row.source_sheet_nos == "26/1"
