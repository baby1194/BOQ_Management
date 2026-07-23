from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging
import os
import platform
import subprocess

from database.database import get_db
from models import models
from schemas import schemas

router = APIRouter()
logger = logging.getLogger(__name__)


def _file_name_from_path(file_path: str) -> str:
    return os.path.basename(file_path.replace("\\", "/").rstrip("/")) or file_path


def _to_response(row: models.ProjectInfoFile) -> schemas.ProjectInfoFile:
    return schemas.ProjectInfoFile(
        id=row.id,
        no=row.display_order,
        category_en=row.category_en,
        category_he=row.category_he,
        file_name=_file_name_from_path(row.file_path),
        file_path=row.file_path,
        description=row.description,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _renumber(db: Session) -> None:
    rows = (
        db.query(models.ProjectInfoFile)
        .order_by(
            models.ProjectInfoFile.display_order.asc(),
            models.ProjectInfoFile.id.asc(),
        )
        .all()
    )
    for index, row in enumerate(rows, start=1):
        row.display_order = index


@router.get("/", response_model=List[schemas.ProjectInfoFile])
async def list_project_info_files(db: Session = Depends(get_db)):
    """List all project info files ordered by No."""
    try:
        rows = (
            db.query(models.ProjectInfoFile)
            .order_by(
                models.ProjectInfoFile.display_order.asc(),
                models.ProjectInfoFile.id.asc(),
            )
            .all()
        )
        return [_to_response(row) for row in rows]
    except Exception as e:
        logger.error("Error listing project info files: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post(
    "/",
    response_model=schemas.ProjectInfoFile,
    status_code=status.HTTP_201_CREATED,
)
async def create_project_info_file(
    body: schemas.ProjectInfoFileCreate,
    db: Session = Depends(get_db),
):
    """Create a project info file row, optionally inserting at a given No."""
    try:
        count = db.query(models.ProjectInfoFile).count()
        requested_no = body.no

        if requested_no is None or requested_no < 1 or requested_no > count:
            display_order = count + 1
        else:
            display_order = requested_no
            to_shift = (
                db.query(models.ProjectInfoFile)
                .filter(models.ProjectInfoFile.display_order >= display_order)
                .all()
            )
            for row in to_shift:
                row.display_order += 1

        db_item = models.ProjectInfoFile(
            display_order=display_order,
            category_en=body.category_en.strip(),
            category_he=body.category_he.strip(),
            file_path=body.file_path.strip(),
            description=(body.description or "").strip() or None,
        )
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return _to_response(db_item)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Error creating project info file: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.put("/{file_id}", response_model=schemas.ProjectInfoFile)
async def update_project_info_file(
    file_id: int,
    body: schemas.ProjectInfoFileUpdate,
    db: Session = Depends(get_db),
):
    """Update file path and/or description for a project info file."""
    try:
        db_item = (
            db.query(models.ProjectInfoFile)
            .filter(models.ProjectInfoFile.id == file_id)
            .first()
        )
        if not db_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project info file not found",
            )

        update_data = body.model_dump(exclude_unset=True)
        if "file_path" in update_data and update_data["file_path"] is not None:
            path = update_data["file_path"].strip()
            if not path:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File path is required",
                )
            db_item.file_path = path
        if "description" in update_data:
            desc = update_data["description"]
            db_item.description = (desc or "").strip() or None

        db.commit()
        db.refresh(db_item)
        return _to_response(db_item)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Error updating project info file %s: %s", file_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project_info_file(file_id: int, db: Session = Depends(get_db)):
    """Delete a project info file and renumber remaining rows."""
    try:
        db_item = (
            db.query(models.ProjectInfoFile)
            .filter(models.ProjectInfoFile.id == file_id)
            .first()
        )
        if not db_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project info file not found",
            )
        db.delete(db_item)
        db.flush()
        _renumber(db)
        db.commit()
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Error deleting project info file %s: %s", file_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/{file_id}/open")
async def open_project_info_file(file_id: int, db: Session = Depends(get_db)):
    """Open the file in the default OS application."""
    db_item = (
        db.query(models.ProjectInfoFile)
        .filter(models.ProjectInfoFile.id == file_id)
        .first()
    )
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project info file not found",
        )

    file_path = db_item.file_path
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
        logger.error("Error opening project info file: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error opening file: {exc}",
        )
