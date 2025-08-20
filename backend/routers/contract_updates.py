from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging

from database.database import get_db
from models import models
from schemas import schemas

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=List[schemas.ContractQuantityUpdate])
async def get_contract_updates(db: Session = Depends(get_db)):
    """Get all contract quantity updates ordered by index"""
    try:
        updates = db.query(models.ContractQuantityUpdate).order_by(models.ContractQuantityUpdate.update_index).all()
        return updates
    except Exception as e:
        logger.error(f"Error getting contract updates: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/", response_model=schemas.ContractQuantityUpdate)
async def create_contract_update(db: Session = Depends(get_db)):
    """Create a new contract quantity update"""
    try:
        # Get the next update index
        last_update = db.query(models.ContractQuantityUpdate).order_by(models.ContractQuantityUpdate.update_index.desc()).first()
        next_index = 1 if not last_update else last_update.update_index + 1
        
        # Create the contract update
        contract_update = models.ContractQuantityUpdate(
            update_index=next_index,
            update_name=f"Updated Contract Qty {next_index}"
        )
        db.add(contract_update)
        db.commit()
        db.refresh(contract_update)
        
        # Get all BOQ items
        boq_items = db.query(models.BOQItem).all()
        
        # Create quantity updates for all BOQ items
        for boq_item in boq_items:
            quantity_update = models.BOQItemQuantityUpdate(
                boq_item_id=boq_item.id,
                contract_update_id=contract_update.id,
                updated_contract_quantity=boq_item.original_contract_quantity,
                updated_contract_sum=boq_item.original_contract_quantity * boq_item.price
            )
            db.add(quantity_update)
        
        db.commit()
        
        logger.info(f"Created contract update {next_index} with {len(boq_items)} BOQ item updates")
        return contract_update
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating contract update: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/{update_id}/boq-items", response_model=List[schemas.BOQItemQuantityUpdate])
async def get_boq_item_updates(update_id: int, db: Session = Depends(get_db)):
    """Get all BOQ item updates for a specific contract update"""
    try:
        updates = db.query(models.BOQItemQuantityUpdate).filter(
            models.BOQItemQuantityUpdate.contract_update_id == update_id
        ).all()
        return updates
    except Exception as e:
        logger.error(f"Error getting BOQ item updates: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.put("/{update_id}/boq-items/{boq_item_id}", response_model=schemas.BOQItemQuantityUpdate)
async def update_boq_item_quantity(
    update_id: int,
    boq_item_id: int,
    update_data: schemas.BOQItemQuantityUpdateUpdate,
    db: Session = Depends(get_db)
):
    """Update a BOQ item's contract quantity for a specific update"""
    try:
        # Find the existing update
        quantity_update = db.query(models.BOQItemQuantityUpdate).filter(
            models.BOQItemQuantityUpdate.contract_update_id == update_id,
            models.BOQItemQuantityUpdate.boq_item_id == boq_item_id
        ).first()
        
        if not quantity_update:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="BOQ item quantity update not found"
            )
        
        # Update the quantity
        if update_data.updated_contract_quantity is not None:
            quantity_update.updated_contract_quantity = update_data.updated_contract_quantity
            
            # Get the BOQ item to calculate the new sum
            boq_item = db.query(models.BOQItem).filter(models.BOQItem.id == boq_item_id).first()
            if boq_item:
                quantity_update.updated_contract_sum = update_data.updated_contract_quantity * boq_item.price
        
        # Update the sum if provided
        if update_data.updated_contract_sum is not None:
            quantity_update.updated_contract_sum = update_data.updated_contract_sum
        
        db.commit()
        db.refresh(quantity_update)
        
        logger.info(f"Updated BOQ item {boq_item_id} quantity for contract update {update_id}")
        return quantity_update
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating BOQ item quantity: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.delete("/{update_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contract_update(update_id: int, db: Session = Depends(get_db)):
    """Delete a contract quantity update and all associated BOQ item updates"""
    try:
        # Delete the contract update (cascade will delete BOQ item updates)
        contract_update = db.query(models.ContractQuantityUpdate).filter(
            models.ContractQuantityUpdate.id == update_id
        ).first()
        
        if not contract_update:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contract update not found"
            )
        
        db.delete(contract_update)
        db.commit()
        
        logger.info(f"Deleted contract update {update_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting contract update: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

