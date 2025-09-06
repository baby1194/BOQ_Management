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

@router.get("/summaries", response_model=List[schemas.StructureSummary])
async def get_structure_summaries(db: Session = Depends(get_db)):
    """Get summaries of all structures with their totals"""
    try:
        # Get all BOQ items
        boq_items = db.query(models.BOQItem).all()
        
        # Get all contract updates
        contract_updates = db.query(models.ContractQuantityUpdate).all()
        
        # Get all BOQ item quantity updates
        boq_item_updates = db.query(models.BOQItemQuantityUpdate).all()
        
        # Group by structure and calculate totals
        structure_totals = {}
        
        for item in boq_items:
            # Ensure structure is an integer and handle float structures properly
            if item.structure is not None:
                # Convert float structures to integers (e.g., 3.0 -> 3)
                if isinstance(item.structure, float):
                    structure = int(item.structure)
                else:
                    structure = int(item.structure)
            else:
                structure = 0
            
            if structure not in structure_totals:
                # Initialize contract update sums dictionary
                contract_update_sums = {}
                for update in contract_updates:
                    contract_update_sums[update.id] = 0.0
                
                structure_totals[structure] = {
                    "structure": structure,
                    "description": "",  # Will be loaded from structure_info table
                    "total_contract_sum": 0.0,
                    "contract_update_sums": contract_update_sums,
                    "total_estimate": 0.0,
                    "total_submitted": 0.0,
                    "internal_total": 0.0,
                    "total_approved": 0.0,
                    "approved_signed_total": 0.0,
                    "item_count": 0
                }
            
            totals = structure_totals[structure]
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
        
        print(structure_totals)

        # Load descriptions from structure_info table
        try:
            # Check if structure_info table exists
            result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='structure_info'"))
            if result.fetchone():
                # Table exists, load descriptions
                result = db.execute(text("SELECT structure, description FROM structure_info"))
                descriptions = {row[0]: row[1] for row in result.fetchall()}
                
                # Update descriptions in totals
                for structure, totals in structure_totals.items():
                    print(structure)
                    if structure in descriptions:
                        totals["description"] = descriptions[structure]
        except Exception as e:
            logger.warning(f"Could not load structure descriptions: {e}")
            # Continue without descriptions if table doesn't exist
        
        summaries = []
        for structure, totals in structure_totals.items():
            summaries.append(schemas.StructureSummary(**totals))
        
        # Sort by structure number
        summaries.sort(key=lambda x: x.structure)
        
        return summaries
        
    except Exception as e:
        logger.error(f"Error getting structure summaries: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.put("/{structure}/description")
async def update_structure_description(
    structure: int,
    description_update: schemas.StructureDescriptionUpdate,
    db: Session = Depends(get_db)
):
    """Update the description for a specific structure"""
    try:
        logger.info(f"Updating structure description for structure {structure}: {description_update.description}")
        
        # Validate input
        if not isinstance(structure, int):
            raise ValueError(f"Structure must be an integer, got {type(structure)}: {structure}")
        
        if not isinstance(description_update.description, str):
            raise ValueError(f"Description must be a string, got {type(description_update.description)}: {description_update.description}")
        
        # Check if structure_info table exists
        result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='structure_info'"))
        if not result.fetchone():
            # Create the table if it doesn't exist
            logger.info("Creating structure_info table")
            try:
                db.execute(text("""
                    CREATE TABLE IF NOT EXISTS structure_info (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        structure INTEGER UNIQUE NOT NULL,
                        description TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                db.commit()
                logger.info("structure_info table created successfully")
            except Exception as create_error:
                logger.error(f"Error creating structure_info table: {create_error}")
                raise
        
        # Insert or update the description
        logger.info(f"Executing INSERT OR REPLACE for structure {structure}")
        logger.info(f"Parameters: structure={structure} (type: {type(structure)}), description='{description_update.description}' (type: {type(description_update.description)})")
        
        try:
            db.execute(text("""
                INSERT OR REPLACE INTO structure_info (structure, description, updated_at)
                VALUES (:structure, :description, CURRENT_TIMESTAMP)
            """), {"structure": structure, "description": description_update.description})
            db.commit()
            logger.info(f"Description updated successfully for structure {structure}")
        except Exception as db_error:
            logger.error(f"Database error: {db_error}")
            logger.error(f"Error type: {type(db_error)}")
            raise
        
        return {
            "success": True,
            "message": f"Description updated for structure: {structure}",
            "structure": structure,
            "description": description_update.description
        }
        
    except Exception as e:
        logger.error(f"Error updating structure description: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Structure: {structure}, Description: {description_update.description if description_update else 'None'}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

