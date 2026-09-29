import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import models
from services.non_boq_service import (
    build_non_boq_import_rows,
    mark_non_boq_items_moved,
    select_import_rows,
)
from utils.calculation_sheet_utils import read_non_boq_price


def _session():
    engine = create_engine("sqlite://")
    models.Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_new_project_remembers_the_main_project(tmp_path, monkeypatch):
    from database import project_registry

    monkeypatch.setattr(project_registry, "DATABASE_DIR", tmp_path)
    monkeypatch.setattr(project_registry, "REGISTRY_FILE", tmp_path / "projects.json")
    linked = project_registry.create_project_entry("Extras", source_project_id="main-1")
    plain = project_registry.create_project_entry("Plain")
    saved = {p["id"]: p for p in project_registry.list_projects()}
    assert saved[linked["id"]]["source_project_id"] == "main-1"
    assert "source_project_id" not in saved[plain["id"]]


def test_select_import_rows_keeps_all_when_nothing_chosen():
    rows = [{"section_number": "A"}, {"section_number": "B"}]
    assert select_import_rows(rows, None) == rows
    assert select_import_rows(rows, [" B "]) == [{"section_number": "B"}]
    assert select_import_rows(rows, []) == []


def test_moved_items_record_the_target_project():
    db = _session()
    db.add_all([models.NonBoqItem(section_number="A"), models.NonBoqItem(section_number="B")])
    db.commit()
    assert mark_non_boq_items_moved(db, ["A"], "project-2") == 1
    db.commit()
    moved = {item.section_number: item.moved_to_project_id for item in db.query(models.NonBoqItem)}
    assert moved == {"A": "project-2", "B": None}


def test_price_is_read_from_excel_row_7():
    df = pd.DataFrame([[None] * 6 for _ in range(8)])
    df.iloc[6, 4] = 1213
    assert read_non_boq_price(df, 4) == 1213


def test_import_rows_sum_quantity_and_keep_the_first_price():
    rows = build_non_boq_import_rows(
        [
            {
                "section_number": "99.02.01.0640",
                "description": "Extra wall",
                "estimated_quantity": 10,
                "unit_price": 50,
            },
            {
                "section_number": "99.02.01.0640",
                "description": "",
                "estimated_quantity": 2.5,
                "unit_price": 80,
            },
            {
                "section_number": "99.05.031.0012",
                "description": "",
                "estimated_quantity": 4,
                "unit_price": None,
            },
        ]
    )
    by_section = {row["section_number"]: row for row in rows}
    assert by_section["99.02.01.0640"]["quantity"] == 12.5
    assert by_section["99.02.01.0640"]["price"] == 50
    assert by_section["99.02.01.0640"]["total"] == 625
    assert by_section["99.05.031.0012"]["description"] == "99.05.031.0012"
    assert by_section["99.05.031.0012"]["missing_price"] is True
