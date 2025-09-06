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

@router.get("/summaries", response_model=List[schemas.SystemSummary])
async def get_system_summaries(db: Session = Depends(get_db)):
    """Get summaries of all systems with their totals"""
    try:
        # Get all BOQ items
        boq_items = db.query(models.BOQItem).all()
        
        # Get all contract updates
        contract_updates = db.query(models.ContractQuantityUpdate).all()
        
        # Get all BOQ item quantity updates
        boq_item_updates = db.query(models.BOQItemQuantityUpdate).all()
        
        # Group by system and calculate totals
        system_totals = {}
        
        for item in boq_items:
            # Ensure system is a string and handle numeric systems properly
            if item.system is not None:
                # Convert numeric systems to strings (e.g., 3.0 -> "3")
                if isinstance(item.system, (int, float)):
                    system = str(int(float(item.system)))
                else:
                    system = str(item.system)
            else:
                system = "Uncategorized"
            
            if system not in system_totals:
                # Initialize contract update sums dictionary
                contract_update_sums = {}
                for update in contract_updates:
                    contract_update_sums[update.id] = 0.0
                
                system_totals[system] = {
                    "system": system,
                    "description": "",  # Will be loaded from system_info table
                    "total_contract_sum": 0.0,
                    "contract_update_sums": contract_update_sums,
                    "total_estimate": 0.0,
                    "total_submitted": 0.0,
                    "internal_total": 0.0,
                    "total_approved": 0.0,
                    "approved_signed_total": 0.0,
                    "item_count": 0
                }
            
            totals = system_totals[system]
            totals["total_contract_sum"] += float(item.total_contract_sum or 0)
            totals["total_estimate"] += float(item.total_estimate or 0)
            totals["total_submitted"] += float(item.total_submitted or 0)
            totals["internal_total"] += float(item.internal_total or 0)
            totals["total_approved"] += float(item.total_approved_by_project_manager or 0)
            totals["approved_signed_total"] += float(item.approved_signed_total or 0)
            totals["item_count"] += 1
            
            # Add contract update sums for this item
            for update in boq_item_updates:
                if update.boq_item_id == item.id:
                    update_id = update.contract_update_id
                    if update_id in totals["contract_update_sums"]:
                        totals["contract_update_sums"][update_id] += float(update.updated_contract_sum or 0)
        
        print(system_totals)

        # Load descriptions from system_info table
        try:
            # Check if system_info table exists
            result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='system_info'"))
            if result.fetchone():
                # Table exists, load descriptions
                result = db.execute(text("SELECT system, description FROM system_info"))
                descriptions = {row[0]: row[1] for row in result.fetchall()}
                
                # Update descriptions in totals
                for system, totals in system_totals.items():
                    print(system)
                    if system in descriptions:
                        totals["description"] = descriptions[system]
        except Exception as e:
            logger.warning(f"Could not load system descriptions: {e}")
            # Continue without descriptions if table doesn't exist
        
        summaries = []
        for system, totals in system_totals.items():
            summaries.append(schemas.SystemSummary(**totals))
        
        # Sort by system name
        summaries.sort(key=lambda x: x.system)
        
        return summaries
        
    except Exception as e:
        logger.error(f"Error getting system summaries: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.put("/{system}/description")
async def update_system_description(
    system: str,
    description_update: schemas.SystemDescriptionUpdate,
    db: Session = Depends(get_db)
):
    """Update the description for a specific system"""
    try:
        logger.info(f"Updating system description for system '{system}': {description_update.description}")
        
        # Validate input
        if not isinstance(system, str):
            raise ValueError(f"System must be a string, got {type(system)}: {system}")
        
        if not isinstance(description_update.description, str):
            raise ValueError(f"Description must be a string, got {type(description_update.description)}: {description_update.description}")
        
        # Check if system_info table exists
        result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='system_info'"))
        if not result.fetchone():
            # Create the table if it doesn't exist
            logger.info("Creating system_info table")
            try:
                db.execute(text("""
                    CREATE TABLE IF NOT EXISTS system_info (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        system TEXT UNIQUE NOT NULL,
                        description TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                db.commit()
                logger.info("system_info table created successfully")
            except Exception as create_error:
                logger.error(f"Error creating system_info table: {create_error}")
                raise
        
        # Insert or update the description
        logger.info(f"Executing INSERT OR REPLACE for system '{system}'")
        logger.info(f"Parameters: system='{system}' (type: {type(system)}), description='{description_update.description}' (type: {type(description_update.description)})")
        
        try:
            db.execute(text("""
                INSERT OR REPLACE INTO system_info (system, description, updated_at)
                VALUES (:system, :description, CURRENT_TIMESTAMP)
            """), {"system": system, "description": description_update.description})
            db.commit()
            logger.info(f"Description updated successfully for system '{system}'")
        except Exception as db_error:
            logger.error(f"Database error: {db_error}")
            logger.error(f"Error type: {type(db_error)}")
            raise
        
        return {
            "success": True,
            "message": f"Description updated for system: {system}",
            "system": system,
            "description": description_update.description
        }
        
    except Exception as e:
        logger.error(f"Error updating system description: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"System: {system}, Description: {description_update.description if description_update else 'None'}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

