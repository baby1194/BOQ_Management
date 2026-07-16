from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Optional
import json
from pydantic import BaseModel
import pandas as pd
import os
from pathlib import Path
import logging
import tempfile
import shutil

from database.database import get_db, get_system_db, get_project_id, get_project_upload_dir, get_project_export_dir
from models import models
from schemas import schemas
from services.excel_service import ExcelService
from services.calculation_sheet_sync import (
    CalcSheetPushResult,
    finalize_calculation_sheet_changes,
    merge_push_results,
    push_calculation_sheet_to_concentration_entries,
)
from services.non_boq_service import register_non_boq_items_from_calculation_entries
from services.auth_service import get_current_user_from_cookie, verify_password
from fatina_paths import (
    FATINA_BASE_DIR,
    fatina_calculation_sheet_dir,
    sanitize_folder_name,
    is_upload_copy_path,
    primary_fatina_source_path,
    resolve_original_source_path,
)

router = APIRouter(prefix="/file-import", tags=["file-import"])

# Response model for create concentration sheets
class CreateConcentrationSheetsResponse(BaseModel):
    success: bool
    message: str
    created_count: int

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def discover_calculation_sheet_xlsx_files(path_str: str) -> List[str]:
    """Return absolute paths to .xlsx files under a folder (recursive) or a single file."""
    path = Path(path_str.strip())
    if not path.exists():
        raise HTTPException(status_code=400, detail="Path does not exist")
    if path.is_file():
        if path.suffix.lower() != ".xlsx":
            raise HTTPException(status_code=400, detail="File must be an .xlsx file")
        return [str(path.resolve())]
    if path.is_dir():
        return sorted(str(f.resolve()) for f in path.rglob("*.xlsx") if f.is_file())
    raise HTTPException(status_code=400, detail="Invalid path")


def import_calculation_sheet_from_disk(
    file_path: Path,
    db: Session,
    excel_service: ExcelService,
) -> tuple[int, int, bool, CalcSheetPushResult]:
    """
    Import or update one calculation sheet from a file on disk.
    Returns (entries_created, fatina_folders_saved, was_existing_update, push_result).
    """
    sheet_data = excel_service.read_calculation_sheet_data(str(file_path))
    source_file_path = str(file_path.resolve())

    existing_sheet = db.query(models.CalculationSheet).filter(
        models.CalculationSheet.calculation_sheet_no == sheet_data["calculation_sheet_no"],
    ).first()

    if existing_sheet:
        logger.info(
            f"Updating existing calculation sheet: {file_path.name} - "
            f"Sheet No: {sheet_data['calculation_sheet_no']}, Drawing No: {sheet_data['drawing_no']}"
        )
        previous_calculation_sheet_no = existing_sheet.calculation_sheet_no
        existing_sheet.file_name = file_path.name
        existing_sheet.calculation_sheet_no = sheet_data["calculation_sheet_no"]
        existing_sheet.drawing_no = sheet_data["drawing_no"]
        existing_sheet.description = sheet_data["description"]
        existing_sheet.source_file_path = source_file_path
        db.query(models.CalculationEntry).filter(
            models.CalculationEntry.calculation_sheet_id == existing_sheet.id
        ).delete()
        current_sheet = existing_sheet
        was_existing = True
    else:
        previous_calculation_sheet_no = None
        logger.info(
            f"Creating new calculation sheet: {file_path.name} - "
            f"Sheet No: {sheet_data['calculation_sheet_no']}, Drawing No: {sheet_data['drawing_no']}"
        )
        new_sheet = models.CalculationSheet(
            file_name=file_path.name,
            calculation_sheet_no=sheet_data["calculation_sheet_no"],
            drawing_no=sheet_data["drawing_no"],
            description=sheet_data["description"],
            source_file_path=source_file_path,
        )
        db.add(new_sheet)
        db.flush()
        current_sheet = new_sheet
        was_existing = False

    entries_created = 0
    for entry_data in sheet_data["entries"]:
        db.add(
            models.CalculationEntry(
                calculation_sheet_id=current_sheet.id,
                section_number=entry_data["section_number"],
                current_invoice_id=entry_data.get("current_invoice_id"),
                estimated_quantity=entry_data["estimated_quantity"],
                quantity_submitted=entry_data["quantity_submitted"],
                submission_breakdown=entry_data.get("submission_breakdown"),
                notes=entry_data.get("notes", ""),
            )
        )
        entries_created += 1

    register_non_boq_items_from_calculation_entries(db, sheet_data["entries"])

    push_result = push_calculation_sheet_to_concentration_entries(
        db,
        current_sheet,
        lookup_calculation_sheet_no=previous_calculation_sheet_no,
    )

    files_saved_count = save_calculation_sheet_to_item_folders(
        file_path,
        sheet_data["entries"],
        db,
        calculation_sheet_no=sheet_data["calculation_sheet_no"],
        original_filename=file_path.name,
    )

    action = "updated" if was_existing else "imported"
    logger.info(
        f"Successfully {action} calculation sheet {file_path.name} with {entries_created} entries "
        f"(source: {source_file_path}). Saved to {files_saved_count} item folder(s)."
    )
    return entries_created, files_saved_count, was_existing, push_result


def save_calculation_sheet_to_item_folders(
    source_file_path: Path,
    calculation_entries: List[Dict],
    db: Session,
    calculation_sheet_no: str,
    original_filename: str = None
) -> int:
    """
    Save calculation sheet Excel file to all contract item folders related to the calculation sheet.
    Each file is stored under C:/Fatina/{section_number}/{calculation_sheet_no}/.
    
    Args:
        source_file_path: Path to the source Excel file
        calculation_entries: List of calculation entries with section_number
        db: Database session
        original_filename: Optional original filename to use when saving (preserves original name)
        
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
        
        if not calculation_sheet_no or not str(calculation_sheet_no).strip():
            logger.warning(
                f"No calculation sheet number for file: {source_file_path}"
            )
            return 0

        sheet_no = str(calculation_sheet_no).strip()
        filename_to_use = original_filename if original_filename else source_file_path.name
        
        files_saved = 0
        
        # Save the file to each related item's folder under a calculation-sheet subfolder
        for boq_item in matching_boq_items:
            if not boq_item.section_number:
                continue
                
            folder_path = fatina_calculation_sheet_dir(
                str(boq_item.section_number), sheet_no
            )
            
            try:
                folder_path.mkdir(parents=True, exist_ok=True)
                
                destination_file = folder_path / filename_to_use
                shutil.copy2(source_file_path, destination_file)
                files_saved += 1
                logger.info(f"Saved calculation sheet to folder: {destination_file}")
                
            except PermissionError as e:
                logger.error(f"Permission denied saving file to folder {folder_path}: {str(e)}")
            except Exception as e:
                logger.error(f"Error saving file to folder {folder_path}: {str(e)}")
        
        logger.info(f"Saved calculation sheet {filename_to_use} to {files_saved} item folder(s)")
        return files_saved
        
    except Exception as e:
        logger.error(f"Error in save_calculation_sheet_to_item_folders: {str(e)}")
        return 0


def copy_calculation_sheets_to_item_folder(
    db: Session,
    section_number: str,
    skip_calc_sheet_nos: set[str] | None = None,
) -> int:
    """
    Copy all calculation sheet files related to the given section_number to the item folder.
    Used when exporting concentration sheets so the destination folder has both the
    concentration sheet and its calculation sheets.

    Section folders under FATINA are created only when at least one file is copied, so
    empty section directories are not left behind when there is nothing to copy.

    Args:
        db: Database session
        section_number: BOQ item section number (folder name)

    Returns:
        Number of calculation sheet files copied
    """
    if not section_number or not str(section_number).strip():
        return 0
    try:
        section_number = str(section_number).strip()

        # Find calculation sheet IDs that have at least one entry with this section_number
        sheet_ids = (
            db.query(models.CalculationEntry.calculation_sheet_id)
            .filter(models.CalculationEntry.section_number == section_number)
            .distinct()
            .all()
        )
        sheet_ids = [sid[0] for sid in sheet_ids]
        if not sheet_ids:
            return 0

        sheets = db.query(models.CalculationSheet).filter(
            models.CalculationSheet.id.in_(sheet_ids),
            models.CalculationSheet.source_file_path.isnot(None),
        ).all()

        copied = 0
        for sheet in sheets:
            src = Path(sheet.source_file_path) if isinstance(sheet.source_file_path, str) else sheet.source_file_path
            if not src.exists():
                logger.warning(f"Calculation sheet source not found: {src}")
                continue
            if not sheet.calculation_sheet_no:
                logger.warning(
                    f"Skipping Fatina copy for sheet id {sheet.id}: no calculation_sheet_no"
                )
                continue
            if skip_calc_sheet_nos and sheet.calculation_sheet_no in skip_calc_sheet_nos:
                logger.info(
                    "Skipping Fatina calc sheet folder for %s (selective export)",
                    sheet.calculation_sheet_no,
                )
                continue
            FATINA_BASE_DIR.mkdir(parents=True, exist_ok=True)
            dest_dir = fatina_calculation_sheet_dir(
                section_number, sheet.calculation_sheet_no
            )
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / (sheet.file_name or src.name)
            try:
                shutil.copy2(src, dest)
                copied += 1
                logger.info(f"Copied calculation sheet to folder: {dest}")
            except (PermissionError, OSError) as e:
                logger.error(f"Error copying calculation sheet to {dest_dir}: {e}")
        return copied
    except Exception as e:
        logger.error(f"Error in copy_calculation_sheets_to_item_folder: {e}")
        return 0


def copy_concentration_entry_drawing_files_to_fatina(
    db: Session,
    section_number: str,
    entries: List[models.ConcentrationEntry] | None = None,
    sheet_id: int | None = None,
    skip_calc_sheet_nos: set[str] | None = None,
) -> int:
    """Copy drawing files attached to concentration entries into Fatina calc sheet folders."""
    from fatina_paths import copy_files_to_calc_sheet_dir

    if not section_number or not str(section_number).strip():
        return 0

    section_number = str(section_number).strip()
    if entries is None and sheet_id is not None:
        entries = (
            db.query(models.ConcentrationEntry)
            .filter(models.ConcentrationEntry.concentration_sheet_id == sheet_id)
            .all()
        )
    if not entries:
        return 0

    copied = 0
    for entry in entries:
        paths = entry.drawing_files
        if isinstance(paths, str):
            import json
            try:
                paths = json.loads(paths)
            except json.JSONDecodeError:
                paths = []
        if not paths or not entry.calculation_sheet_no:
            continue
        if skip_calc_sheet_nos and entry.calculation_sheet_no in skip_calc_sheet_nos:
            continue
        copied += copy_files_to_calc_sheet_dir(
            section_number,
            entry.calculation_sheet_no,
            paths,
        )
    return copied


async def _require_valid_system_password(
    request: Request,
    system_password: Optional[str],
    system_db: Session,
) -> None:
    if not system_password or not str(system_password).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="System password is required",
        )
    current_user = await get_current_user_from_cookie(request, system_db)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    if not verify_password(system_password, current_user.system_password):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid system password. Please check your system password in the profile page.",
        )


@router.post("/upload/", response_model=schemas.ImportResponse)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    system_password: str = Form(...),
    db: Session = Depends(get_db),
    system_db: Session = Depends(get_system_db),
    project_id: str = Depends(get_project_id),
):
    """
    Upload and import a single Excel file
    """
    await _require_valid_system_password(request, system_password, system_db)
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files are supported")
    
    try:
        # Save uploaded file
        upload_dir = get_project_upload_dir(project_id)
        file_path = upload_dir / file.filename
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Process the file
        excel_service = ExcelService(exports_dir=get_project_export_dir(project_id))
        items, errors = excel_service.process_excel_file(file_path)
        
        if not items:
            raise HTTPException(status_code=400, detail="No valid items found in file")
        
        # Import items to database
        imported_count = 0
        skipped_count = 0
        max_order = db.query(func.max(models.BOQItem.display_order)).scalar()
        next_display_order = (max_order if max_order is not None else -1)

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
                    next_display_order += 1
                    row = dict(item_data)
                    row["display_order"] = next_display_order
                    # Create new item - serial_number will be automatically set to id by the event listener
                    new_item = models.BOQItem(**row)
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
    http_request: Request,
    request: schemas.ImportRequest,
    db: Session = Depends(get_db),
    system_db: Session = Depends(get_system_db),
    project_id: str = Depends(get_project_id),
):
    """
    Import all Excel files from a folder
    """
    await _require_valid_system_password(http_request, request.system_password, system_db)
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
    
    excel_service = ExcelService(exports_dir=get_project_export_dir(project_id))
    total_items_updated = 0
    all_errors = []
    max_order = db.query(func.max(models.BOQItem.display_order)).scalar()
    next_display_order = max_order if max_order is not None else -1

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
                            next_display_order += 1
                            row = dict(item_data)
                            row["display_order"] = next_display_order
                            # Create new item - serial_number will be automatically set to id by the event listener
                            new_item = models.BOQItem(**row)
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

@router.post("/list-calculation-sheet-files/", response_model=schemas.CalculationSheetsListResponse)
async def list_calculation_sheet_files(request: schemas.CalculationSheetsPathRequest):
    """List .xlsx calculation sheet files from a folder path or single file path."""
    files = discover_calculation_sheet_xlsx_files(request.path)
    if not files:
        raise HTTPException(status_code=400, detail="No .xlsx files found at path")
    return schemas.CalculationSheetsListResponse(files=files)


@router.post("/import-calculation-sheets-from-paths/", response_model=schemas.CalculationImportResponse)
async def import_calculation_sheets_from_paths(
    request: schemas.CalculationSheetsImportPathsRequest,
    db: Session = Depends(get_db),
    project_id: str = Depends(get_project_id),
):
    """Import calculation sheets directly from absolute file paths on disk."""
    excel_service = ExcelService(exports_dir=get_project_export_dir(project_id))
    total_sheets_imported = 0
    total_entries_imported = 0
    all_errors = []
    push_results: list[CalcSheetPushResult] = []

    for path_str in request.file_paths:
        file_path = Path(path_str)
        if not file_path.is_file():
            all_errors.append(f"{path_str} - File not found")
            continue
        if file_path.suffix.lower() != ".xlsx":
            all_errors.append(f"{file_path.name} - Not an .xlsx file")
            continue
        try:
            entries_created, _, _, push_result = import_calculation_sheet_from_disk(
                file_path, db, excel_service
            )
            total_sheets_imported += 1
            total_entries_imported += entries_created
            push_results.append(push_result)
        except Exception as e:
            error_msg = f"{file_path.name} - Error processing file: {str(e)}"
            logger.error(error_msg)
            all_errors.append(error_msg)

    db.commit()

    log = models.ImportLog(
        file_name=f"Calculation Sheets Import ({len(request.file_paths)} files)",
        file_path="Disk paths",
        status="success" if not all_errors else "partial" if total_sheets_imported > 0 else "error",
        error_message="; ".join(all_errors) if all_errors else None,
        items_processed=len(request.file_paths),
        items_updated=total_sheets_imported,
    )
    db.add(log)
    db.commit()

    success_message = (
        f"Successfully processed {total_sheets_imported} calculation sheets "
        f"with {total_entries_imported} entries"
    )
    if total_sheets_imported > 0:
        success_message = finalize_calculation_sheet_changes(
            db, project_id, success_message, merge_push_results(push_results)
        )
    return schemas.CalculationImportResponse(
        success=len(all_errors) == 0,
        message=success_message,
        files_processed=len(request.file_paths),
        sheets_imported=total_sheets_imported,
        entries_imported=total_entries_imported,
        errors=all_errors,
    )


@router.post("/import-calculation-sheets-from-folder/", response_model=schemas.CalculationImportResponse)
async def import_calculation_sheets_from_folder(
    request: schemas.ImportRequest,
    db: Session = Depends(get_db),
    project_id: str = Depends(get_project_id),
):
    """
    Import calculation sheet Excel files from a folder path
    Automatically captures and saves the source file paths
    """
    excel_files = discover_calculation_sheet_xlsx_files(request.folder_path)
    if not excel_files:
        raise HTTPException(status_code=400, detail="No .xlsx files found in folder")

    excel_service = ExcelService(exports_dir=get_project_export_dir(project_id))
    total_sheets_imported = 0
    total_entries_imported = 0
    all_errors = []
    push_results: list[CalcSheetPushResult] = []

    for path_str in excel_files:
        file_path = Path(path_str)
        try:
            entries_created, _, _, push_result = import_calculation_sheet_from_disk(
                file_path, db, excel_service
            )
            total_sheets_imported += 1
            total_entries_imported += entries_created
            push_results.append(push_result)
        except Exception as e:
            error_msg = f"{file_path.name} - Error processing file: {str(e)}"
            logger.error(error_msg)
            all_errors.append(error_msg)

    db.commit()

    success_message = (
        f"Successfully processed {total_sheets_imported} calculation sheets "
        f"with {total_entries_imported} entries"
    )
    if total_sheets_imported > 0:
        success_message = finalize_calculation_sheet_changes(
            db, project_id, success_message, merge_push_results(push_results)
        )

    return schemas.CalculationImportResponse(
        success=len(all_errors) == 0,
        message=(
            success_message
        ),
        files_processed=len(excel_files),
        sheets_imported=total_sheets_imported,
        entries_imported=total_entries_imported,
        errors=all_errors,
    )

@router.post("/import-calculation-sheets/", response_model=schemas.CalculationImportResponse)
async def import_calculation_sheets(
    files: List[UploadFile] = File(...),
    source_folder_path: Optional[str] = Form(None),
    file_relative_paths: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    project_id: str = Depends(get_project_id),
):
    """
    Import multiple calculation sheet Excel files (uploaded via form).
    Files are processed from a temporary uploads copy. When source_folder_path is provided,
    source_file_path stores the matching original file on disk instead of the upload copy.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    try:
        upload_dir = get_project_upload_dir(project_id)
        excel_service = ExcelService(exports_dir=get_project_export_dir(project_id))
        total_sheets_imported = 0
        total_entries_imported = 0
        all_errors = []
        push_results: list[CalcSheetPushResult] = []
        relative_paths_map: Dict[str, str] = {}
        if file_relative_paths:
            try:
                relative_paths_map = json.loads(file_relative_paths)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid file_relative_paths JSON")
        
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
                
                source_file_path = resolve_original_source_path(
                    file.filename,
                    file_path,
                    source_folder_path=source_folder_path,
                    relative_path=relative_paths_map.get(file.filename),
                )
                
                # Process the calculation sheet
                sheet_data = excel_service.read_calculation_sheet_data(str(file_path))
                
                # Check if calculation sheet already exists (by calculation_sheet_no only)
                existing_sheet = db.query(models.CalculationSheet).filter(
                    models.CalculationSheet.calculation_sheet_no == sheet_data['calculation_sheet_no'],
                ).first()
                
                previous_calculation_sheet_no = None
                if existing_sheet:
                    # Update existing calculation sheet with new data
                    logger.info(f"Updating existing calculation sheet: {file.filename} - Sheet No: {sheet_data['calculation_sheet_no']}, Drawing No: {sheet_data['drawing_no']}")
                    
                    previous_calculation_sheet_no = existing_sheet.calculation_sheet_no
                    existing_sheet.file_name = file.filename
                    existing_sheet.calculation_sheet_no = sheet_data['calculation_sheet_no']
                    existing_sheet.drawing_no = sheet_data['drawing_no']
                    existing_sheet.description = sheet_data['description']
                    keep_existing_source = (
                        existing_sheet.source_file_path
                        and not is_upload_copy_path(existing_sheet.source_file_path, upload_dir)
                        and Path(existing_sheet.source_file_path).is_file()
                    )
                    if not keep_existing_source:
                        existing_sheet.source_file_path = source_file_path
                    
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
                        current_invoice_id=entry_data.get('current_invoice_id'),
                        estimated_quantity=entry_data['estimated_quantity'],
                        quantity_submitted=entry_data['quantity_submitted'],
                        submission_breakdown=entry_data.get('submission_breakdown'),
                        notes=entry_data.get('notes', '')
                    )
                    db.add(new_entry)
                    entries_created += 1

                register_non_boq_items_from_calculation_entries(
                    db, sheet_data["entries"]
                )

                push_result = push_calculation_sheet_to_concentration_entries(
                    db,
                    current_sheet,
                    lookup_calculation_sheet_no=previous_calculation_sheet_no,
                )
                push_results.append(push_result)
                
                # Save the calculation sheet Excel file to all related contract item folders
                # Use the original filename (file.filename) to preserve the original name even if it was renamed during upload
                files_saved_count = save_calculation_sheet_to_item_folders(
                    file_path,
                    sheet_data['entries'],
                    db,
                    calculation_sheet_no=sheet_data['calculation_sheet_no'],
                    original_filename=file.filename
                )

                # Browsers cannot send absolute disk paths on upload; use the C:/Fatina copy instead of uploads.
                section_numbers = {
                    str(entry_data['section_number']).strip()
                    for entry_data in sheet_data['entries']
                    if entry_data.get('section_number') and str(entry_data['section_number']).strip()
                }
                fatina_source = primary_fatina_source_path(
                    file.filename,
                    section_numbers,
                    sheet_data['calculation_sheet_no'],
                )
                if fatina_source and is_upload_copy_path(source_file_path, upload_dir):
                    source_file_path = fatina_source
                    current_sheet.source_file_path = fatina_source
                
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
        if total_sheets_imported > 0:
            success_message = finalize_calculation_sheet_changes(
                db, project_id, success_message, merge_push_results(push_results)
            )
        
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
