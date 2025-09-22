from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging

from database.database import get_db
from models import models
from schemas import schemas

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/", response_model=List[schemas.BOQItem])
async def get_boq_items(
    skip: int = 0, 
    limit: int = 10000, 
    db: Session = Depends(get_db)
):
    """Get all BOQ items with pagination"""
    try:
        items = db.query(models.BOQItem).offset(skip).limit(limit).all()
        return items
    except Exception as e:
        logger.error(f"Error fetching BOQ items: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/{item_id}", response_model=schemas.BOQItem)
async def get_boq_item(item_id: int, db: Session = Depends(get_db)):
    """Get a specific BOQ item by ID"""
    try:
        item = db.query(models.BOQItem).filter(models.BOQItem.id == item_id).first()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="BOQ item not found"
            )
        return item
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching BOQ item {item_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/", response_model=schemas.BOQItem, status_code=status.HTTP_201_CREATED)
async def create_boq_item(item: schemas.BOQItemCreate, db: Session = Depends(get_db)):
    """Create a new BOQ item"""
    try:
        # Check if section number already exists
        existing_item = db.query(models.BOQItem).filter(
            models.BOQItem.section_number == item.section_number
        ).first()
        
        if existing_item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Section number already exists"
            )
        
        db_item = models.BOQItem(
            # serial_number will be set to id after creation
            structure=item.structure,
            system=item.system,
            section_number=item.section_number,
            description=item.description,
            unit=item.unit,
            original_contract_quantity=item.original_contract_quantity,
            price=item.price,
            total_contract_sum=item.total_contract_sum,
            # Set default values for fields removed from frontend form
            estimated_quantity=0.0,
            quantity_submitted=0.0,
            internal_quantity=0.0,
            approved_by_project_manager=0.0,
            total_estimate=0.0,
            total_submitted=0.0,
            internal_total=0.0,
            total_approved_by_project_manager=0.0,
            approved_signed_quantity=0.0,
            approved_signed_total=0.0,
            notes=None,
            subsection=item.subsection
        )
        
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        
        # Set serial_number to id value
        db_item.serial_number = db_item.id
        db.commit()
        db.refresh(db_item)
        
        logger.info(f"Created BOQ item: {item.section_number}")
        return db_item
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating BOQ item: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.put("/{item_id}", response_model=schemas.BOQItem)
async def update_boq_item(
    item_id: int, 
    item_update: schemas.BOQItemUpdate, 
    db: Session = Depends(get_db)
):
    """Update a BOQ item"""
    try:
        db_item = db.query(models.BOQItem).filter(models.BOQItem.id == item_id).first()
        if not db_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="BOQ item not found"
            )
        
        # Update fields if provided
        update_data = item_update.dict(exclude_unset=True)
        
        # Recalculate total contract sum if quantity or price changed
        if 'original_contract_quantity' in update_data or 'price' in update_data:
            new_quantity = update_data.get('original_contract_quantity', db_item.original_contract_quantity)
            new_price = update_data.get('price', db_item.price)
            update_data['total_contract_sum'] = new_quantity * new_price
        
        # Recalculate approved signed total if approved_signed_quantity changed
        if 'approved_signed_quantity' in update_data:
            new_approved_quantity = update_data.get('approved_signed_quantity')
            update_data['approved_signed_total'] = new_approved_quantity * db_item.price
        
        # Recalculate other totals if their base quantities changed
        if 'estimated_quantity' in update_data:
            update_data['total_estimate'] = update_data.get('estimated_quantity') * db_item.price
        
        if 'quantity_submitted' in update_data:
            update_data['total_submitted'] = update_data.get('quantity_submitted') * db_item.price
        
        if 'internal_quantity' in update_data:
            update_data['internal_total'] = update_data.get('internal_quantity') * db_item.price
        
        if 'approved_by_project_manager' in update_data:
            update_data['total_approved_by_project_manager'] = update_data.get('approved_by_project_manager') * db_item.price
        
        for field, value in update_data.items():
            setattr(db_item, field, value)
        
        db.commit()
        db.refresh(db_item)
        
        logger.info(f"Updated BOQ item: {db_item.section_number}")
        return db_item
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating BOQ item {item_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_boq_item(item_id: int, db: Session = Depends(get_db)):
    """Delete a BOQ item and all related concentration sheets and entries"""
    try:
        db_item = db.query(models.BOQItem).filter(models.BOQItem.id == item_id).first()
        if not db_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="BOQ item not found"
            )
        
        # Get the section number for logging before deletion
        section_number = db_item.section_number
        
        # Delete related concentration sheets and their entries (cascade will handle ConcentrationEntries)
        concentration_sheets = db.query(models.ConcentrationSheet).filter(
            models.ConcentrationSheet.boq_item_id == item_id
        ).all()
        
        concentration_sheets_count = len(concentration_sheets)
        total_entries_count = 0
        
        for sheet in concentration_sheets:
            # Count entries before deletion for logging
            entries_count = db.query(models.ConcentrationEntry).filter(
                models.ConcentrationEntry.concentration_sheet_id == sheet.id
            ).count()
            total_entries_count += entries_count
            
            # Delete the sheet (cascade will delete entries)
            db.delete(sheet)
        
        # Delete the BOQ item (cascade will handle quantity_updates)
        db.delete(db_item)
        db.commit()
        
        logger.info(
            f"Deleted BOQ item: {section_number} with {concentration_sheets_count} "
            f"concentration sheets and {total_entries_count} concentration entries"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting BOQ item {item_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/code/{section_number}", response_model=schemas.BOQItem)
async def get_boq_item_by_section_number(section_number: str, db: Session = Depends(get_db)):
    """Get a BOQ item by section number"""
    try:
        item = db.query(models.BOQItem).filter(models.BOQItem.section_number == section_number).first()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="BOQ item not found"
            )
        return item
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching BOQ item by section number {section_number}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/bulk", response_model=List[schemas.BOQItem], status_code=status.HTTP_201_CREATED)
async def create_bulk_boq_items(
    items: List[schemas.BOQItemCreate], 
    db: Session = Depends(get_db)
):
    """Create multiple BOQ items at once"""
    try:
        created_items = []
        
        for item in items:
            # Check if section number already exists
            existing_item = db.query(models.BOQItem).filter(
                models.BOQItem.section_number == item.section_number
            ).first()
            
            if existing_item:
                logger.warning(f"Skipping duplicate section number: {item.section_number}")
                continue
            
            db_item = models.BOQItem(
                # serial_number will be set to id after creation
                structure=item.structure,
                system=item.system,
                section_number=item.section_number,
                description=item.description,
                unit=item.unit,
                original_contract_quantity=item.original_contract_quantity,
                price=item.price,
                total_contract_sum=item.total_contract_sum,
                # Set default values for fields removed from frontend form
                estimated_quantity=0.0,
                quantity_submitted=0.0,
                internal_quantity=0.0,
                approved_by_project_manager=0.0,
                total_estimate=0.0,
                total_submitted=0.0,
                internal_total=0.0,
                total_approved_by_project_manager=0.0,
                approved_signed_quantity=0.0,
                approved_signed_total=0.0,
                notes=None,
                subsection=item.subsection
            )
            
            db.add(db_item)
            created_items.append(db_item)
        
        db.commit()
        
        # Set serial_number to id for all created items
        for item in created_items:
            db.refresh(item)
            item.serial_number = item.id
        
        # Commit the serial_number updates
        db.commit()
        
        # Refresh all created items again
        for item in created_items:
            db.refresh(item)
        
        logger.info(f"Created {len(created_items)} BOQ items")
        return created_items
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating bulk BOQ items: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) 

@router.get("/{item_id}/with-latest-contract-update", response_model=schemas.BOQItemWithLatestContractUpdate)
async def get_boq_item_with_latest_contract_update(item_id: int, db: Session = Depends(get_db)):
    """Get BOQ item with its latest contract update quantities"""
    try:
        # Get the BOQ item
        boq_item = db.query(models.BOQItem).filter(models.BOQItem.id == item_id).first()
        if not boq_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="BOQ item not found"
            )
        
        # Get the latest contract update (highest update_index)
        latest_contract_update = db.query(models.ContractQuantityUpdate).order_by(
            models.ContractQuantityUpdate.update_index.desc()
        ).first()
        
        # Get the quantity update for this BOQ item and latest contract update
        latest_quantity_update = None
        if latest_contract_update:
            latest_quantity_update = db.query(models.BOQItemQuantityUpdate).filter(
                models.BOQItemQuantityUpdate.boq_item_id == item_id,
                models.BOQItemQuantityUpdate.contract_update_id == latest_contract_update.id
            ).first()
        
        # Create response with latest contract quantities
        response_data = {
            **boq_item.__dict__,
            "latest_contract_quantity": latest_quantity_update.updated_contract_quantity if latest_quantity_update else boq_item.original_contract_quantity,
            "latest_contract_sum": latest_quantity_update.updated_contract_sum if latest_quantity_update else (boq_item.original_contract_quantity * boq_item.price),
            "has_contract_updates": latest_contract_update is not None,
            "latest_update_index": latest_contract_update.update_index if latest_contract_update else None
        }
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting BOQ item with latest contract update: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) 