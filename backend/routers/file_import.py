from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from sqlalchemy.orm import Session
from typing import List
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
        updated_count = 0
        
        for item_data in items:
            print("_________________", item_data)
            try:
                # Check if item already exists by section_number
                existing_item = db.query(models.BOQItem).filter(
                    models.BOQItem.section_number == item_data["section_number"]
                ).first()
                
                if existing_item:
                    # Update existing item
                    for key, value in item_data.items():
                        if hasattr(existing_item, key):
                            setattr(existing_item, key, value)
                    updated_count += 1
                else:
                    # Create new item
                    new_item = models.BOQItem(**item_data)
                    db.add(new_item)
                    imported_count += 1
                    
            except Exception as e:
                errors.append(f"Error processing item {item_data.get('section_number', 'Unknown')}: {str(e)}")
        
        # Commit changes
        db.commit()
        
        # Create import log
        log = models.ImportLog(
            file_name=file.filename,
            file_path=str(file_path),
            status="success" if not errors else "partial" if imported_count > 0 or updated_count > 0 else "error",
            error_message="; ".join(errors) if errors else None,
            items_processed=len(items),
            items_updated=imported_count + updated_count
        )
        db.add(log)
        db.commit()
        
        return schemas.ImportResponse(
            success=True,
            message=f"File processed successfully. {imported_count} items imported, {updated_count} items updated.",
            files_processed=1,
            items_updated=imported_count + updated_count,
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
                updated_count = 0
                
                for item_data in items:
                    try:
                        # Check if item already exists by section_number
                        existing_item = db.query(models.BOQItem).filter(
                            models.BOQItem.section_number == item_data["section_number"]
                        ).first()
                        
                        if existing_item:
                            # Update existing item
                            for key, value in item_data.items():
                                if hasattr(existing_item, key):
                                    setattr(existing_item, key, value)
                            updated_count += 1
                        else:
                            # Create new item
                            new_item = models.BOQItem(**item_data)
                            db.add(new_item)
                            imported_count += 1
                            
                    except Exception as e:
                        all_errors.append(f"{file_path.name} - Error processing item {item_data.get('section_number', 'Unknown')}: {str(e)}")
                
                total_items_updated += imported_count + updated_count
                
                # Create import log for this file
                log = models.ImportLog(
                    file_name=file_path.name,
                    file_path=str(file_path),
                    status="success" if not errors else "partial" if imported_count > 0 or updated_count > 0 else "error",
                    error_message="; ".join(errors) if errors else None,
                    items_processed=len(items),
                    items_updated=imported_count + updated_count
                )
                db.add(log)
                
        except Exception as e:
            error_msg = f"Error processing file {file_path.name}: {str(e)}"
            logger.error(error_msg)
            all_errors.append(error_msg)
    
    # Commit all changes
    db.commit()
    
    return schemas.ImportResponse(
        success=len(all_errors) == 0,
        message=f"Processed {len(excel_files)} files. {total_items_updated} items updated.",
        files_processed=len(excel_files),
        items_updated=total_items_updated,
        errors=all_errors
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

@router.post("/import-calculation-sheets/", response_model=schemas.CalculationImportResponse)
async def import_calculation_sheets(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    Import multiple calculation sheet Excel files
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    excel_service = ExcelService()
    total_sheets_imported = 0
    total_entries_imported = 0
    all_errors = []
    
    try:
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            for file in files:
                if not file.filename.endswith(('.xlsx', '.xls')):
                    all_errors.append(f"{file.filename} - Not an Excel file")
                    continue
                
                try:
                    # Save uploaded file to temporary directory
                    file_path = temp_path / file.filename
                    with open(file_path, "wb") as buffer:
                        content = await file.read()
                        buffer.write(content)
                    
                    # Process the calculation sheet
                    sheet_data = excel_service.read_calculation_sheet_data(str(file_path))
                    
                    # Check if calculation sheet already exists (by calculation_sheet_no and drawing_no)
                    existing_sheet = db.query(models.CalculationSheet).filter(
                        models.CalculationSheet.calculation_sheet_no == sheet_data['calculation_sheet_no'],
                        models.CalculationSheet.drawing_no == sheet_data['drawing_no']
                    ).first()
                    
                    if existing_sheet:
                        logger.info(f"Skipping duplicate calculation sheet: {file.filename} - Sheet No: {sheet_data['calculation_sheet_no']}, Drawing No: {sheet_data['drawing_no']} already exists")
                        all_errors.append(f"{file.filename} - Skipped: Calculation Sheet No '{sheet_data['calculation_sheet_no']}' with Drawing No '{sheet_data['drawing_no']}' already exists")
                        continue
                    
                    # Create calculation sheet record
                    new_sheet = models.CalculationSheet(
                        file_name=file.filename,
                        calculation_sheet_no=sheet_data['calculation_sheet_no'],
                        drawing_no=sheet_data['drawing_no'],
                        description=sheet_data['description']
                    )
                    
                    db.add(new_sheet)
                    db.flush()  # Get the ID without committing
                    
                    # Create calculation entries
                    entries_created = 0
                    for entry_data in sheet_data['entries']:
                        new_entry = models.CalculationEntry(
                            calculation_sheet_id=new_sheet.id,
                            section_number=entry_data['section_number'],
                            estimated_quantity=entry_data['estimated_quantity'],
                            quantity_submitted=entry_data['quantity_submitted']
                        )
                        db.add(new_entry)
                        entries_created += 1
                    
                    total_sheets_imported += 1
                    total_entries_imported += entries_created
                    
                    logger.info(f"Successfully imported calculation sheet {file.filename} with {entries_created} entries")
                    
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
        
        # Count skipped files (duplicates)
        skipped_count = len([error for error in all_errors if "Skipped:" in error])
        
        success_message = f"Successfully imported {total_sheets_imported} calculation sheets with {total_entries_imported} entries"
        if skipped_count > 0:
            success_message += f". Skipped {skipped_count} duplicate sheets."
        
        return schemas.CalculationImportResponse(
            success=len([error for error in all_errors if "Skipped:" not in error]) == 0,
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
            files_processed=len(files),
            sheets_imported=0,
            entries_imported=0,
            errors=[error_msg]
        )
