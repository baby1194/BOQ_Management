from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, sessionmaker
from typing import List
import logging

from database import project_registry
from database.database import get_db, get_project_engine, init_project_database
from models import models
from schemas import schemas
from services.non_boq_service import (
    list_non_boq_items_with_calc_sheets,
    non_boq_import_rows,
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
):
    """Create a new project whose BOQ is the non-BOQ items, including price."""
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Project name is required")
    rows = non_boq_import_rows(db)
    if not rows:
        raise HTTPException(status_code=400, detail="No non-BOQ items to import")

    project = project_registry.create_project_entry(name)
    init_project_database(project["id"])
    Target = sessionmaker(bind=get_project_engine(project["id"]))
    target = Target()
    try:
        for index, row in enumerate(rows):
            item = models.BOQItem(
                display_order=index,
                serial_number=index + 1,
                section_number=row["section_number"],
                description=row["description"],
                unit=row["unit"],
                original_contract_quantity=row["quantity"],
                price=row["price"],
                total_contract_sum=row["total"],
                estimated_quantity=row["quantity"],
                total_estimate=row["total"],
                notes="Imported from non-BOQ calculation sheets",
            )
            target.add(item)
        target.commit()
    except Exception:
        target.rollback()
        raise
    finally:
        target.close()

    missing_price = sum(1 for row in rows if row["missing_price"])
    return {
        "project_id": project["id"],
        "project_name": project["name"],
        "item_count": len(rows),
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
