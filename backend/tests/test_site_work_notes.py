from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from database.database import _ensure_site_work_notes_column
from models.models import SiteWorkItem
from routers.site_work import (
    ALLOWED_PDF_TYPES,
    ALLOWED_PHOTO_TYPES,
    SiteWorkOpenFile,
    SiteWorkUpdate,
    attachment_extension,
    merge_photo_paths,
    open_site_work_file,
    site_work_disk_path,
    update_site_work,
)


def test_notes_column_is_added_to_an_existing_site_work_table():
    engine = create_engine("sqlite://")
    with engine.connect() as conn:
        conn.execute(
            text(
                "CREATE TABLE site_work_items (id INTEGER PRIMARY KEY, description TEXT)"
            )
        )
        conn.commit()

    _ensure_site_work_notes_column(engine)

    with engine.connect() as conn:
        columns = [row[1] for row in conn.execute(text("PRAGMA table_info(site_work_items)"))]
    assert "notes" in columns


def test_a_note_can_be_saved_without_changing_the_system():
    engine = create_engine("sqlite://")
    SiteWorkItem.__table__.create(engine)
    session = sessionmaker(bind=engine)()
    item = SiteWorkItem(
        description="Pour the ramp",
        dedupe_key="pour-the-ramp",
        system_name="Exception",
        classification="exception",
        source="whatsapp",
        work_date="2026-10-22",
    )
    session.add(item)
    session.commit()

    updated = update_site_work(item.id, SiteWorkUpdate(notes="  Check the north side  "), session)

    assert updated["notes"] == "Check the north side"
    assert updated["system_name"] == "Exception"
    session.refresh(item)
    assert item.notes == "Check the north side"
    session.close()


def test_an_existing_task_keeps_a_newly_attached_pdf():
    merged = merge_photo_paths(
        ["/uploads/proj/site-work/old.pdf"],
        ["/uploads/proj/site-work/old.pdf", "/uploads/proj/site-work/new.pdf"],
    )
    assert merged == [
        "/uploads/proj/site-work/old.pdf",
        "/uploads/proj/site-work/new.pdf",
    ]


def test_open_attachment_launches_the_saved_pdf(tmp_path, monkeypatch):
    engine = create_engine("sqlite://")
    SiteWorkItem.__table__.create(engine)
    session = sessionmaker(bind=engine)()
    project_id = "proj"
    stored = f"/uploads/{project_id}/site-work/report.pdf"
    folder = tmp_path / "uploads" / project_id / "site-work"
    folder.mkdir(parents=True)
    pdf = folder / "report.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    item = SiteWorkItem(
        description="Pour the ramp",
        dedupe_key="pour-the-ramp",
        system_name="Exception",
        classification="exception",
        source="site_report",
        photo_paths=[stored],
    )
    session.add(item)
    session.commit()

    monkeypatch.setattr(
        "routers.site_work.get_project_upload_dir",
        lambda _project_id: tmp_path / "uploads" / _project_id,
    )
    opened = {}
    monkeypatch.setattr(
        "routers.site_work.open_in_default_app",
        lambda path: opened.setdefault("path", path),
    )

    result = open_site_work_file(
        item.id,
        SiteWorkOpenFile(path=stored),
        project_id,
        session,
    )

    assert result == {"success": True}
    assert opened["path"] == str(pdf.resolve())
    assert site_work_disk_path(project_id, stored) == pdf.resolve()
    session.close()


def test_site_report_accepts_a_pdf_and_whatsapp_still_accepts_a_photo():
    assert attachment_extension("daily-report.pdf", "application/pdf", ALLOWED_PDF_TYPES) == ".pdf"
    assert (
        attachment_extension("daily-report.PDF", "application/octet-stream", ALLOWED_PDF_TYPES)
        == ".pdf"
    )
    assert attachment_extension("photo.jpg", "image/jpeg", ALLOWED_PDF_TYPES) is None
    assert attachment_extension("photo.jpg", "image/jpeg", ALLOWED_PHOTO_TYPES) == ".jpg"
    assert attachment_extension("daily-report.pdf", "application/pdf", ALLOWED_PHOTO_TYPES) is None
