"""Unit tests for BOQ cross-project transfer helpers."""

from types import SimpleNamespace

from services.boq_transfer_service import (
    _normalize_drawing_files,
    rewrite_breakdown_drawing_files,
)


def test_normalize_drawing_files_filters_empty():
    assert _normalize_drawing_files(None) == []
    assert _normalize_drawing_files(["a.pdf", "", None, "b.pdf"]) == [
        "a.pdf",
        "b.pdf",
    ]


def test_rewrite_breakdown_drawing_files_copies_period_paths(tmp_path):
    src = tmp_path / "source.pdf"
    src.write_text("drawing")
    breakdown = {
        "periods": {"INV-1": 10},
        "period_details": {
            "INV-1": {
                "drawing_files": [str(src)],
                "notes": "ok",
            }
        },
    }
    target_upload = tmp_path / "uploads"
    rewritten = rewrite_breakdown_drawing_files(breakdown, target_upload, 99)
    files = rewritten["period_details"]["INV-1"]["drawing_files"]
    assert len(files) == 1
    assert files[0].endswith("source.pdf")
    assert (target_upload / "drawing-files" / "99" / "source.pdf").is_file()
    # original breakdown unchanged
    assert breakdown["period_details"]["INV-1"]["drawing_files"] == [str(src)]


def test_classify_transfer_items_skips_conflicts():
    from services.boq_transfer_service import classify_transfer_items

    source_items = [
        SimpleNamespace(id=1, section_number="01.01", description="A"),
        SimpleNamespace(id=2, section_number="01.02", description="B"),
    ]

    class FakeQuery:
        def __init__(self, rows):
            self.rows = rows

        def filter(self, *_args, **_kwargs):
            return self

        def all(self):
            return self.rows

    class SourceDb:
        def query(self, model):
            # BOQItem query returns full items
            return FakeQuery(source_items)

    class TargetDb:
        def query(self, model):
            # section_number query returns existing conflict for 01.01
            return FakeQuery([("01.01",)])

    to_copy, conflicts, missing = classify_transfer_items(
        SourceDb(), TargetDb(), [1, 2, 99]
    )
    assert [item.section_number for item in to_copy] == ["01.02"]
    assert len(conflicts) == 1
    assert conflicts[0]["section_number"] == "01.01"
    assert missing == [99]


def test_copy_boq_items_copies_concentration_sheet_and_keeps_auto_entries(tmp_path):
    """Transferred auto entries must survive orphan purge (marked manual)."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from database.database import Base
    from models import models
    from services.boq_transfer_service import copy_boq_items_to_project
    from utils.concentration_utils import remove_orphan_concentration_entries

    def make_session(db_file):
        engine = create_engine(
            f"sqlite:///{db_file.as_posix()}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=engine)
        return sessionmaker(autocommit=False, autoflush=False, bind=engine)()

    source_db = make_session(tmp_path / "source.db")
    target_db = make_session(tmp_path / "target.db")

    source_item = models.BOQItem(
        display_order=0,
        serial_number=1,
        section_number="10.20.30",
        description="Exceptional item",
        unit="m",
        original_contract_quantity=5.0,
        price=100.0,
        total_contract_sum=500.0,
        estimated_quantity=5.0,
        quantity_submitted=5.0,
        approved_by_project_manager=5.0,
    )
    source_db.add(source_item)
    source_db.flush()

    source_sheet = models.ConcentrationSheet(
        boq_item_id=source_item.id,
        sheet_name="Concentration Sheet - 10.20.30",
        total_submitted=5.0,
        total_approved=5.0,
    )
    source_db.add(source_sheet)
    source_db.flush()

    source_db.add(
        models.ConcentrationEntry(
            concentration_sheet_id=source_sheet.id,
            section_number="10.20.30",
            description="from calc",
            calculation_sheet_no="CS-MISSING-IN-TARGET",
            estimated_quantity=5.0,
            quantity_submitted=5.0,
            approved_by_project_manager=5.0,
            is_manual=False,
        )
    )
    source_db.commit()

    result = copy_boq_items_to_project(
        source_db=source_db,
        target_db=target_db,
        boq_item_ids=[source_item.id],
        target_upload_dir=tmp_path / "uploads",
    )
    assert result["transferred_count"] == 1

    target_boq = (
        target_db.query(models.BOQItem)
        .filter(models.BOQItem.section_number == "10.20.30")
        .one()
    )
    target_sheet = (
        target_db.query(models.ConcentrationSheet)
        .filter(models.ConcentrationSheet.boq_item_id == target_boq.id)
        .one()
    )
    target_entries = (
        target_db.query(models.ConcentrationEntry)
        .filter(models.ConcentrationEntry.concentration_sheet_id == target_sheet.id)
        .all()
    )
    assert len(target_entries) == 1
    assert target_entries[0].is_manual is True
    assert target_entries[0].calculation_sheet_no == "CS-MISSING-IN-TARGET"
    assert target_entries[0].quantity_submitted == 5.0

    removed, _ = remove_orphan_concentration_entries(target_db)
    assert removed == 0
    assert (
        target_db.query(models.ConcentrationEntry)
        .filter(models.ConcentrationEntry.concentration_sheet_id == target_sheet.id)
        .count()
        == 1
    )
