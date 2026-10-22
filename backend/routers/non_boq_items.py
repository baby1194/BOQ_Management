from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, sessionmaker
from typing import List
import logging

from database import project_registry
from database.database import (
    get_db,
    get_project_engine,
    get_project_id,
    init_project_database,
)
from models import models
from schemas import schemas
from services.non_boq_project_copy import add_non_boq_items_to_project, fill_non_boq_project
from services.project_info_copy import copy_project_info
from services.non_boq_service import (
    list_non_boq_items_with_calc_sheets,
    mark_non_boq_items_moved,
    non_boq_import_rows,
    select_import_rows,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[schemas.NonBoqItem])
async def list_non_boq_items(db: Session = Depends(get_db)):
    """List section numbers from calculation sheets that are not in the BOQ list."""
    try:
        return list_non_boq_items_with_calc_sheets(db)
    except Exception as e:
        logger.error("Error fetching non-BOQ items: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/import-as-project")
async def import_non_boq_as_project(
    body: schemas.NonBoqProjectImport,
    db: Session = Depends(get_db),
    source_project_id: str = Depends(get_project_id),
):
    """Create a new project whose BOQ is the non-BOQ items, including price."""
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Project name is required")
    rows = select_import_rows(non_boq_import_rows(db), body.section_numbers)
    if not rows:
        raise HTTPException(status_code=400, detail="No non-BOQ items to import")

    project = project_registry.create_project_entry(name, source_project_id=source_project_id)
    init_project_database(project["id"])
    Target = sessionmaker(bind=get_project_engine(project["id"]))
    target = Target()
    try:
        filled = fill_non_boq_project(db, target, rows)
        copy_project_info(db, target)
        target.commit()
    except Exception:
        target.rollback()
        raise
    finally:
        target.close()

    mark_non_boq_items_moved(db, [row["section_number"] for row in rows], project["id"])
    db.commit()

    missing_price = sum(1 for row in rows if row["missing_price"])
    return {
        "project_id": project["id"],
        "project_name": project["name"],
        "item_count": len(rows),
        "calculation_sheet_count": filled["calculation_sheet_count"],
        "missing_price": missing_price,
    }


@router.post("/add-to-project")
async def add_non_boq_to_existing_project(
    body: schemas.NonBoqProjectAdd,
    db: Session = Depends(get_db),
    source_project_id: str = Depends(get_project_id),
):
    """Add selected non-BOQ items to a project that already exists."""
    target_id = body.target_project_id.strip()
    if not target_id or target_id == source_project_id:
        raise HTTPException(status_code=400, detail="same_project")
    project = project_registry.get_project(target_id)
    if not project:
        raise HTTPException(status_code=404, detail="project_not_found")

    rows = select_import_rows(non_boq_import_rows(db), body.section_numbers)
    if not rows:
        raise HTTPException(status_code=400, detail="no_items")

    init_project_database(project["id"])
    Target = sessionmaker(bind=get_project_engine(project["id"]))
    target = Target()
    try:
        added = add_non_boq_items_to_project(db, target, rows)
        if added["item_count"] == 0:
            target.rollback()
        else:
            target.commit()
    except Exception:
        target.rollback()
        raise
    finally:
        target.close()

    if added["item_count"] == 0:
        raise HTTPException(status_code=400, detail="already_in_project")

    mark_non_boq_items_moved(db, added["added_sections"], project["id"])
    db.commit()

    added_rows = [row for row in rows if row["section_number"] in set(added["added_sections"])]
    missing_price = sum(1 for row in added_rows if row["missing_price"])
    return {
        "project_id": project["id"],
        "project_name": project["name"],
        "item_count": added["item_count"],
        "skipped_count": added["skipped_count"],
        "calculation_sheet_count": added["calculation_sheet_count"],
        "missing_price": missing_price,
    }


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_non_boq_item(item_id: int, db: Session = Depends(get_db)):
    """Remove a section from the non-BOQ items list."""
    item = db.query(models.NonBoqItem).filter(models.NonBoqItem.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Non-BOQ item not found",
        )
    db.delete(item)
    db.commit()
