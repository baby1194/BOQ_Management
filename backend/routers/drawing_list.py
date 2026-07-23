from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
import os
import platform
import subprocess

from database.database import get_db
from models import models
from schemas import schemas

router = APIRouter()
logger = logging.getLogger(__name__)

VALID_EXECUTION_STATUSES = {None, "", "to_be_executed", "cancelled"}


def _clean_str(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_execution_status(value: Optional[str]) -> Optional[str]:
    cleaned = _clean_str(value)
    if cleaned not in VALID_EXECUTION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='execution_status must be "to_be_executed", "cancelled", or empty',
        )
    return cleaned


def _to_response(row: models.DrawingListItem) -> schemas.DrawingListItem:
    return schemas.DrawingListItem(
        id=row.id,
        no=row.display_order,
        drawing_type=row.drawing_type,
        planning_office=row.planning_office,
        drawing_name=row.drawing_name,
        cross_sections=row.cross_sections,
        element=row.element,
        sheet_name=row.sheet_name,
        edition=row.edition,
        release_date=row.release_date,
        update_description=row.update_description,
        folder_date=row.folder_date,
        file_path=row.file_path,
        notes=row.notes,
        execution_status=row.execution_status,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _ordered_rows(db: Session) -> List[models.DrawingListItem]:
    return (
        db.query(models.DrawingListItem)
        .order_by(
            models.DrawingListItem.display_order.asc(),
            models.DrawingListItem.id.asc(),
        )
        .all()
    )


def _renumber(rows: List[models.DrawingListItem]) -> None:
    for index, row in enumerate(rows, start=1):
        row.display_order = index


def _insert_at(
    rows: List[models.DrawingListItem],
    item: models.DrawingListItem,
    target_no: Optional[int],
) -> None:
    """Place item at 1-based target_no; append if missing/invalid/too large."""
    count = len(rows)
    if target_no is None or target_no < 1 or target_no > count + 1:
        rows.append(item)
    else:
        rows.insert(target_no - 1, item)
    _renumber(rows)


def _apply_fields(db_item: models.DrawingListItem, data: dict) -> None:
    field_map = {
        "drawing_type": _clean_str,
        "planning_office": _clean_str,
        "drawing_name": _clean_str,
        "cross_sections": _clean_str,
        "element": _clean_str,
        "sheet_name": _clean_str,
        "edition": _clean_str,
        "release_date": _clean_str,
        "update_description": _clean_str,
        "folder_date": _clean_str,
        "file_path": _clean_str,
        "notes": _clean_str,
    }
    for key, cleaner in field_map.items():
        if key in data:
            setattr(db_item, key, cleaner(data[key]))
    if "execution_status" in data:
        db_item.execution_status = _normalize_execution_status(data["execution_status"])


@router.get("/", response_model=List[schemas.DrawingListItem])
async def list_drawings(db: Session = Depends(get_db)):
    try:
        return [_to_response(row) for row in _ordered_rows(db)]
    except Exception as e:
        logger.error("Error listing drawings: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post(
    "/",
    response_model=schemas.DrawingListItem,
    status_code=status.HTTP_201_CREATED,
)
async def create_drawing(
    body: schemas.DrawingListItemCreate,
    db: Session = Depends(get_db),
):
    try:
        data = body.model_dump(exclude={"no"})
        db_item = models.DrawingListItem(display_order=1)
        _apply_fields(db_item, data)

        rows = _ordered_rows(db)
        _insert_at(rows, db_item, body.no)
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return _to_response(db_item)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Error creating drawing: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.put("/{item_id}", response_model=schemas.DrawingListItem)
async def update_drawing(
    item_id: int,
    body: schemas.DrawingListItemUpdate,
    db: Session = Depends(get_db),
):
    try:
        db_item = (
            db.query(models.DrawingListItem)
            .filter(models.DrawingListItem.id == item_id)
            .first()
        )
        if not db_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Drawing not found",
            )

        data = body.model_dump(exclude_unset=True, exclude={"no"})
        _apply_fields(db_item, data)

        if body.no is not None and body.no != db_item.display_order:
            rows = [r for r in _ordered_rows(db) if r.id != item_id]
            _insert_at(rows, db_item, body.no)

        db.commit()
        db.refresh(db_item)
        return _to_response(db_item)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Error updating drawing %s: %s", item_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_drawing(item_id: int, db: Session = Depends(get_db)):
    try:
        db_item = (
            db.query(models.DrawingListItem)
            .filter(models.DrawingListItem.id == item_id)
            .first()
        )
        if not db_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Drawing not found",
            )
        db.delete(db_item)
        db.flush()
        _renumber(_ordered_rows(db))
        db.commit()
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Error deleting drawing %s: %s", item_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/{item_id}/open")
async def open_drawing_file(item_id: int, db: Session = Depends(get_db)):
    db_item = (
        db.query(models.DrawingListItem)
        .filter(models.DrawingListItem.id == item_id)
        .first()
    )
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drawing not found",
        )
    file_path = db_item.file_path
    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file path set for this drawing",
        )
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {file_path}",
        )

    try:
        if platform.system() == "Windows":
            os.startfile(file_path)
        elif platform.system() == "Darwin":
            subprocess.call(["open", file_path])
        else:
            subprocess.call(["xdg-open", file_path])
        return {"success": True, "message": f"Opening file: {file_path}"}
    except Exception as exc:
        logger.error("Error opening drawing file: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error opening file: {exc}",
        )
