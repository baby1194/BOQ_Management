from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from database.database import _ensure_site_work_notes_column
from models.models import SiteWorkItem
from routers.site_work import (
    ALLOWED_PDF_TYPES,
    ALLOWED_PHOTO_TYPES,
    SiteWorkUpdate,
    attachment_extension,
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


def test_site_report_accepts_a_pdf_and_whatsapp_still_accepts_a_photo():
    assert attachment_extension("daily-report.pdf", "application/pdf", ALLOWED_PDF_TYPES) == ".pdf"
    assert (
        attachment_extension("daily-report.PDF", "application/octet-stream", ALLOWED_PDF_TYPES)
        == ".pdf"
    )
    assert attachment_extension("photo.jpg", "image/jpeg", ALLOWED_PDF_TYPES) is None
    assert attachment_extension("photo.jpg", "image/jpeg", ALLOWED_PHOTO_TYPES) == ".jpg"
    assert attachment_extension("daily-report.pdf", "application/pdf", ALLOWED_PHOTO_TYPES) is None
