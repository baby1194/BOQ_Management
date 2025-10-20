from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from typing import List
import logging

from database.database import get_db
from models import models
from schemas import schemas

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/", response_model=List[schemas.ConcentrationSheet])
async def get_concentration_sheets(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """Get all concentration sheets with pagination"""
    try:
        sheets = db.query(models.ConcentrationSheet).offset(skip).limit(limit).all()
        return sheets
    except Exception as e:
        logger.error(f"Error fetching concentration sheets: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/with-boq-data", response_model=List[schemas.ConcentrationSheetWithBOQData])
async def get_concentration_sheets_with_boq_data(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """Get all concentration sheets with their associated BOQ item data including latest contract updates"""
    try:
        # Get all concentration sheets with their BOQ items in a single query using joinedload
        sheets = db.query(models.ConcentrationSheet).options(
            joinedload(models.ConcentrationSheet.boq_item)
        ).offset(skip).limit(limit).all()
        
        if not sheets:
            return []
        
        # Get the latest contract update once (for all items)
        latest_contract_update = db.query(models.ContractQuantityUpdate).order_by(
            desc(models.ContractQuantityUpdate.update_index)
        ).first()
        
        # Get all BOQ item IDs from the sheets
        boq_item_ids = [sheet.boq_item_id for sheet in sheets if sheet.boq_item]
        
        # Get all quantity updates for all BOQ items and latest contract update in a single query
        latest_quantity_updates = {}
        if latest_contract_update and boq_item_ids:
            quantity_updates = db.query(models.BOQItemQuantityUpdate).filter(
                models.BOQItemQuantityUpdate.boq_item_id.in_(boq_item_ids),
                models.BOQItemQuantityUpdate.contract_update_id == latest_contract_update.id
            ).all()
            latest_quantity_updates = {update.boq_item_id: update for update in quantity_updates}
        
        result = []
        for sheet in sheets:
            if sheet.boq_item:
                # Get the quantity update for this specific BOQ item
                latest_quantity_update = latest_quantity_updates.get(sheet.boq_item_id)
                
                # Create BOQ item with latest contract update data
                boq_item_dict = {c.key: getattr(sheet.boq_item, c.key) for c in sheet.boq_item.__table__.columns}
                boq_item_dict.update({
                    "latest_contract_quantity": latest_quantity_update.updated_contract_quantity if latest_quantity_update else sheet.boq_item.original_contract_quantity,
                    "latest_contract_sum": latest_quantity_update.updated_contract_sum if latest_quantity_update else (sheet.boq_item.original_contract_quantity * sheet.boq_item.price),
                    "has_contract_updates": latest_contract_update is not None,
                    "latest_update_index": latest_contract_update.update_index if latest_contract_update else None
                })
                
                # Create the combined response - convert sheet to dict and add boq_item
                sheet_dict = {c.key: getattr(sheet, c.key) for c in sheet.__table__.columns}
                sheet_dict["boq_item"] = boq_item_dict
                result.append(sheet_dict)
        
        return result
    except Exception as e:
        logger.error(f"Error fetching concentration sheets with BOQ data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/{sheet_id}", response_model=schemas.ConcentrationSheet)
async def get_concentration_sheet(sheet_id: int, db: Session = Depends(get_db)):
    """Get a specific concentration sheet by ID"""
    try:
        sheet = db.query(models.ConcentrationSheet).filter(models.ConcentrationSheet.id == sheet_id).first()
        if not sheet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Concentration sheet not found"
            )
        return sheet
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching concentration sheet {sheet_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/item/{boq_item_id}", response_model=schemas.ConcentrationSheet)
async def get_concentration_sheet_by_boq_item(boq_item_id: int, db: Session = Depends(get_db)):
    """Get concentration sheet by BOQ item ID"""
    try:
        sheet = db.query(models.ConcentrationSheet).filter(
            models.ConcentrationSheet.boq_item_id == boq_item_id
        ).first()
        if not sheet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Concentration sheet not found for this BOQ item"
            )
        return sheet
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching concentration sheet for BOQ item {boq_item_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/", response_model=schemas.ConcentrationSheet, status_code=status.HTTP_201_CREATED)
async def create_concentration_sheet(sheet: schemas.ConcentrationSheetCreate, db: Session = Depends(get_db)):
    """Create a new concentration sheet"""
    try:
        # Check if BOQ item exists
        boq_item = db.query(models.BOQItem).filter(models.BOQItem.id == sheet.boq_item_id).first()
        if not boq_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="BOQ item not found"
            )
        
        # Check if concentration sheet already exists for this BOQ item
        existing_sheet = db.query(models.ConcentrationSheet).filter(
            models.ConcentrationSheet.boq_item_id == sheet.boq_item_id
        ).first()
        
        if existing_sheet:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Concentration sheet already exists for this BOQ item"
            )
        
        db_sheet = models.ConcentrationSheet(
            boq_item_id=sheet.boq_item_id,
            sheet_name=sheet.sheet_name
        )
        
        db.add(db_sheet)
        db.commit()
        db.refresh(db_sheet)
        
        logger.info(f"Created concentration sheet: {sheet.sheet_name}")
        return db_sheet
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating concentration sheet: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.put("/{sheet_id}", response_model=schemas.ConcentrationSheet)
async def update_concentration_sheet(
    sheet_id: int, 
    sheet_update: schemas.ConcentrationSheetUpdate, 
    db: Session = Depends(get_db)
):
    """Update a concentration sheet"""
    try:
        db_sheet = db.query(models.ConcentrationSheet).filter(models.ConcentrationSheet.id == sheet_id).first()
        if not db_sheet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Concentration sheet not found"
            )
        
        # Update fields if provided
        update_data = sheet_update.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(db_sheet, field, value)
        
        db.commit()
        db.refresh(db_sheet)
        
        logger.info(f"Updated concentration sheet: {db_sheet.sheet_name}")
        return db_sheet
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating concentration sheet {sheet_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.put("/{sheet_id}/project-info", response_model=schemas.ConcentrationSheet)
async def update_concentration_sheet_project_info(
    sheet_id: int, 
    project_info: schemas.ConcentrationSheetUpdate, 
    db: Session = Depends(get_db)
):
    """Update project information for a concentration sheet"""
    try:
        db_sheet = db.query(models.ConcentrationSheet).filter(models.ConcentrationSheet.id == sheet_id).first()
        if not db_sheet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Concentration sheet not found"
            )
        
        # Update only project information fields
        project_fields = ['project_name', 'contractor_in_charge', 'contract_no', 'developer_name']
        update_data = project_info.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if field in project_fields:
                setattr(db_sheet, field, value)
        
        db.commit()
        db.refresh(db_sheet)
        
        logger.info(f"Updated project info for concentration sheet: {db_sheet.sheet_name}")
        return db_sheet
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating project info for concentration sheet {sheet_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.delete("/{sheet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_concentration_sheet(sheet_id: int, db: Session = Depends(get_db)):
    """Delete a concentration sheet"""
    try:
        db_sheet = db.query(models.ConcentrationSheet).filter(models.ConcentrationSheet.id == sheet_id).first()
        if not db_sheet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Concentration sheet not found"
            )
        
        # First, manually delete all concentration entries to avoid foreign key issues
        entries = db.query(models.ConcentrationEntry).filter(
            models.ConcentrationEntry.concentration_sheet_id == sheet_id
        ).all()
        
        for entry in entries:
            db.delete(entry)
        
        # Now delete the concentration sheet
        db.delete(db_sheet)
        db.commit()
        
        logger.info(f"Deleted concentration sheet: {db_sheet.sheet_name} and {len(entries)} entries")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting concentration sheet {sheet_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

# Concentration Entry endpoints
@router.get("/{sheet_id}/entries", response_model=List[schemas.ConcentrationEntry])
async def get_concentration_entries(sheet_id: int, db: Session = Depends(get_db)):
    """Get all entries for a concentration sheet"""
    try:
        entries = db.query(models.ConcentrationEntry).filter(
            models.ConcentrationEntry.concentration_sheet_id == sheet_id
        ).order_by(models.ConcentrationEntry.id).all()
        return entries
    except Exception as e:
        logger.error(f"Error fetching concentration entries: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/{sheet_id}/entries", response_model=schemas.ConcentrationEntry, status_code=status.HTTP_201_CREATED)
async def create_concentration_entry(
    sheet_id: int, 
    entry: schemas.ConcentrationEntryCreate, 
    db: Session = Depends(get_db)
):
    """Create a new concentration entry"""
    try:
        # Check if concentration sheet exists
        sheet = db.query(models.ConcentrationSheet).filter(models.ConcentrationSheet.id == sheet_id).first()
        if not sheet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Concentration sheet not found"
            )
        
        db_entry = models.ConcentrationEntry(
            concentration_sheet_id=sheet_id,
            section_number=entry.section_number,
            description=entry.description,
            calculation_sheet_no=entry.calculation_sheet_no,
            drawing_no=entry.drawing_no,
            estimated_quantity=entry.estimated_quantity,
            quantity_submitted=entry.quantity_submitted,
            internal_quantity=entry.internal_quantity,
            approved_by_project_manager=entry.approved_by_project_manager,
            notes=entry.notes,
            is_manual=True  # Mark as manually created
        )
        
        db.add(db_entry)
        db.commit()
        db.refresh(db_entry)
        
        # Update BOQ Item totals
        await _update_boq_item_totals(sheet.boq_item_id, db)
        
        logger.info(f"Created concentration entry: {entry.section_number}")
        return db_entry
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating concentration entry: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.put("/entries/{entry_id}", response_model=schemas.ConcentrationEntry)
async def update_concentration_entry(
    entry_id: int, 
    entry_update: schemas.ConcentrationEntryUpdate, 
    db: Session = Depends(get_db)
):
    """Update a concentration entry"""
    try:
        db_entry = db.query(models.ConcentrationEntry).filter(models.ConcentrationEntry.id == entry_id).first()
        if not db_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Concentration entry not found"
            )
        
        # Update fields if provided
        update_data = entry_update.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(db_entry, field, value)
        
        db.commit()
        db.refresh(db_entry)
        
        # Update BOQ Item totals
        await _update_boq_item_totals(db_entry.concentration_sheet_id, db)
        
        logger.info(f"Updated concentration entry: {db_entry.section_number}")
        return db_entry
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating concentration entry {entry_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_concentration_entry(entry_id: int, db: Session = Depends(get_db)):
    """Delete a concentration entry"""
    try:
        db_entry = db.query(models.ConcentrationEntry).filter(models.ConcentrationEntry.id == entry_id).first()
        if not db_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Concentration entry not found"
            )
        
        concentration_sheet_id = db_entry.concentration_sheet_id
        db.delete(db_entry)
        db.commit()
        
        # Update BOQ Item totals
        await _update_boq_item_totals(concentration_sheet_id, db)
        
        logger.info(f"Deleted concentration entry: {db_entry.section_number}")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting concentration entry {entry_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

async def _update_boq_item_totals(boq_item_id: int, db: Session):
    """Helper function to update BOQ Item totals based on concentration entries"""
    try:
        # Get the BOQ item
        boq_item = db.query(models.BOQItem).filter(models.BOQItem.id == boq_item_id).first()
        if not boq_item:
            return
        
        # Get all concentration entries for this BOQ item's concentration sheet
        concentration_sheet = db.query(models.ConcentrationSheet).filter(
            models.ConcentrationSheet.boq_item_id == boq_item_id
        ).first()
        
        if not concentration_sheet:
            return
        
        entries = db.query(models.ConcentrationEntry).filter(
            models.ConcentrationEntry.concentration_sheet_id == concentration_sheet.id
        ).all()
        
        # Calculate totals (even if no entries, totals will be 0)
        total_estimated = sum(entry.estimated_quantity for entry in entries)
        total_submitted = sum(entry.quantity_submitted for entry in entries)
        total_internal = sum(entry.internal_quantity for entry in entries)
        total_approved = sum(entry.approved_by_project_manager for entry in entries)
        
        # Update BOQ Item (always update, even if totals are 0)
        boq_item.estimated_quantity = total_estimated
        boq_item.quantity_submitted = total_submitted
        boq_item.internal_quantity = total_internal
        boq_item.approved_by_project_manager = total_approved
        
        # Calculate derived totals
        boq_item.total_estimate = total_estimated * boq_item.price
        boq_item.total_submitted = total_submitted * boq_item.price
        boq_item.internal_total = total_internal * boq_item.price
        boq_item.total_approved_by_project_manager = total_approved * boq_item.price
        
        db.commit()
        logger.info(f"Updated BOQ item {boq_item.section_number} totals: Est={total_estimated}, Submitted={total_submitted}, Internal={total_internal}, Approved={total_approved}")
        
    except Exception as e:
        logger.error(f"Error updating BOQ item totals: {str(e)}")
        db.rollback()