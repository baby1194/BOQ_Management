from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging

from database.database import get_db
from models import models
from schemas import schemas
from services.non_boq_service import list_non_boq_items_with_calc_sheets

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
