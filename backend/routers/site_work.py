import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.database import get_db, get_project_id, get_project_upload_dir
from models import models
from services.site_work_parser import (
    EXCEPTION_SYSTEM,
    classification_after_system_change,
    manual_task,
    parse_work_lines,
)

router = APIRouter()

ALLOWED_PHOTO_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}

ALLOWED_PDF_TYPES = {
    "application/pdf": ".pdf",
    "application/x-pdf": ".pdf",
}


def attachment_extension(filename: str, content_type: str, allowed: dict) -> Optional[str]:
    """Return a safe suffix for an upload, or None when the type is not allowed."""
    normalized = (content_type or "").split(";")[0].strip().lower()
    ext = allowed.get(normalized)
    if ext:
        return ext
    name = (filename or "").lower()
    for candidate in set(allowed.values()):
        if name.endswith(candidate):
            return candidate
    return None


def _known_systems(db: Session) -> List[str]:
    rows = db.query(models.BOQItem.system).distinct().all()
    names = []
    for (value,) in rows:
        if value is None:
            continue
        text = str(value).strip()
        if text and text not in names:
            names.append(text)
    return names


def _to_dict(item: models.SiteWorkItem) -> dict:
    return {
        "id": item.id,
        "description": item.description,
        "system_name": item.system_name,
        "classification": item.classification,
        "source": item.source,
        "work_date": item.work_date,
        "notes": item.notes,
        "photo_paths": item.photo_paths or [],
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


async def _save_attachments(
    project_id: str, uploads: List[UploadFile], allowed: dict
) -> List[str]:
    if not uploads:
        return []
    folder = Path(get_project_upload_dir(project_id)) / "site-work"
    folder.mkdir(parents=True, exist_ok=True)
    saved: List[str] = []
    for upload in uploads:
        if not upload or not upload.filename:
            continue
        ext = attachment_extension(upload.filename, upload.content_type or "", allowed)
        if ext is None:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {upload.filename}",
            )
        name = f"{uuid.uuid4().hex}{ext}"
        target = folder / name
        data = await upload.read()
        target.write_bytes(data)
        saved.append(f"/uploads/{project_id}/site-work/{name}")
    return saved


class SiteWorkUpdate(BaseModel):
    system_name: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = Field(None, max_length=5000)


class SiteWorkCreate(BaseModel):
    description: str
    system_name: str = EXCEPTION_SYSTEM
    classification: str = "exception"
    source: str = "site_report"
    work_date: Optional[str] = None


@router.post("/")
def create_site_work(payload: SiteWorkCreate, db: Session = Depends(get_db)):
    try:
        row = manual_task(
            payload.description,
            payload.system_name,
            payload.classification,
            payload.source,
            payload.work_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    existing = (
        db.query(models.SiteWorkItem)
        .filter(models.SiteWorkItem.dedupe_key == row["dedupe_key"])
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="This task is already listed")
    item = models.SiteWorkItem(
        description=row["description"],
        dedupe_key=row["dedupe_key"],
        system_name=row["system_name"],
        classification=row["classification"],
        source=row["source"],
        work_date=row["work_date"],
        photo_paths=[],
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_dict(item)


@router.get("/systems")
def list_site_work_systems(db: Session = Depends(get_db)):
    names = _known_systems(db)
    if EXCEPTION_SYSTEM not in names:
        names = [EXCEPTION_SYSTEM, *names]
    return names


@router.get("/")
def list_site_work(db: Session = Depends(get_db)):
    items = (
        db.query(models.SiteWorkItem)
        .order_by(models.SiteWorkItem.id.desc())
        .all()
    )
    return [_to_dict(item) for item in items]


@router.post("/ingest")
async def ingest_site_work(
    source: str = Form(...),
    text: str = Form(""),
    work_date: Optional[str] = Form(None),
    photos: List[UploadFile] = File(default=[]),
    project_id: str = Depends(get_project_id),
    db: Session = Depends(get_db),
):
    if source not in ("site_report", "whatsapp"):
        raise HTTPException(status_code=400, detail="Source must be site_report or whatsapp")
    parsed = parse_work_lines(text, _known_systems(db))
    allowed = ALLOWED_PHOTO_TYPES if source == "whatsapp" else ALLOWED_PDF_TYPES
    photo_paths = await _save_attachments(project_id, photos, allowed)

    created = []
    skipped = 0
    for row in parsed:
        existing = (
            db.query(models.SiteWorkItem)
            .filter(models.SiteWorkItem.dedupe_key == row["dedupe_key"])
            .first()
        )
        if existing:
            skipped += 1
            continue
        item = models.SiteWorkItem(
            description=row["description"],
            dedupe_key=row["dedupe_key"],
            system_name=row["system_name"],
            classification=row["classification"],
            source=source,
            work_date=(work_date or "").strip() or None,
            photo_paths=photo_paths,
        )
        db.add(item)
        db.flush()
        created.append(_to_dict(item))
    db.commit()
    return {
        "created": created,
        "created_count": len(created),
        "skipped_duplicates": skipped,
        "ignored_lines": max(0, len([ln for ln in text.splitlines() if ln.strip()]) - len(parsed) - skipped),
    }


@router.patch("/{item_id}")
def update_site_work(
    item_id: int,
    payload: SiteWorkUpdate,
    db: Session = Depends(get_db),
):
    if payload.system_name is None and payload.notes is None:
        raise HTTPException(status_code=400, detail="Nothing to update")
    item = db.query(models.SiteWorkItem).filter(models.SiteWorkItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Site work item not found")
    if payload.system_name is not None:
        system_name = payload.system_name.strip()
        if not system_name:
            raise HTTPException(status_code=400, detail="System is required")
        item.system_name = system_name
        item.classification = classification_after_system_change(
            item.classification, system_name
        )
    if payload.notes is not None:
        item.notes = payload.notes.strip() or None
    db.commit()
    db.refresh(item)
    return _to_dict(item)


@router.delete("/{item_id}")
def delete_site_work(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.SiteWorkItem).filter(models.SiteWorkItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Site work item not found")
    db.delete(item)
    db.commit()
    return {"success": True}
