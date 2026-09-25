import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from database.database import get_db, get_project_id, get_project_upload_dir
from models import models
from services.site_work_parser import parse_work_lines

router = APIRouter()

ALLOWED_PHOTO_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


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
        "photo_paths": item.photo_paths or [],
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


async def _save_photos(project_id: str, photos: List[UploadFile]) -> List[str]:
    if not photos:
        return []
    folder = Path(get_project_upload_dir(project_id)) / "site-work"
    folder.mkdir(parents=True, exist_ok=True)
    saved: List[str] = []
    for photo in photos:
        if not photo or not photo.filename:
            continue
        content_type = (photo.content_type or "").lower()
        ext = ALLOWED_PHOTO_TYPES.get(content_type)
        if ext is None:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported photo type: {photo.filename}",
            )
        name = f"{uuid.uuid4().hex}{ext}"
        target = folder / name
        data = await photo.read()
        target.write_bytes(data)
        saved.append(f"/uploads/{project_id}/site-work/{name}")
    return saved


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
    photo_paths = await _save_photos(project_id, photos) if source == "whatsapp" else []

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


@router.delete("/{item_id}")
def delete_site_work(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.SiteWorkItem).filter(models.SiteWorkItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Site work item not found")
    db.delete(item)
    db.commit()
    return {"success": True}
