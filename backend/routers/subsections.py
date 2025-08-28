from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
import logging
from datetime import datetime

from database.database import get_db
from models import models
from schemas import schemas

router = APIRouter()

logger = logging.getLogger(__name__)

@router.get("/summaries", response_model=List[schemas.SubsectionSummary])
async def get_subsection_summaries(db: Session = Depends(get_db)):
    """Get summaries of all subsections with their totals"""
    try:
        # Get all BOQ items
        boq_items = db.query(models.BOQItem).all()
        
        # Group by subsection and calculate totals
        subsection_totals = {}
        
        for item in boq_items:
            # Ensure subsection is a string and handle numeric subsections properly
            if item.subsection is not None:
                # Convert numeric subsections to strings (e.g., 3.0 -> "3")
                if isinstance(item.subsection, (int, float)):
                    subsection = str(int(float(item.subsection)))
                else:
                    subsection = str(item.subsection)
            else:
                subsection = "Uncategorized"
            
            if subsection not in subsection_totals:
                subsection_totals[subsection] = {
                    "subsection": subsection,
                    "description": "",  # Will be loaded from subsection_info table
                    "total_estimate": 0.0,
                    "total_submitted": 0.0,
                    "internal_total": 0.0,
                    "total_approved": 0.0,
                    "approved_signed_total": 0.0,
                    "item_count": 0
                }
            
            totals = subsection_totals[subsection]
            totals["total_estimate"] += float(item.total_estimate or 0)
            totals["total_submitted"] += float(item.total_submitted or 0)
            totals["internal_total"] += float(item.internal_total or 0)
            totals["total_approved"] += float(item.total_approved_by_project_manager or 0)
            totals["approved_signed_total"] += float(item.approved_signed_total or 0)
            totals["item_count"] += 1
        
        print(subsection_totals)
        # print()

        # Load descriptions from subsection_info table
        try:
            # Check if subsection_info table exists
            result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='subsection_info'"))
            if result.fetchone():
                # Table exists, load descriptions
                result = db.execute(text("SELECT subsection, description FROM subsection_info"))
                descriptions = {row[0]: row[1] for row in result.fetchall()}
                
                # Update descriptions in totals
                for subsection, totals in subsection_totals.items():
                    print(subsection)
                    if subsection in descriptions:
                        totals["description"] = descriptions[subsection]
        except Exception as e:
            logger.warning(f"Could not load subsection descriptions: {e}")
            # Continue without descriptions if table doesn't exist
        
        summaries = []
        for subsection, totals in subsection_totals.items():
            summaries.append(schemas.SubsectionSummary(**totals))
        
        # Sort by subsection name
        summaries.sort(key=lambda x: x.subsection)
        
        return summaries
        
    except Exception as e:
        logger.error(f"Error getting subsection summaries: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.put("/{subsection}/description")
async def update_subsection_description(
    subsection: str,
    description_update: schemas.SubsectionDescriptionUpdate,
    db: Session = Depends(get_db)
):
    """Update the description for a specific subsection"""
    try:
        logger.info(f"Updating subsection description for subsection '{subsection}': {description_update.description}")
        
        # Validate input
        if not isinstance(subsection, str):
            raise ValueError(f"Subsection must be a string, got {type(subsection)}: {subsection}")
        
        if not isinstance(description_update.description, str):
            raise ValueError(f"Description must be a string, got {type(description_update.description)}: {description_update.description}")
        
        # Check if subsection_info table exists
        result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='subsection_info'"))
        if not result.fetchone():
            # Create the table if it doesn't exist
            logger.info("Creating subsection_info table")
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS subsection_info (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subsection TEXT UNIQUE NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            db.commit()
            logger.info("subsection_info table created successfully")
        
        # Try to update existing description
        logger.info(f"Executing UPDATE for subsection '{subsection}'")
        result = db.execute(
            text("UPDATE subsection_info SET description = :description, updated_at = :updated_at WHERE subsection = :subsection"),
            {"description": description_update.description, "updated_at": datetime.now(), "subsection": subsection}
        )
        
        if result.rowcount == 0:
            # No existing record, insert new one
            logger.info(f"No existing record found, inserting new one for subsection '{subsection}'")
            db.execute(
                text("INSERT INTO subsection_info (subsection, description, created_at, updated_at) VALUES (:subsection, :description, :created_at, :updated_at)"),
                {"subsection": subsection, "description": description_update.description, "created_at": datetime.now(), "updated_at": datetime.now()}
            )
        
        db.commit()
        logger.info(f"Description updated successfully for subsection '{subsection}'")
        
        return {
            "success": True,
            "message": f"Description updated for subsection '{subsection}'",
            "subsection": subsection,
            "description": description_update.description
        }
        
    except Exception as e:
        logger.error(f"Error updating subsection description: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Subsection: {subsection}, Description: {description_update.description if description_update else 'None'}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )
