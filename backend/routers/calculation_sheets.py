from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
import logging
from database.database import get_db
from models import models
from schemas import schemas
from services.sync_service import SyncService

# Set up logger
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/", response_model=List[schemas.CalculationSheet])
async def get_calculation_sheets(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get all calculation sheets with pagination
    """
    print("___get_calculation_sheets___")
    sheets = db.query(models.CalculationSheet).offset(skip).limit(limit).all()
    return sheets

@router.get("/{sheet_id}", response_model=schemas.CalculationSheet)
async def get_calculation_sheet(
    sheet_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific calculation sheet by ID
    """
    sheet = db.query(models.CalculationSheet).filter(models.CalculationSheet.id == sheet_id).first()
    if not sheet:
        raise HTTPException(status_code=404, detail="Calculation sheet not found")
    return sheet

@router.get("/{sheet_id}/entries", response_model=schemas.CalculationSheetWithEntries)
async def get_calculation_sheet_with_entries(
    sheet_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a calculation sheet with all its entries
    """
    sheet = db.query(models.CalculationSheet).filter(models.CalculationSheet.id == sheet_id).first()
    if not sheet:
        raise HTTPException(status_code=404, detail="Calculation sheet not found")
    
    # Get entries for this sheet
    entries = db.query(models.CalculationEntry).filter(
        models.CalculationEntry.calculation_sheet_id == sheet_id
    ).all()
    
    # Create response with entries
    response = schemas.CalculationSheetWithEntries(
        id=sheet.id,
        file_name=sheet.file_name,
        calculation_sheet_no=sheet.calculation_sheet_no,
        drawing_no=sheet.drawing_no,
        description=sheet.description,
        comment=sheet.comment,
        import_date=sheet.import_date,
        created_at=sheet.created_at,
        updated_at=sheet.updated_at,
        entries=entries
    )
    
    return response

@router.put("/{sheet_id}/comment", response_model=schemas.CalculationSheet)
async def update_calculation_sheet_comment(
    sheet_id: int,
    comment_update: schemas.CalculationSheetUpdate,
    db: Session = Depends(get_db)
):
    """
    Update the comment field of a calculation sheet
    """
    sheet = db.query(models.CalculationSheet).filter(models.CalculationSheet.id == sheet_id).first()
    if not sheet:
        raise HTTPException(status_code=404, detail="Calculation sheet not found")
    
    try:
        # Update only the comment field
        sheet.comment = comment_update.comment
        db.commit()
        db.refresh(sheet)
        return sheet
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating calculation sheet comment: {str(e)}")

@router.delete("/{sheet_id}")
async def delete_calculation_sheet(
    sheet_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a calculation sheet and all its entries, with automatic synchronization
    """
    sheet = db.query(models.CalculationSheet).filter(models.CalculationSheet.id == sheet_id).first()
    if not sheet:
        raise HTTPException(status_code=404, detail="Calculation sheet not found")
    
    try:
        # Initialize sync service
        sync_service = SyncService(db)
        
        # Sync the deletion (this will handle concentration entries and BOQ items)
        sync_result = sync_service.sync_calculation_sheet_deletion(sheet_id)
        
        if not sync_result["success"]:
            logger.warning(f"Sync failed during calculation sheet deletion: {sync_result['message']}")
        
        # Delete the calculation sheet
        db.delete(sheet)
        db.commit()
        
        # Prepare response message
        message = "Calculation sheet deleted successfully"
        if sync_result["success"]:
            message += f". Synchronized: {sync_result['entries_deleted']} concentration entries deleted, {sync_result['boq_items_updated']} BOQ items updated"
        
        return {
            "message": message,
            "sync_result": sync_result
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting calculation sheet: {str(e)}")

@router.delete("/entries/{entry_id}")
async def delete_calculation_entry(
    entry_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a specific calculation entry with automatic synchronization
    """
    entry = db.query(models.CalculationEntry).filter(models.CalculationEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Calculation entry not found")
    
    try:
        # Initialize sync service
        sync_service = SyncService(db)
        
        # Sync the deletion (this will handle concentration entries and BOQ items)
        sync_result = sync_service.sync_calculation_entry_deletion(entry_id)
        
        if not sync_result["success"]:
            logger.warning(f"Sync failed during calculation entry deletion: {sync_result['message']}")
        
        # Delete the calculation entry
        db.delete(entry)
        db.commit()
        
        # Prepare response message
        message = "Calculation entry deleted successfully"
        if sync_result["success"]:
            message += f". Synchronized: {sync_result['entries_deleted']} concentration entries deleted, {sync_result['boq_items_updated']} BOQ items updated"
        
        return {
            "message": message,
            "sync_result": sync_result
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting calculation entry: {str(e)}")

@router.put("/entries/{entry_id}", response_model=schemas.CalculationEntry)
async def update_calculation_entry(
    entry_id: int,
    entry_update: schemas.CalculationEntryUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a calculation entry with automatic synchronization
    """
    entry = db.query(models.CalculationEntry).filter(models.CalculationEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Calculation entry not found")
    
    try:
        # Update fields if provided
        update_data = entry_update.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(entry, field, value)
        
        db.commit()
        db.refresh(entry)
        
        # Initialize sync service and sync the update
        sync_service = SyncService(db)
        sync_result = sync_service.sync_calculation_entry_update(entry_id)
        
        if not sync_result["success"]:
            logger.warning(f"Sync failed during calculation entry update: {sync_result['message']}")
        
        logger.info(f"Updated calculation entry {entry_id} and synced changes")
        return entry
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating calculation entry: {str(e)}")

@router.post("/sync-all", response_model=dict)
async def sync_all_calculation_sheets(db: Session = Depends(get_db)):
    """
    Synchronize all calculation sheets with concentration sheets and BOQ items
    """
    try:
        sync_service = SyncService(db)
        result = sync_service.sync_all_calculation_sheets()
        
        if result["success"]:
            return {
                "success": True,
                "message": result["message"],
                "details": {
                    "sheets_processed": result["sheets_processed"],
                    "entries_updated": result["entries_updated"],
                    "boq_items_updated": result["boq_items_updated"]
                }
            }
        else:
            raise HTTPException(status_code=500, detail=result["message"])
            
    except Exception as e:
        logger.error(f"Error in sync all operation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error synchronizing all calculation sheets: {str(e)}")

@router.post("/{sheet_id}/populate-concentration-entries", response_model=schemas.PopulateConcentrationEntriesResponse)
async def populate_concentration_entries(
    sheet_id: int,
    db: Session = Depends(get_db)
):
    """
    Populate concentration entries from calculation sheet entries
    """
    # Get the calculation sheet
    calculation_sheet = db.query(models.CalculationSheet).filter(models.CalculationSheet.id == sheet_id).first()
    if not calculation_sheet:
        raise HTTPException(status_code=404, detail="Calculation sheet not found")
    
    # Get all calculation entries for this sheet
    calculation_entries = db.query(models.CalculationEntry).filter(
        models.CalculationEntry.calculation_sheet_id == sheet_id
    ).all()
    
    if not calculation_entries:
        raise HTTPException(status_code=400, detail="No calculation entries found for this sheet")
    
    # Validate that calculation entries have valid section numbers
    invalid_entries = [entry for entry in calculation_entries if not entry.section_number or entry.section_number.strip() == ""]
    if invalid_entries:
        logger.warning(f"Found {len(invalid_entries)} calculation entries with invalid section numbers")
        raise HTTPException(
            status_code=400, 
            detail=f"Found {len(invalid_entries)} calculation entries with invalid or empty section numbers. Please ensure all calculation entries have valid section numbers."
        )
    
    # For each calculation entry, find the corresponding concentration sheet by section number
    # We need to find BOQ items with matching section numbers, then get their concentration sheets
    section_numbers = [entry.section_number for entry in calculation_entries]
    
    logger.info(f"Looking for BOQ items with section numbers: {section_numbers}")
    
    # Find BOQ items with matching section numbers
    matching_boq_items = db.query(models.BOQItem).filter(
        models.BOQItem.section_number.in_(section_numbers)
    ).all()
    
    if not matching_boq_items:
        logger.warning(f"No BOQ items found with section numbers: {section_numbers}")
        raise HTTPException(
            status_code=404, 
            detail=f"No BOQ items found with matching section numbers: {section_numbers}. Please ensure the calculation sheet section numbers match existing BOQ item section numbers."
        )
    
    logger.info(f"Found {len(matching_boq_items)} matching BOQ items")
    
    # Create a mapping of section number to concentration sheet
    section_to_concentration_sheet = {}
    for boq_item in matching_boq_items:
        concentration_sheet = db.query(models.ConcentrationSheet).filter(
            models.ConcentrationSheet.boq_item_id == boq_item.id
        ).first()
        
        if concentration_sheet:
            section_to_concentration_sheet[boq_item.section_number] = concentration_sheet
            logger.info(f"Mapped section {boq_item.section_number} to concentration sheet: {concentration_sheet.sheet_name}")
        else:
            logger.warning(f"No concentration sheet found for BOQ item {boq_item.id} with section {boq_item.section_number}")
    
    if not section_to_concentration_sheet:
        raise HTTPException(
            status_code=404, 
            detail="No concentration sheets found for the matching BOQ items. Please ensure concentration sheets exist for the matching BOQ items."
        )
    
    # Log the matching process
    logger.info(f"Populating concentration entries from calculation sheet {calculation_sheet.calculation_sheet_no}")
    logger.info(f"Found {len(matching_boq_items)} matching BOQ items")
    logger.info(f"Found {len(section_to_concentration_sheet)} concentration sheets")
    logger.info(f"Calculation entries to process: {len(calculation_entries)}")
    
    # Debug: Show section numbers and matching details
    logger.info(f"Calculation entry section numbers: {section_numbers}")
    logger.info(f"Matching BOQ item section numbers: {[item.section_number for item in matching_boq_items]}")
    logger.info(f"Concentration sheets found: {[sheet.sheet_name for sheet in section_to_concentration_sheet.values()]}")
    
    # Populate concentration entries
    entries_created = 0
    entries_skipped = 0
    
    try:
        for calc_entry in calculation_entries:
            # Find the corresponding concentration sheet for this entry
            if calc_entry.section_number not in section_to_concentration_sheet:
                logger.warning(f"No concentration sheet found for section {calc_entry.section_number}")
                continue
            
            concentration_sheet = section_to_concentration_sheet[calc_entry.section_number]
            
            # Get existing concentration entries for this specific sheet to check for duplicates
            existing_entries = db.query(models.ConcentrationEntry).filter(
                models.ConcentrationEntry.concentration_sheet_id == concentration_sheet.id
            ).all()
            
            # Check if entry already exists with the same Calculation Sheet No AND Drawing No
            existing_concentration_entry = None
            for entry in existing_entries:
                if (entry.section_number == calc_entry.section_number and
                    entry.calculation_sheet_no == calculation_sheet.calculation_sheet_no and
                    entry.drawing_no == calculation_sheet.drawing_no):
                    existing_concentration_entry = entry
                    break
            
            if existing_concentration_entry:
                # Only update if it's an auto-generated entry, don't override manual entries
                if not existing_concentration_entry.is_manual:
                    existing_concentration_entry.estimated_quantity = calc_entry.estimated_quantity
                    existing_concentration_entry.quantity_submitted = calc_entry.quantity_submitted
                    existing_concentration_entry.description = calculation_sheet.description
                    existing_concentration_entry.notes = f"Auto-updated from calculation sheet {calculation_sheet.calculation_sheet_no}"
                    entries_created += 1  # Count as updated
                    logger.info(f"Updated existing auto-generated entry for section {calc_entry.section_number} with Calculation Sheet No {calculation_sheet.calculation_sheet_no} and Drawing No {calculation_sheet.drawing_no} in sheet {concentration_sheet.sheet_name}")
                else:
                    logger.info(f"Skipped updating manual entry for section {calc_entry.section_number} as it was manually created")
            else:
                # Create new concentration entry
                new_concentration_entry = models.ConcentrationEntry(
                    concentration_sheet_id=concentration_sheet.id,
                    section_number=calc_entry.section_number,  # Use section number from calculation entry
                    description=calculation_sheet.description,  # Use calculation sheet description
                    calculation_sheet_no=calculation_sheet.calculation_sheet_no,
                    drawing_no=calculation_sheet.drawing_no,
                    estimated_quantity=calc_entry.estimated_quantity,
                    quantity_submitted=calc_entry.quantity_submitted,
                    internal_quantity=0.0,
                    approved_by_project_manager=0.0,
                    notes=f"Auto-populated from calculation sheet {calculation_sheet.calculation_sheet_no}",
                    is_manual=False  # Mark as auto-generated
                )
                
                db.add(new_concentration_entry)
                entries_created += 1
                logger.info(f"Created entry for section {calc_entry.section_number} in concentration sheet {concentration_sheet.sheet_name}")
        
        db.commit()
        
        # Update BOQ Items with totals from concentration sheets
        logger.info("Updating BOQ Items with totals from concentration sheets...")
        boq_items_updated = 0
        
        for boq_item in matching_boq_items:
            concentration_sheet = section_to_concentration_sheet.get(boq_item.section_number)
            if concentration_sheet:
                # Get all concentration entries for this sheet
                sheet_entries = db.query(models.ConcentrationEntry).filter(
                    models.ConcentrationEntry.concentration_sheet_id == concentration_sheet.id
                ).all()
                
                if sheet_entries:
                    # Calculate totals
                    total_estimated = sum(entry.estimated_quantity for entry in sheet_entries)
                    total_submitted = sum(entry.quantity_submitted for entry in sheet_entries)
                    total_internal = sum(entry.internal_quantity for entry in sheet_entries)
                    total_approved = sum(entry.approved_by_project_manager for entry in sheet_entries)
                    
                    # Update BOQ Item
                    boq_item.estimated_quantity = total_estimated
                    boq_item.quantity_submitted = total_submitted
                    boq_item.internal_quantity = total_internal
                    boq_item.approved_by_project_manager = total_approved
                    
                    # Calculate derived totals
                    boq_item.total_estimate = total_estimated * boq_item.price
                    boq_item.total_submitted = total_submitted * boq_item.price
                    boq_item.internal_total = total_internal * boq_item.price
                    boq_item.total_approved_by_project_manager = total_approved * boq_item.price
                    
                    boq_items_updated += 1
                    logger.info(f"Updated BOQ item {boq_item.section_number} with totals: Est={total_estimated}, Submitted={total_submitted}, Internal={total_internal}, Approved={total_approved}")
        
        # Commit BOQ Item updates
        if boq_items_updated > 0:
            db.commit()
            logger.info(f"Updated {boq_items_updated} BOQ Items with concentration sheet totals")
        
        return {
            "success": True,
            "message": f"Successfully processed {entries_created} concentration entries (updated existing entries and created new ones as needed). Updated {boq_items_updated} BOQ Items with totals.",
            "entries_created": entries_created,
            "entries_skipped": 0,  # No longer skipping entries
            "boq_items_updated": boq_items_updated,
            "concentration_sheet_id": concentration_sheet.id
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error populating concentration entries: {str(e)}")

@router.post("/populate-all", response_model=schemas.PopulateConcentrationEntriesResponse)
async def populate_all_calculation_entries(
    db: Session = Depends(get_db)
):
    """
    Populate concentration entries from ALL calculation sheets in the database
    This will erase all existing concentration entries first and rewrite them.
    """
    try:
        # Get all calculation sheets
        calculation_sheets = db.query(models.CalculationSheet).all()
        
        if not calculation_sheets:
            raise HTTPException(
                status_code=400, 
                detail="No calculation sheets found in the database"
            )
        
        logger.info(f"Starting bulk population from {len(calculation_sheets)} calculation sheets")
        
        # FIRST: Clear only auto-generated concentration entries before repopulating
        logger.info("Clearing auto-generated concentration entries (preserving manual ones)...")
        try:
            # Delete only auto-generated entries (is_manual = False)
            concentration_entries_deleted = db.query(models.ConcentrationEntry).filter(
                models.ConcentrationEntry.is_manual == False
            ).delete()
            db.commit()
            logger.info(f"Deleted {concentration_entries_deleted} auto-generated concentration entries, preserved manual entries")
        except Exception as e:
            logger.error(f"Error clearing auto-generated concentration entries: {str(e)}")
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Error clearing auto-generated concentration entries: {str(e)}")
        
        total_entries_processed = 0
        total_boq_items_updated = 0
        processed_sheets = 0
        
        for calculation_sheet in calculation_sheets:
            try:
                logger.info(f"Processing calculation sheet {calculation_sheet.calculation_sheet_no} (ID: {calculation_sheet.id})")
                
                # Get all calculation entries for this sheet
                calculation_entries = db.query(models.CalculationEntry).filter(
                    models.CalculationEntry.calculation_sheet_id == calculation_sheet.id
                ).all()
                
                if not calculation_entries:
                    logger.info(f"No calculation entries found for sheet {calculation_sheet.calculation_sheet_no}, skipping")
                    continue
                
                # Validate that calculation entries have valid section numbers
                invalid_entries = [entry for entry in calculation_entries if not entry.section_number or entry.section_number.strip() == ""]
                if invalid_entries:
                    logger.warning(f"Found {len(invalid_entries)} calculation entries with invalid section numbers in sheet {calculation_sheet.calculation_sheet_no}")
                    continue
                
                # For each calculation entry, find the corresponding concentration sheet by section number
                section_numbers = [entry.section_number for entry in calculation_entries]
                
                # Find BOQ items with matching section numbers
                matching_boq_items = db.query(models.BOQItem).filter(
                    models.BOQItem.section_number.in_(section_numbers)
                ).all()
                
                if not matching_boq_items:
                    logger.warning(f"No BOQ items found with section numbers: {section_numbers} for sheet {calculation_sheet.calculation_sheet_no}")
                    continue
                
                # Create a mapping of section number to concentration sheet
                section_to_concentration_sheet = {}
                for boq_item in matching_boq_items:
                    concentration_sheet = db.query(models.ConcentrationSheet).filter(
                        models.ConcentrationSheet.boq_item_id == boq_item.id
                    ).first()
                    
                    if concentration_sheet:
                        section_to_concentration_sheet[boq_item.section_number] = concentration_sheet
                
                if not section_to_concentration_sheet:
                    logger.warning(f"No concentration sheets found for BOQ items in sheet {calculation_sheet.calculation_sheet_no}")
                    continue
                
                # Populate concentration entries for this sheet
                entries_processed = 0
                
                for calc_entry in calculation_entries:
                    # Find the corresponding concentration sheet for this entry
                    if calc_entry.section_number not in section_to_concentration_sheet:
                        continue
                    
                    concentration_sheet = section_to_concentration_sheet[calc_entry.section_number]
                    
                    # Since we cleared auto-generated entries, we can directly create new ones
                    # Create new concentration entry
                    new_concentration_entry = models.ConcentrationEntry(
                        concentration_sheet_id=concentration_sheet.id,
                        section_number=calc_entry.section_number,
                        description=calculation_sheet.description,  # Use calculation sheet description
                        calculation_sheet_no=calculation_sheet.calculation_sheet_no,
                        drawing_no=calculation_sheet.drawing_no,
                        estimated_quantity=calc_entry.estimated_quantity,
                        quantity_submitted=calc_entry.quantity_submitted,
                        internal_quantity=0.0,
                        approved_by_project_manager=0.0,
                        notes=f"Auto-populated from calculation sheet {calculation_sheet.calculation_sheet_no}",
                        is_manual=False  # Mark as auto-generated
                    )
                    
                    db.add(new_concentration_entry)
                    entries_processed += 1
                    logger.info(f"Created new concentration entry for section {calc_entry.section_number} in sheet {concentration_sheet.sheet_name}")
                
                # Update BOQ Items with totals from concentration sheets
                boq_items_updated = 0
                for boq_item in matching_boq_items:
                    concentration_sheet = section_to_concentration_sheet.get(boq_item.section_number)
                    if concentration_sheet:
                        # Get all concentration entries for this sheet
                        sheet_entries = db.query(models.ConcentrationEntry).filter(
                            models.ConcentrationEntry.concentration_sheet_id == concentration_sheet.id
                        ).all()
                        
                        if sheet_entries:
                            # Calculate totals
                            total_estimated = sum(entry.estimated_quantity for entry in sheet_entries)
                            total_submitted = sum(entry.quantity_submitted for entry in sheet_entries)
                            total_internal = sum(entry.internal_quantity for entry in sheet_entries)
                            total_approved = sum(entry.approved_by_project_manager for entry in sheet_entries)
                            
                            # Update BOQ Item
                            boq_item.estimated_quantity = total_estimated
                            boq_item.quantity_submitted = total_submitted
                            boq_item.internal_quantity = total_internal
                            boq_item.approved_by_project_manager = total_approved
                            
                            # Calculate derived totals
                            boq_item.total_estimate = total_estimated * boq_item.price
                            boq_item.total_submitted = total_submitted * boq_item.price
                            boq_item.internal_total = total_internal * boq_item.price
                            boq_item.total_approved_by_project_manager = total_approved * boq_item.price
                            
                            boq_items_updated += 1
                
                # Commit changes for this sheet
                db.commit()
                
                total_entries_processed += entries_processed
                total_boq_items_updated += boq_items_updated
                processed_sheets += 1
                
                logger.info(f"Processed sheet {calculation_sheet.calculation_sheet_no}: {entries_processed} entries created, {boq_items_updated} BOQ items updated")
                
            except Exception as e:
                logger.error(f"Error processing calculation sheet {calculation_sheet.calculation_sheet_no}: {str(e)}")
                db.rollback()
                continue
        
        logger.info(f"Bulk population completed. Processed {processed_sheets} sheets. Total: {total_entries_processed} entries created (after clearing auto-generated entries), {total_boq_items_updated} BOQ items updated, manual entries preserved")
        
        return {
            "success": True,
            "message": f"Successfully cleared auto-generated concentration entries and created {total_entries_processed} new concentration entries from {processed_sheets} calculation sheets. Manual entries were preserved. Updated {total_boq_items_updated} BOQ Items with totals.",
            "entries_created": total_entries_processed,
            "entries_skipped": 0,  # No longer skipping entries
            "boq_items_updated": total_boq_items_updated,
            "concentration_sheet_id": 0  # Not applicable for bulk operation
        }
        
    except Exception as e:
        logger.error(f"Error in bulk population: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in bulk population: {str(e)}")
