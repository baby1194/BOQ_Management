from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from sqlalchemy.orm import Session
from typing import List, Dict
from pydantic import BaseModel
import pandas as pd
import os
from pathlib import Path
import logging
import tempfile
import shutil

from database.database import get_db
from models import models
from schemas import schemas
from services.excel_service import ExcelService

router = APIRouter(prefix="/file-import", tags=["file-import"])

# Response model for create concentration sheets
class CreateConcentrationSheetsResponse(BaseModel):
    success: bool
    message: str
    created_count: int

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base directory for creating folders
FATINA_BASE_DIR = Path("C:/FATINA")

def sanitize_folder_name(folder_name: str) -> str:
    """
    Sanitize folder name to avoid invalid characters for Windows
    """
    return folder_name.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')

def create_folders_for_boq_items(db: Session):
    """
    Create folders named after section_numbers of BOQ items under C:\FATINA\
    Skips folders that already exist
    """
    try:
        # Ensure base directory exists
        FATINA_BASE_DIR.mkdir(parents=True, exist_ok=True)
        
        # Get all BOQ items (section_number is required and unique)
        boq_items = db.query(models.BOQItem).all()
        
        created_count = 0
        skipped_count = 0
        
        for item in boq_items:
            if item.section_number:
                # Use section_number as folder name
                folder_name = sanitize_folder_name(str(item.section_number))
                folder_path = FATINA_BASE_DIR / folder_name
                
                # Skip if folder already exists
                if folder_path.exists() and folder_path.is_dir():
                    skipped_count += 1
                    logger.debug(f"Folder already exists: {folder_path}")
                else:
                    try:
                        folder_path.mkdir(parents=True, exist_ok=True)
                        # Double-check that folder was created successfully
                        if folder_path.exists() and folder_path.is_dir():
                            created_count += 1
                            logger.info(f"Created folder: {folder_path}")
                        else:
                            logger.warning(f"Folder creation may have failed: {folder_path}")
                    except PermissionError as e:
                        logger.error(f"Permission denied creating folder {folder_path}: {str(e)}")
                    except Exception as e:
                        logger.error(f"Error creating folder {folder_path}: {str(e)}")
        
        logger.info(f"Folder creation completed: {created_count} created, {skipped_count} skipped")
        return created_count, skipped_count
        
    except PermissionError as e:
        logger.error(f"Permission denied accessing base directory {FATINA_BASE_DIR}: {str(e)}")
        return 0, 0
    except Exception as e:
        logger.error(f"Error in create_folders_for_boq_items: {str(e)}")
        return 0, 0

def save_calculation_sheet_to_item_folders(
    source_file_path: Path,
    calculation_entries: List[Dict],
    db: Session
) -> int:
    """
    Save calculation sheet Excel file to all contract item folders related to the calculation sheet.
    Each calculation sheet contains calculations for one or more items (identified by section_number).
    
    Args:
        source_file_path: Path to the source Excel file
        calculation_entries: List of calculation entries with section_number
        db: Database session
        
    Returns:
        Number of folders the file was saved to
    """
    try:
        # Ensure base directory exists
        FATINA_BASE_DIR.mkdir(parents=True, exist_ok=True)
        
        # Extract unique section numbers from calculation entries
        section_numbers = set()
        for entry in calculation_entries:
            section_number = entry.get('section_number')
            if section_number and str(section_number).strip():
                section_numbers.add(str(section_number).strip())
        
        if not section_numbers:
            logger.warning(f"No valid section numbers found in calculation entries for file: {source_file_path}")
            return 0
        
        # Find BOQ items with matching section numbers
        matching_boq_items = db.query(models.BOQItem).filter(
            models.BOQItem.section_number.in_(section_numbers)
        ).all()
        
        if not matching_boq_items:
            logger.warning(f"No BOQ items found with section numbers: {section_numbers} for file: {source_file_path}")
            return 0
        
        files_saved = 0
        
        # Save the file to each related item's folder
        for boq_item in matching_boq_items:
            if not boq_item.section_number:
                continue
                
            # Create folder path using sanitized section number
            folder_name = sanitize_folder_name(str(boq_item.section_number))
            folder_path = FATINA_BASE_DIR / folder_name
            
            try:
                # Create folder if it doesn't exist
                folder_path.mkdir(parents=True, exist_ok=True)
                
                # Copy the Excel file to the folder
                destination_file = folder_path / source_file_path.name
                
                # Handle filename conflicts by adding a number suffix
                original_destination = destination_file
                counter = 1
                while destination_file.exists():
                    stem = original_destination.stem
                    suffix = original_destination.suffix
                    destination_file = folder_path / f"{stem}_{counter}{suffix}"
                    counter += 1
                
                # Copy the file
                shutil.copy2(source_file_path, destination_file)
                files_saved += 1
                logger.info(f"Saved calculation sheet to folder: {destination_file}")
                
            except PermissionError as e:
                logger.error(f"Permission denied saving file to folder {folder_path}: {str(e)}")
            except Exception as e:
                logger.error(f"Error saving file to folder {folder_path}: {str(e)}")
        
        logger.info(f"Saved calculation sheet {source_file_path.name} to {files_saved} item folder(s)")
        return files_saved
        
    except Exception as e:
        logger.error(f"Error in save_calculation_sheet_to_item_folders: {str(e)}")
        return 0

@router.post("/upload/", response_model=schemas.ImportResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload and import a single Excel file
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files are supported")
    
    try:
        # Save uploaded file
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)
        file_path = upload_dir / file.filename
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Process the file
        excel_service = ExcelService()
        items, errors = excel_service.process_excel_file(file_path)
        
        if not items:
            raise HTTPException(status_code=400, detail="No valid items found in file")
        
        # Import items to database
        imported_count = 0
        skipped_count = 0
        
        for item_data in items:
            # print("_________________", item_data)
            try:
                # Check if item already exists by section_number
                existing_item = db.query(models.BOQItem).filter(
                    models.BOQItem.section_number == item_data["section_number"]
                ).first()
                
                if existing_item:
                    # Skip existing item
                    skipped_count += 1
                    logger.info(f"Skipping existing BOQ item: {item_data['section_number']}")
                else:
                    # Create new item - serial_number will be automatically set to id by the event listener
                    new_item = models.BOQItem(**item_data)
                    db.add(new_item)
                    imported_count += 1
                    
            except Exception as e:
                errors.append(f"Error processing item {item_data.get('section_number', 'Unknown')}: {str(e)}")
        
        # Commit changes
        db.commit()
        
        # Set serial_number to id for all newly imported items
        if imported_count > 0:
            # Get all items that were just imported (those without serial_number set)
            new_items = db.query(models.BOQItem).filter(models.BOQItem.serial_number.is_(None)).all()
            for item in new_items:
                item.serial_number = item.id
            
            # Commit the serial_number updates
            db.commit()
            
            # Create folders for all BOQ items (including newly imported ones)
            create_folders_for_boq_items(db)
        
        # Create import log
        log = models.ImportLog(
            file_name=file.filename,
            file_path=str(file_path),
            status="success" if not errors else "partial" if imported_count > 0 else "error",
            error_message="; ".join(errors) if errors else None,
            items_processed=len(items),
            items_updated=imported_count
        )
        db.add(log)
        db.commit()
        
        # Prepare success message
        message_parts = []
        if imported_count > 0:
            message_parts.append(f"{imported_count} items imported")
        if skipped_count > 0:
            message_parts.append(f"{skipped_count} items skipped (already exist)")
        
        success_message = f"File processed successfully. {', '.join(message_parts)}." if message_parts else "No new items to import."
        
        return schemas.ImportResponse(
            success=True,
            message=success_message,
            files_processed=1,
            items_updated=imported_count,
            errors=errors
        )
        
    except Exception as e:
        logger.error(f"Error processing file {file.filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@router.post("/import-folder/", response_model=schemas.ImportResponse)
async def import_folder(
    request: schemas.ImportRequest,
    db: Session = Depends(get_db)
):
    """
    Import all Excel files from a folder
    """
    folder_path = Path(request.folder_path)
    
    if not folder_path.exists():
        raise HTTPException(status_code=400, detail="Folder does not exist")
    
    if not folder_path.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")
    
    excel_files = []
    if request.recursive:
        excel_files = list(folder_path.rglob("*.xlsx")) + list(folder_path.rglob("*.xls"))
    else:
        excel_files = list(folder_path.glob("*.xlsx")) + list(folder_path.glob("*.xls"))
    
    if not excel_files:
        raise HTTPException(status_code=400, detail="No Excel files found in folder")
    
    excel_service = ExcelService()
    total_items_updated = 0
    all_errors = []
    
    for file_path in excel_files:
        try:
            logger.info(f"Processing file: {file_path}")
            items, errors = excel_service.process_excel_file(file_path)
            
            if errors:
                all_errors.extend([f"{file_path.name}: {error}" for error in errors])
            
            if items:
                # Import items to database
                imported_count = 0
                skipped_count = 0
                
                for item_data in items:
                    try:
                        # Check if item already exists by section_number
                        existing_item = db.query(models.BOQItem).filter(
                            models.BOQItem.section_number == item_data["section_number"]
                        ).first()
                        
                        if existing_item:
                            # Skip existing item
                            skipped_count += 1
                            logger.info(f"Skipping existing BOQ item: {item_data['section_number']} from file {file_path.name}")
                        else:
                            # Create new item - serial_number will be automatically set to id by the event listener
                            new_item = models.BOQItem(**item_data)
                            db.add(new_item)
                            imported_count += 1
                            
                    except Exception as e:
                        all_errors.append(f"{file_path.name} - Error processing item {item_data.get('section_number', 'Unknown')}: {str(e)}")
                
                total_items_updated += imported_count
                
                # Add skipped items info to errors for display
                if skipped_count > 0:
                    all_errors.append(f"{file_path.name} - Skipped {skipped_count} existing items")
                
                # Create import log for this file
                log = models.ImportLog(
                    file_name=file_path.name,
                    file_path=str(file_path),
                    status="success" if not errors else "partial" if imported_count > 0 else "error",
                    error_message="; ".join(errors) if errors else None,
                    items_processed=len(items),
                    items_updated=imported_count
                )
                db.add(log)
                
        except Exception as e:
            error_msg = f"Error processing file {file_path.name}: {str(e)}"
            logger.error(error_msg)
            all_errors.append(error_msg)
    
    # Commit all changes
    db.commit()
    
    # Set serial_number to id for all newly imported items
    if total_items_updated > 0:
        # Get all items that were just imported (those without serial_number set)
        new_items = db.query(models.BOQItem).filter(models.BOQItem.serial_number.is_(None)).all()
        for item in new_items:
            item.serial_number = item.id
        
        # Commit the serial_number updates
        db.commit()
        
        # Create folders for all BOQ items (including newly imported ones)
        create_folders_for_boq_items(db)
    
    # Count skipped items from errors
    skipped_messages = [error for error in all_errors if "Skipped" in error and "existing items" in error]
    actual_errors = [error for error in all_errors if not ("Skipped" in error and "existing items" in error)]
    
    return schemas.ImportResponse(
        success=len(actual_errors) == 0,
        message=f"Processed {len(excel_files)} files. {total_items_updated} items imported.",
        files_processed=len(excel_files),
        items_updated=total_items_updated,
        errors=all_errors  # Include both errors and skipped info
    )

@router.get("/logs/", response_model=List[schemas.ImportLog])
async def get_import_logs(
    db: Session = Depends(get_db),
    limit: int = 50
):
    """
    Get import logs
    """
    logs = db.query(models.ImportLog).order_by(models.ImportLog.import_date.desc()).limit(limit).all()
    return logs

@router.post("/create-concentration-sheets/", response_model=CreateConcentrationSheetsResponse)
async def create_concentration_sheets_for_all_items(db: Session = Depends(get_db)):
    """
    Create concentration sheets for all BOQ items that don't have them yet
    """
    try:
        # Get all BOQ items
        boq_items = db.query(models.BOQItem).all()
        
        if not boq_items:
            return CreateConcentrationSheetsResponse(
                success=False,
                message="No BOQ items found",
                created_count=0
            )
        
        created_count = 0
        
        for boq_item in boq_items:
            # Check if concentration sheet already exists for this BOQ item
            existing_sheet = db.query(models.ConcentrationSheet).filter(
                models.ConcentrationSheet.boq_item_id == boq_item.id
            ).first()
            
            if not existing_sheet:
                # Create new concentration sheet
                sheet_name = f"Concentration Sheet - {boq_item.section_number}"
                
                new_sheet = models.ConcentrationSheet(
                    boq_item_id=boq_item.id,
                    sheet_name=sheet_name
                )
                
                db.add(new_sheet)
                created_count += 1
        
        # Commit all changes
        db.commit()
        
        logger.info(f"Created {created_count} concentration sheets")
        
        return CreateConcentrationSheetsResponse(
            success=True,
            message=f"Successfully created {created_count} concentration sheets",
            created_count=created_count
        )
        
    except Exception as e:
        db.rollback()
        error_msg = f"Error creating concentration sheets: {str(e)}"
        logger.error(error_msg)
        return CreateConcentrationSheetsResponse(
            success=False,
            message=error_msg,
            created_count=0
        )

@router.post("/import-calculation-sheets-from-folder/", response_model=schemas.CalculationImportResponse)
async def import_calculation_sheets_from_folder(
    request: schemas.ImportRequest,
    db: Session = Depends(get_db)
):
    """
    Import calculation sheet Excel files from a folder path
    Automatically captures and saves the source file paths
    """
    folder_path = Path(request.folder_path)
    
    if not folder_path.exists():
        raise HTTPException(status_code=400, detail="Folder does not exist")
    
    if not folder_path.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")
    
    # Find all Excel files in the folder
    excel_files = []
    if request.recursive:
        excel_files = list(folder_path.rglob("*.xlsx")) + list(folder_path.rglob("*.xls"))
    else:
        excel_files = list(folder_path.glob("*.xlsx")) + list(folder_path.glob("*.xls"))
    
    if not excel_files:
        raise HTTPException(status_code=400, detail="No Excel files found in folder")
    
    excel_service = ExcelService()
    total_sheets_imported = 0
    total_entries_imported = 0
    all_errors = []
    
    for file_path in excel_files:
        try:
            logger.info(f"Processing calculation sheet file: {file_path}")
            
            # Process the calculation sheet
            sheet_data = excel_service.read_calculation_sheet_data(str(file_path))
            
            # Get the full source file path (automatically captured from folder)
            source_file_path = str(file_path.absolute())
            
            # Check if calculation sheet already exists (by calculation_sheet_no and drawing_no)
            existing_sheet = db.query(models.CalculationSheet).filter(
                models.CalculationSheet.calculation_sheet_no == sheet_data['calculation_sheet_no'],
                models.CalculationSheet.drawing_no == sheet_data['drawing_no']
            ).first()
            
            if existing_sheet:
                # Update existing calculation sheet with new data
                logger.info(f"Updating existing calculation sheet: {file_path.name} - Sheet No: {sheet_data['calculation_sheet_no']}, Drawing No: {sheet_data['drawing_no']}")
                
                # Update the existing sheet with new data
                existing_sheet.file_name = file_path.name
                existing_sheet.description = sheet_data['description']
                existing_sheet.source_file_path = source_file_path  # Always update with the actual path
                
                # Delete existing calculation entries for this sheet
                db.query(models.CalculationEntry).filter(
                    models.CalculationEntry.calculation_sheet_id == existing_sheet.id
                ).delete()
                
                current_sheet = existing_sheet
            else:
                # Create new calculation sheet record
                logger.info(f"Creating new calculation sheet: {file_path.name} - Sheet No: {sheet_data['calculation_sheet_no']}, Drawing No: {sheet_data['drawing_no']}")
                
                new_sheet = models.CalculationSheet(
                    file_name=file_path.name,
                    calculation_sheet_no=sheet_data['calculation_sheet_no'],
                    drawing_no=sheet_data['drawing_no'],
                    description=sheet_data['description'],
                    source_file_path=source_file_path  # Automatically save the full path
                )
                
                db.add(new_sheet)
                db.flush()  # Get the ID without committing
                current_sheet = new_sheet
            
            # Create calculation entries (for both new and updated sheets)
            entries_created = 0
            for entry_data in sheet_data['entries']:
                new_entry = models.CalculationEntry(
                    calculation_sheet_id=current_sheet.id,
                    section_number=entry_data['section_number'],
                    estimated_quantity=entry_data['estimated_quantity'],
                    quantity_submitted=entry_data['quantity_submitted'],
                    notes=entry_data.get('notes', '')
                )
                db.add(new_entry)
                entries_created += 1
            
            # Save the calculation sheet Excel file to all related contract item folders
            files_saved_count = save_calculation_sheet_to_item_folders(
                file_path,
                sheet_data['entries'],
                db
            )
            
            # Count as imported (whether new or updated)
            total_sheets_imported += 1
            total_entries_imported += entries_created
            
            action = "updated" if existing_sheet else "imported"
            logger.info(f"Successfully {action} calculation sheet {file_path.name} with {entries_created} entries (source: {source_file_path}). Saved to {files_saved_count} item folder(s).")
            
        except Exception as e:
            error_msg = f"{file_path.name} - Error processing file: {str(e)}"
            logger.error(error_msg)
            all_errors.append(error_msg)
            continue
    
    # Commit all changes
    db.commit()

@router.post("/import-calculation-sheets/", response_model=schemas.CalculationImportResponse)
async def import_calculation_sheets(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    Import multiple calculation sheet Excel files (uploaded via form)
    Files are saved to the uploads directory and the path is automatically saved as source_file_path
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    try:
        # Create uploads directory if it doesn't exist
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)
        
        excel_service = ExcelService()
        total_sheets_imported = 0
        total_entries_imported = 0
        all_errors = []
        
        for file in files:
            if not file.filename.endswith(('.xlsx', '.xls')):
                all_errors.append(f"{file.filename} - Not an Excel file")
                continue
            
            try:
                # Save uploaded file to uploads directory (permanent location)
                file_path = upload_dir / file.filename
                
                # Handle filename conflicts by adding a number suffix
                original_file_path = file_path
                counter = 1
                while file_path.exists():
                    stem = original_file_path.stem
                    suffix = original_file_path.suffix
                    file_path = upload_dir / f"{stem}_{counter}{suffix}"
                    counter += 1
                
                with open(file_path, "wb") as buffer:
                    content = await file.read()
                    buffer.write(content)
                
                # Get the absolute path to save as source_file_path
                source_file_path = str(file_path.absolute())
                
                # Process the calculation sheet
                sheet_data = excel_service.read_calculation_sheet_data(str(file_path))
                
                # Check if calculation sheet already exists (by calculation_sheet_no and drawing_no)
                existing_sheet = db.query(models.CalculationSheet).filter(
                    models.CalculationSheet.calculation_sheet_no == sheet_data['calculation_sheet_no'],
                    models.CalculationSheet.drawing_no == sheet_data['drawing_no']
                ).first()
                
                if existing_sheet:
                    # Update existing calculation sheet with new data
                    logger.info(f"Updating existing calculation sheet: {file.filename} - Sheet No: {sheet_data['calculation_sheet_no']}, Drawing No: {sheet_data['drawing_no']}")
                    
                    # Update the existing sheet with new data
                    existing_sheet.file_name = file.filename
                    existing_sheet.description = sheet_data['description']
                    existing_sheet.source_file_path = source_file_path  # Save the upload directory path
                    
                    # Delete existing calculation entries for this sheet
                    db.query(models.CalculationEntry).filter(
                        models.CalculationEntry.calculation_sheet_id == existing_sheet.id
                    ).delete()
                    
                    current_sheet = existing_sheet
                else:
                    # Create new calculation sheet record
                    logger.info(f"Creating new calculation sheet: {file.filename} - Sheet No: {sheet_data['calculation_sheet_no']}, Drawing No: {sheet_data['drawing_no']}")
                    
                    new_sheet = models.CalculationSheet(
                        file_name=file.filename,
                        calculation_sheet_no=sheet_data['calculation_sheet_no'],
                        drawing_no=sheet_data['drawing_no'],
                        description=sheet_data['description'],
                        source_file_path=source_file_path  # Save the upload directory path
                    )
                    
                    db.add(new_sheet)
                    db.flush()  # Get the ID without committing
                    current_sheet = new_sheet
                
                # Create calculation entries (for both new and updated sheets)
                entries_created = 0
                for entry_data in sheet_data['entries']:
                    new_entry = models.CalculationEntry(
                        calculation_sheet_id=current_sheet.id,
                        section_number=entry_data['section_number'],
                        estimated_quantity=entry_data['estimated_quantity'],
                        quantity_submitted=entry_data['quantity_submitted'],
                        notes=entry_data.get('notes', '')
                    )
                    db.add(new_entry)
                    entries_created += 1
                
                # Save the calculation sheet Excel file to all related contract item folders
                files_saved_count = save_calculation_sheet_to_item_folders(
                    file_path,
                    sheet_data['entries'],
                    db
                )
                
                # Count as imported (whether new or updated)
                total_sheets_imported += 1
                total_entries_imported += entries_created
                
                action = "updated" if existing_sheet else "imported"
                logger.info(f"Successfully {action} calculation sheet {file.filename} with {entries_created} entries (saved to: {source_file_path}). Saved to {files_saved_count} item folder(s).")
                
            except Exception as e:
                error_msg = f"{file.filename} - Error processing file: {str(e)}"
                logger.error(error_msg)
                all_errors.append(error_msg)
                continue
        
        # Commit all changes
        db.commit()
        
        # Create import log
        log = models.ImportLog(
            file_name=f"Calculation Sheets Import ({len(files)} files)",
            file_path="Multiple files",
            status="success" if not all_errors else "partial" if total_sheets_imported > 0 else "error",
            error_message="; ".join(all_errors) if all_errors else None,
            items_processed=len(files),
            items_updated=total_sheets_imported
        )
        db.add(log)
        db.commit()
        
        success_message = f"Successfully processed {total_sheets_imported} calculation sheets with {total_entries_imported} entries (updated existing sheets and added new ones as needed)"
        
        return schemas.CalculationImportResponse(
            success=len(all_errors) == 0,
            message=success_message,
            files_processed=len(files),
            sheets_imported=total_sheets_imported,
            entries_imported=total_entries_imported,
            errors=all_errors
        )
    except Exception as e:
        db.rollback()
        error_msg = f"Error importing calculation sheets: {str(e)}"
        logger.error(error_msg)
        return schemas.CalculationImportResponse(
            success=False,
            message=error_msg,
            files_processed=len(files) if files else 0,
            sheets_imported=0,
            entries_imported=0,
            errors=[error_msg]
        )
