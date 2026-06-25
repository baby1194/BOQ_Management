from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from pathlib import Path
import logging
from database.database import get_db, get_project_id, get_project_upload_dir, get_project_export_dir
from fatina_paths import resolve_calculation_sheet_open_path
from models import models
from schemas import schemas
from services.calculation_sheet_sync import (
    perform_sync_all_calculation_sheets,
    push_calculation_sheet_to_concentration_entries,
    run_auto_sync_after_calculation_sheet_changes,
)
from services.sync_service import SyncService
from services.excel_service import ExcelService
from services.non_boq_service import register_non_boq_items_from_calculation_entries
from services.pdf_service import PDFService
from utils.concentration_utils import (
    apply_calculation_entry_quantities,
    compute_submission_percentage,
    concentration_entry_quantities_differ,
)
from utils.calculation_sheet_utils import resolve_calc_entry_current_invoice_id

# Set up logger
logger = logging.getLogger(__name__)


def refresh_calculation_sheet_from_disk(
    sheet: models.CalculationSheet,
    excel_service: ExcelService,
    db: Session,
) -> tuple[int, str | None]:
    """
    Reread one calculation sheet from its source file path.
    Returns (entries_refreshed, error_message_or_none).
    """
    label = f"{sheet.calculation_sheet_no} / {sheet.drawing_no}"
    if not sheet.source_file_path:
        return 0, f"{label} - No source file path saved"

    file_path = Path(sheet.source_file_path)
    if not file_path.is_file():
        return 0, f"{label} - Source file not found: {sheet.source_file_path}"

    try:
        sheet_data = excel_service.read_calculation_sheet_data(str(file_path))
        previous_calculation_sheet_no = sheet.calculation_sheet_no
        sheet.file_name = file_path.name
        sheet.description = sheet_data["description"]
        sheet.calculation_sheet_no = sheet_data["calculation_sheet_no"]
        sheet.drawing_no = sheet_data["drawing_no"]

        db.query(models.CalculationEntry).filter(
            models.CalculationEntry.calculation_sheet_id == sheet.id
        ).delete()

        entries_refreshed = 0
        for entry_data in sheet_data["entries"]:
            db.add(
                models.CalculationEntry(
                    calculation_sheet_id=sheet.id,
                    section_number=entry_data["section_number"],
                    current_invoice_id=entry_data.get("current_invoice_id"),
                    estimated_quantity=entry_data["estimated_quantity"],
                    quantity_submitted=entry_data["quantity_submitted"],
                    submission_breakdown=entry_data.get("submission_breakdown"),
                    notes=entry_data.get("notes", ""),
                )
            )
            entries_refreshed += 1

        register_non_boq_items_from_calculation_entries(db, sheet_data["entries"])

        push_calculation_sheet_to_concentration_entries(
            db,
            sheet,
            lookup_calculation_sheet_no=previous_calculation_sheet_no,
        )

        logger.info(f"Tracked calculation sheet {label} from {file_path}")
        return entries_refreshed, None
    except Exception as e:
        error_msg = f"{label} - {file_path.name}: {str(e)}"
        logger.error(error_msg)
        return 0, error_msg


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
        source_file_path=sheet.source_file_path,
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

@router.put("/{sheet_id}/source-file-path", response_model=schemas.CalculationSheet)
async def update_calculation_sheet_source_file_path(
    sheet_id: int,
    source_file_path_update: schemas.CalculationSheetSourceFilePathUpdate,
    db: Session = Depends(get_db)
):
    """
    Update the source_file_path field of a calculation sheet
    """
    sheet = db.query(models.CalculationSheet).filter(models.CalculationSheet.id == sheet_id).first()
    if not sheet:
        raise HTTPException(status_code=404, detail="Calculation sheet not found")
    
    try:
        # Update only the source_file_path field
        sheet.source_file_path = source_file_path_update.source_file_path
        db.commit()
        db.refresh(sheet)
        return sheet
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating calculation sheet source file path: {str(e)}")

@router.post("/{sheet_id}/open-source-file")
async def open_source_file(
    sheet_id: int,
    db: Session = Depends(get_db),
    project_id: str = Depends(get_project_id),
):
    """
    Open the source Excel file in the default application (Windows)
    """
    import os
    import platform
    import subprocess
    
    sheet = db.query(models.CalculationSheet).filter(models.CalculationSheet.id == sheet_id).first()
    if not sheet:
        raise HTTPException(status_code=404, detail="Calculation sheet not found")
    
    upload_root = get_project_upload_dir(project_id)
    file_path = resolve_calculation_sheet_open_path(sheet, db, upload_root)
    if not file_path:
        raise HTTPException(status_code=400, detail="Source file path not set for this calculation sheet")
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Source file not found at path: {file_path}")
    
    try:
        # Open file based on operating system
        if platform.system() == 'Windows':
            os.startfile(file_path)
        elif platform.system() == 'Darwin':  # macOS
            subprocess.call(['open', file_path])
        else:  # Linux
            subprocess.call(['xdg-open', file_path])
        
        return {"success": True, "message": f"Opening file: {file_path}"}
    except Exception as e:
        logger.error(f"Error opening file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error opening file: {str(e)}")

@router.post("/{sheet_id}/track", response_model=schemas.CalculationSheetsTrackResponse)
async def track_calculation_sheet(
    sheet_id: int,
    db: Session = Depends(get_db),
    project_id: str = Depends(get_project_id),
):
    """Reread one calculation sheet from its saved source file path on disk."""
    sheet = db.query(models.CalculationSheet).filter(
        models.CalculationSheet.id == sheet_id
    ).first()
    if not sheet:
        raise HTTPException(status_code=404, detail="Calculation sheet not found")

    excel_service = ExcelService(exports_dir=get_project_export_dir(project_id))
    entries_refreshed, error = refresh_calculation_sheet_from_disk(
        sheet, excel_service, db
    )

    if error:
        return schemas.CalculationSheetsTrackResponse(
            success=False,
            message=error,
            sheets_updated=0,
            sheets_skipped=1,
            entries_updated=0,
            errors=[error],
        )

    db.commit()
    db.refresh(sheet)

    message = (
        f"Updated calculation sheet {sheet.calculation_sheet_no} "
        f"({entries_refreshed} entries refreshed from disk)"
    )
    message = run_auto_sync_after_calculation_sheet_changes(db, project_id, message)
    return schemas.CalculationSheetsTrackResponse(
        success=True,
        message=message,
        sheets_updated=1,
        sheets_skipped=0,
        entries_updated=entries_refreshed,
        errors=[],
    )

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

@router.post("/bulk-delete", response_model=schemas.BulkDeleteCalculationSheetsResponse)
async def bulk_delete_calculation_sheets(
    request: schemas.BulkDeleteCalculationSheetsRequest,
    db: Session = Depends(get_db)
):
    """
    Delete multiple calculation sheets at once with automatic synchronization
    """
    if not request.sheet_ids:
        raise HTTPException(status_code=400, detail="No sheet IDs provided")
    
    try:
        # Initialize sync service
        sync_service = SyncService(db)
        
        sheets_deleted = 0
        total_entries_deleted = 0
        total_boq_items_updated = 0
        errors = []
        
        # Process each sheet deletion
        for sheet_id in request.sheet_ids:
            try:
                sheet = db.query(models.CalculationSheet).filter(models.CalculationSheet.id == sheet_id).first()
                if not sheet:
                    errors.append(f"Sheet ID {sheet_id} not found")
                    continue
                
                # Sync the deletion (this will handle concentration entries and BOQ items)
                sync_result = sync_service.sync_calculation_sheet_deletion(sheet_id)
                
                if not sync_result["success"]:
                    logger.warning(f"Sync failed during calculation sheet deletion {sheet_id}: {sync_result['message']}")
                    errors.append(f"Sync failed for sheet ID {sheet_id}: {sync_result['message']}")
                
                # Delete the calculation sheet
                db.delete(sheet)
                db.commit()
                
                sheets_deleted += 1
                total_entries_deleted += sync_result.get("entries_deleted", 0)
                total_boq_items_updated += sync_result.get("boq_items_updated", 0)
                
                logger.info(f"Successfully deleted calculation sheet {sheet_id}")
                
            except Exception as e:
                db.rollback()
                error_msg = f"Error deleting sheet ID {sheet_id}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                continue
        
        message = f"Successfully deleted {sheets_deleted} calculation sheet(s)"
        if total_entries_deleted > 0 or total_boq_items_updated > 0:
            message += f". Synchronized: {total_entries_deleted} concentration entries deleted, {total_boq_items_updated} BOQ items updated"
        
        if errors:
            message += f". {len(errors)} error(s) occurred during deletion."
        
        return {
            "success": sheets_deleted > 0,
            "message": message,
            "sheets_deleted": sheets_deleted,
            "total_entries_deleted": total_entries_deleted,
            "total_boq_items_updated": total_boq_items_updated,
            "errors": errors
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error in bulk delete operation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in bulk delete operation: {str(e)}")

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

@router.post("/track", response_model=schemas.CalculationSheetsTrackResponse)
async def track_calculation_sheets(
    db: Session = Depends(get_db),
    project_id: str = Depends(get_project_id),
):
    """
    Reread all calculation sheets from their saved source file paths on disk
    and refresh calculation entry values.
    """
    excel_service = ExcelService(exports_dir=get_project_export_dir(project_id))
    sheets = db.query(models.CalculationSheet).all()

    sheets_updated = 0
    sheets_skipped = 0
    entries_updated = 0
    errors: List[str] = []

    for sheet in sheets:
        entries_refreshed, error = refresh_calculation_sheet_from_disk(
            sheet, excel_service, db
        )
        if error:
            sheets_skipped += 1
            errors.append(error)
        else:
            sheets_updated += 1
            entries_updated += entries_refreshed

    db.commit()

    message = (
        f"Updated {sheets_updated} calculation sheet(s) "
        f"({entries_updated} entries refreshed from disk)"
    )
    if sheets_skipped:
        message += f". Skipped {sheets_skipped} sheet(s)."

    if sheets_updated > 0:
        message = run_auto_sync_after_calculation_sheet_changes(
            db, project_id, message
        )

    return schemas.CalculationSheetsTrackResponse(
        success=sheets_updated > 0 or sheets_skipped == 0,
        message=message,
        sheets_updated=sheets_updated,
        sheets_skipped=sheets_skipped,
        entries_updated=entries_updated,
        errors=errors,
    )


@router.post("/sync-all", response_model=dict)
async def sync_all_calculation_sheets(
    db: Session = Depends(get_db),
    project_id: str = Depends(get_project_id),
):
    """
    Synchronize all calculation sheets with concentration sheets and BOQ items
    """
    try:
        result = perform_sync_all_calculation_sheets(db, project_id)

        if result["success"]:
            return {
                "success": True,
                "message": result["message"],
                "details": result["details"],
            }
        else:
            raise HTTPException(status_code=500, detail=result["message"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in sync all operation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error synchronizing all calculation sheets: {str(e)}")

@router.post("/{sheet_id}/populate-concentration-entries", response_model=schemas.PopulateConcentrationEntriesResponse)
async def populate_concentration_entries(
    sheet_id: int,
    db: Session = Depends(get_db),
    project_id: str = Depends(get_project_id),
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
    boq_items_to_export: set[int] = set()
    
    try:
        for calc_entry in calculation_entries:
            entry_invoice_id = resolve_calc_entry_current_invoice_id(
                calc_entry, calculation_sheet
            )
            # Find the corresponding concentration sheet for this entry
            if calc_entry.section_number not in section_to_concentration_sheet:
                logger.warning(f"No concentration sheet found for section {calc_entry.section_number}")
                continue
            
            concentration_sheet = section_to_concentration_sheet[calc_entry.section_number]
            
            # Get existing concentration entries for this specific sheet to check for duplicates
            existing_entries = db.query(models.ConcentrationEntry).filter(
                models.ConcentrationEntry.concentration_sheet_id == concentration_sheet.id
            ).all()
            
            # Check if entry already exists with the same section + Calculation Sheet No
            existing_concentration_entry = None
            for entry in existing_entries:
                if (entry.section_number == calc_entry.section_number and
                    entry.calculation_sheet_no == calculation_sheet.calculation_sheet_no):
                    existing_concentration_entry = entry
                    break
            
            if existing_concentration_entry:
                if concentration_entry_quantities_differ(
                    existing_concentration_entry,
                    calc_entry,
                    drawing_no=entry_invoice_id,
                ):
                    was_incorrectly_manual = existing_concentration_entry.is_manual
                    apply_calculation_entry_quantities(
                        existing_concentration_entry,
                        calc_entry,
                        drawing_no=entry_invoice_id,
                    )
                    existing_concentration_entry.description = calculation_sheet.description
                    existing_concentration_entry.notes = calc_entry.notes or f"Auto-updated from calculation sheet {calculation_sheet.calculation_sheet_no}"
                    existing_concentration_entry.is_manual = False
                    entries_created += 1
                    boq_items_to_export.add(concentration_sheet.boq_item_id)
                    if was_incorrectly_manual:
                        logger.info(
                            f"Corrected is_manual flag and updated entry for section {calc_entry.section_number} "
                            f"with Calculation Sheet No {calculation_sheet.calculation_sheet_no} and Invoice No {entry_invoice_id}"
                        )
                    else:
                        logger.info(
                            f"Updated existing auto-generated entry for section {calc_entry.section_number} "
                            f"with Calculation Sheet No {calculation_sheet.calculation_sheet_no} and Invoice No {entry_invoice_id} "
                            f"in sheet {concentration_sheet.sheet_name}"
                        )
                elif existing_concentration_entry.is_manual:
                    existing_concentration_entry.is_manual = False
                    existing_concentration_entry.drawing_no = entry_invoice_id
                    entries_skipped += 1
                    logger.info(
                        f"Corrected is_manual flag for section {calc_entry.section_number} "
                        f"(quantities unchanged)"
                    )
                else:
                    entries_skipped += 1
                    logger.info(
                        f"Skipped unchanged entry for section {calc_entry.section_number} "
                        f"with Calculation Sheet No {calculation_sheet.calculation_sheet_no} and Invoice No {entry_invoice_id}"
                    )
            else:
                estimated = float(calc_entry.estimated_quantity or 0)
                submitted = float(calc_entry.quantity_submitted or 0)
                # Create new concentration entry
                new_concentration_entry = models.ConcentrationEntry(
                    concentration_sheet_id=concentration_sheet.id,
                    section_number=calc_entry.section_number,  # Use section number from calculation entry
                    description=calculation_sheet.description,  # Use calculation sheet description
                    calculation_sheet_no=calculation_sheet.calculation_sheet_no,
                    drawing_no=entry_invoice_id,
                    estimated_quantity=estimated,
                    quantity_submitted=submitted,
                    submission_percentage=compute_submission_percentage(
                        estimated, submitted
                    ),
                    submission_breakdown=getattr(
                        calc_entry, "submission_breakdown", None
                    ),
                    internal_quantity=0.0,
                    approved_by_project_manager=0.0,
                    notes=calc_entry.notes or f"Auto-populated from calculation sheet {calculation_sheet.calculation_sheet_no}",
                    is_manual=False  # Mark as auto-generated
                )
                
                db.add(new_concentration_entry)
                entries_created += 1
                boq_items_to_export.add(concentration_sheet.boq_item_id)
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

        concentration_sheets_exported = 0
        if boq_items_to_export:
            pdf_service = PDFService(exports_dir=get_project_export_dir(project_id))
            concentration_sheets_exported = pdf_service.export_concentration_sheets_for_boq_items(
                boq_items_to_export, db
            )
            logger.info(
                f"Exported {concentration_sheets_exported} concentration sheet PDF(s) to Fatina "
                f"after populating entries"
            )
        
        return {
            "success": True,
            "message": f"Successfully processed {entries_created} concentration entries (updated existing entries and created new ones as needed). Updated {boq_items_updated} BOQ Items with totals. Exported {concentration_sheets_exported} concentration sheet PDF(s) to Fatina.",
            "entries_created": entries_created,
            "entries_skipped": entries_skipped,
            "boq_items_updated": boq_items_updated,
            "concentration_sheet_id": concentration_sheet.id,
            "concentration_sheets_exported": concentration_sheets_exported,
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error populating concentration entries: {str(e)}")
