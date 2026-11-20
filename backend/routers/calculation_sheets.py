from fastapi import APIRouter, HTTPException, Depends, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from pathlib import Path
import logging
import os
import platform
import subprocess
import threading
from database.database import get_db, get_project_id, get_project_upload_dir, get_project_export_dir
from fatina_paths import resolve_calculation_sheet_open_path
from models import models
from schemas import schemas
from services.calculation_sheet_sync import (
    CalcSheetPushResult,
    finalize_calculation_sheet_changes,
    merge_push_results,
    perform_sync_all_calculation_sheets,
    push_calculation_sheet_to_concentration_entries,
)
from services.sync_service import SyncService
from services.excel_service import ExcelService
from services.non_boq_service import (
    reconcile_missing_non_boq_items,
    register_non_boq_items_from_calculation_entries,
)
from services.subproject_calc_sync import (
    apply_subproject_calc_updates,
    capture_sheet_entries,
    delete_sheets_from_subprojects,
    find_subproject_sheet_copies,
    note_transferred_changes,
)
from services.pdf_service import PDFService
from utils.calc_sheet_freshness import remember_source_modified_at, sheet_freshness
from utils.concentration_utils import (
    entry_cumulative_submitted,
    sync_calc_entry_to_concentration,
)

# Set up logger
logger = logging.getLogger(__name__)


def _entry_columns_dict(
    body: Optional[schemas.AutoExportColumnsRequest] = None,
    entry_columns: Optional[schemas.ConcentrationEntryExportRequest] = None,
):
    cols = entry_columns
    if cols is None and body is not None:
        cols = body.entry_columns
    return cols.dict() if cols is not None else None


def open_file_in_default_application(file_path: str) -> None:
    """Open a file with the OS default application."""
    if platform.system() == "Windows":
        os.startfile(file_path)
    elif platform.system() == "Darwin":
        subprocess.call(["open", file_path])
    else:
        subprocess.call(["xdg-open", file_path])


def refresh_calculation_sheet_from_disk(
    sheet: models.CalculationSheet,
    excel_service: ExcelService,
    db: Session,
    removed_notices: Optional[List[str]] = None,
    subproject_updates: Optional[List[dict]] = None,
) -> tuple[int, str | None, CalcSheetPushResult]:
    """
    Reread one calculation sheet from its source file path.
    Returns (entries_refreshed, error_message_or_none, push_result).
    """
    label = f"{sheet.calculation_sheet_no} / {sheet.drawing_no}"
    if not sheet.source_file_path:
        return 0, f"{label} - No source file path saved", CalcSheetPushResult()

    file_path = Path(sheet.source_file_path)
    if not file_path.is_file():
        return 0, f"{label} - Source file not found: {sheet.source_file_path}", CalcSheetPushResult()

    try:
        logger.info("Reading calculation sheet %s", file_path)
        sheet_data = excel_service.read_calculation_sheet_data(str(file_path))
        previous_calculation_sheet_no = sheet.calculation_sheet_no
        before_entries = capture_sheet_entries(db, sheet.id)
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
                    invoice_description=entry_data.get("invoice_description"),
                    item_description=entry_data.get("item_description"),
                    estimated_quantity=entry_data["estimated_quantity"],
                    quantity_submitted=entry_data["quantity_submitted"],
                    submission_breakdown=entry_data.get("submission_breakdown"),
                    notes=entry_data.get("notes", ""),
                    unit_price=entry_data.get("unit_price"),
                    unit=entry_data.get("unit"),
                    system=entry_data.get("system"),
                )
            )
            entries_refreshed += 1

        register_non_boq_items_from_calculation_entries(db, sheet_data["entries"])
        note_transferred_changes(
            db,
            sheet_data["calculation_sheet_no"],
            previous_calculation_sheet_no,
            before_entries,
            sheet_data["entries"],
            subproject_updates,
        )
        notices, _changed = reconcile_missing_non_boq_items(db)
        if removed_notices is not None:
            for notice in notices:
                if notice not in removed_notices:
                    removed_notices.append(notice)

        push_result = push_calculation_sheet_to_concentration_entries(
            db,
            sheet,
            lookup_calculation_sheet_no=previous_calculation_sheet_no,
        )

        remember_source_modified_at(sheet, file_path)
        logger.info(f"Tracked calculation sheet {label} from {file_path}")
        return entries_refreshed, None, push_result
    except Exception as e:
        error_msg = f"{label} - {file_path.name}: {str(e)}"
        logger.error(error_msg)
        return 0, error_msg, CalcSheetPushResult()


router = APIRouter()
_PRINT_LOCK = threading.Lock()

def _concentration_sections_by_calc_sheet(db: Session) -> dict:
    """BOQ section numbers whose concentration sheet uses each calculation sheet."""
    rows = (
        db.query(
            models.ConcentrationEntry.calculation_sheet_no,
            models.BOQItem.section_number,
        )
        .join(
            models.ConcentrationSheet,
            models.ConcentrationEntry.concentration_sheet_id == models.ConcentrationSheet.id,
        )
        .join(
            models.BOQItem,
            models.ConcentrationSheet.boq_item_id == models.BOQItem.id,
        )
        .all()
    )
    found = {}
    for sheet_no, section in rows:
        number = str(sheet_no or "").strip()
        section_number = str(section or "").strip()
        if not number or not section_number:
            continue
        sections = found.setdefault(number, [])
        if section_number not in sections:
            sections.append(section_number)
    return found


@router.post("/print-pdfs")
def print_calculation_sheet_pdfs(body: dict, db: Session = Depends(get_db)):
    """Print the calculation sheets from the copies saved in Fatina and Fatina Invoice.

    Each PDF is made from the workbook in that folder, so a hide or delete saved
    there is what gets printed. The original calculation sheet is not read and
    is left unchanged. A folder without the workbook is left unchanged.

    This stays a normal function so FastAPI runs it on a worker thread. An async
    endpoint would read the workbooks on the event loop and freeze every other
    request until the print finished.
    """
    from fatina_paths import existing_calc_workbooks
    from services.sheet_print import print_saved_copy

    orientation = body.get("orientation") or "landscape"
    if orientation not in ("landscape", "portrait"):
        raise HTTPException(status_code=400, detail="orientation must be landscape or portrait")
    margin = float(body.get("margin_mm") or 10)
    if not _PRINT_LOCK.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail="A calculation-sheet print is already running. Wait for it to finish.",
        )
    try:
        sheets = (
            db.query(models.CalculationSheet)
            .order_by(models.CalculationSheet.calculation_sheet_no)
            .all()
        )
        sections_by_sheet = _concentration_sections_by_calc_sheet(db)
        jobs = [
            {
                "number": sheet.calculation_sheet_no,
                "file_name": sheet.file_name
                or (Path(sheet.source_file_path).name if sheet.source_file_path else ""),
                "sections": sections_by_sheet.get(
                    str(sheet.calculation_sheet_no or "").strip(), []
                ),
            }
            for sheet in sheets
        ]
        db.close()
        logger.info(
            "Printing %s calculation sheet(s) from the Fatina copies",
            len(jobs),
        )
        files = []
        errors = []
        for index, job in enumerate(jobs, start=1):
            number = job["number"] or "(no number)"
            section_list = ", ".join(job["sections"]) or "none"
            logger.info(
                "[%s/%s] %s file=%s concentration sections=%s",
                index,
                len(jobs),
                number,
                job["file_name"] or "missing",
                section_list,
            )
            if not job["file_name"]:
                message = f"{number}: no workbook name is stored"
                logger.error(message)
                errors.append(message)
                continue
            if not job["sections"]:
                message = (
                    f"{number}: not used by a concentration sheet, "
                    "so it has no Fatina folder"
                )
                logger.error(message)
                errors.append(message)
                continue
            copies = existing_calc_workbooks(
                job["sections"],
                job["number"],
                job["file_name"],
            )
            if not copies:
                message = (
                    f"{number}: the workbook is not in a Fatina or "
                    "Fatina Invoice calculation-sheet folder"
                )
                logger.error(message)
                errors.append(message)
                continue
            for workbook in copies:
                logger.info("Printing Fatina copy %s", workbook)
                try:
                    files.append(
                        print_saved_copy(
                            workbook,
                            orientation=orientation,
                            margin_mm=margin,
                        )
                    )
                except Exception as exc:
                    logger.exception("Print failed for %s", workbook)
                    errors.append(f"{number}: {workbook}: {type(exc).__name__}: {exc}")
        logger.info(
            "Print finished: %s pdf(s), %s failed",
            len(files),
            len(errors),
        )
        return {
            "count": len(files),
            "failed": len(errors),
            "files": files[:30],
            "errors": errors[:30],
        }
    finally:
        _PRINT_LOCK.release()


@router.get("/for-system")
def calculation_sheets_for_system(system: str, db: Session = Depends(get_db)):
    """Sheet ids that contain at least one BOQ section of this contract system."""
    from services.sheet_system_filter import load_sheet_ids_for_system

    return load_sheet_ids_for_system(db, system)


@router.get("/quantity-check")
async def check_calculation_quantities(db: Session = Depends(get_db)):
    """Compare calculated totals with detail quantities that have an invoice in the prior cell."""
    from services.quantity_check import mismatches_from_db

    rows = mismatches_from_db(db)
    return {"count": len(rows), "items": rows}


@router.post("/freshness", response_model=schemas.CalculationSheetFreshnessResponse)
def check_calculation_sheet_freshness(db: Session = Depends(get_db)):
    """List sheets whose file on this computer is newer than the copy in the project.

    Sheets that already match get their file date stored, so a later save is
    visible even if someone edits a comment in the system afterwards.
    """
    sheets = (
        db.query(models.CalculationSheet)
        .order_by(models.CalculationSheet.calculation_sheet_no)
        .all()
    )
    items = []
    sealed = False
    for sheet in sheets:
        item = sheet_freshness(sheet)
        if item is None:
            if sheet.source_modified_at is None and sheet.source_file_path:
                remember_source_modified_at(sheet)
                sealed = True
            continue
        items.append(item)
    if sealed:
        db.commit()
    return schemas.CalculationSheetFreshnessResponse(
        count=len(items),
        checked=len(sheets),
        items=items,
    )


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
        source_file_missing=sheet.source_file_missing,
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

@router.post("/open-source-file-by-no")
async def open_source_file_by_no(
    body: schemas.OpenSourceFileByNoRequest,
    db: Session = Depends(get_db),
    project_id: str = Depends(get_project_id),
):
    """Open a calculation sheet source file by its sheet number."""
    normalized_no = body.calculation_sheet_no.strip()
    if not normalized_no:
        raise HTTPException(status_code=400, detail="Calculation sheet number is required")

    sheet = (
        db.query(models.CalculationSheet)
        .filter(models.CalculationSheet.calculation_sheet_no == normalized_no)
        .first()
    )
    if not sheet:
        raise HTTPException(
            status_code=404,
            detail=f"Calculation sheet {normalized_no} not found",
        )

    upload_root = get_project_upload_dir(project_id)
    file_path = resolve_calculation_sheet_open_path(sheet, db, upload_root)
    if not file_path:
        raise HTTPException(
            status_code=400,
            detail="Source file path not set for this calculation sheet",
        )

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail=f"Source file not found at path: {file_path}",
        )

    try:
        open_file_in_default_application(file_path)
        return {"success": True, "message": f"Opening file: {file_path}"}
    except Exception as e:
        logger.error(f"Error opening file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error opening file: {str(e)}")


@router.post("/{sheet_id}/open-source-file")
async def open_source_file(
    sheet_id: int,
    db: Session = Depends(get_db),
    project_id: str = Depends(get_project_id),
):
    """
    Open the source Excel file in the default application (Windows)
    """
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
        open_file_in_default_application(file_path)
        return {"success": True, "message": f"Opening file: {file_path}"}
    except Exception as e:
        logger.error(f"Error opening file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error opening file: {str(e)}")

@router.post("/{sheet_id}/track", response_model=schemas.CalculationSheetsTrackResponse)
async def track_calculation_sheet(
    sheet_id: int,
    body: Optional[schemas.AutoExportColumnsRequest] = Body(None),
    db: Session = Depends(get_db),
    project_id: str = Depends(get_project_id),
    language: str = Query("en"),
):
    """Reread one calculation sheet from its saved source file path on disk."""
    sheet = db.query(models.CalculationSheet).filter(
        models.CalculationSheet.id == sheet_id
    ).first()
    if not sheet:
        raise HTTPException(status_code=404, detail="Calculation sheet not found")

    excel_service = ExcelService(exports_dir=get_project_export_dir(project_id))
    removed_notices: List[str] = []
    subproject_updates: List[dict] = []
    entries_refreshed, error, push_result = refresh_calculation_sheet_from_disk(
        sheet, excel_service, db, removed_notices, subproject_updates
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
    message = finalize_calculation_sheet_changes(
        db,
        project_id,
        message,
        push_result,
        language=language,
        entry_columns=_entry_columns_dict(body),
    )
    if removed_notices:
        message = f"{message} " + " ".join(removed_notices)
    return schemas.CalculationSheetsTrackResponse(
        success=True,
        message=message,
        sheets_updated=1,
        sheets_skipped=0,
        entries_updated=entries_refreshed,
        errors=[],
        subproject_updates=subproject_updates,
    )

@router.post("/subproject-copies", response_model=schemas.SubprojectSheetCopiesResponse)
async def subproject_calculation_sheet_copies(
    body: schemas.SubprojectSheetCopyRequest,
    db: Session = Depends(get_db),
    project_id: str = Depends(get_project_id),
):
    """Sheets with these numbers that also exist in a linked sub-project."""
    numbers = list(body.calculation_sheet_nos)
    if body.sheet_ids:
        sheets = (
            db.query(models.CalculationSheet)
            .filter(models.CalculationSheet.id.in_(body.sheet_ids))
            .all()
        )
        numbers.extend(sheet.calculation_sheet_no for sheet in sheets)
    return schemas.SubprojectSheetCopiesResponse(
        copies=find_subproject_sheet_copies(db, project_id, numbers)
    )


@router.post(
    "/apply-subproject-updates",
    response_model=schemas.ApplySubprojectCalcUpdatesResponse,
)
async def apply_subproject_calculation_updates(
    body: schemas.ApplySubprojectCalcUpdatesRequest,
    db: Session = Depends(get_db),
):
    """Copy confirmed quantity and price changes onto the sub-project sheets."""
    result = apply_subproject_calc_updates(
        db, [item.model_dump() for item in body.updates]
    )
    return schemas.ApplySubprojectCalcUpdatesResponse(**result)


@router.delete("/{sheet_id}")
async def delete_calculation_sheet(
    sheet_id: int,
    also_delete_subprojects: bool = Query(False),
    db: Session = Depends(get_db),
    project_id: str = Depends(get_project_id),
):
    """
    Delete a calculation sheet and all its entries, with automatic synchronization
    """
    sheet = db.query(models.CalculationSheet).filter(models.CalculationSheet.id == sheet_id).first()
    if not sheet:
        raise HTTPException(status_code=404, detail="Calculation sheet not found")

    sheet_no = sheet.calculation_sheet_no
    try:
        sync_service = SyncService(db)
        sync_result = sync_service.sync_calculation_sheet_deletion(sheet_id)

        if not sync_result["success"]:
            logger.warning(f"Sync failed during calculation sheet deletion: {sync_result['message']}")

        db.delete(sheet)
        db.commit()

        subproject_result = {"deleted": 0, "errors": [], "message": ""}
        if also_delete_subprojects:
            subproject_result = delete_sheets_from_subprojects(db, project_id, [sheet_no])

        message = "Calculation sheet deleted successfully"
        if sync_result["success"]:
            message += f". Synchronized: {sync_result['entries_deleted']} concentration entries deleted, {sync_result['boq_items_updated']} BOQ items updated"
        if subproject_result.get("message") and also_delete_subprojects:
            message += " " + subproject_result["message"]

        return {
            "message": message,
            "sync_result": sync_result,
            "subprojects_deleted": subproject_result.get("deleted", 0),
            "subproject_errors": subproject_result.get("errors", []),
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting calculation sheet: {str(e)}")

@router.post("/bulk-delete", response_model=schemas.BulkDeleteCalculationSheetsResponse)
async def bulk_delete_calculation_sheets(
    request: schemas.BulkDeleteCalculationSheetsRequest,
    db: Session = Depends(get_db),
    project_id: str = Depends(get_project_id),
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
        deleted_sheet_numbers = []
        
        # Process each sheet deletion
        for sheet_id in request.sheet_ids:
            try:
                sheet = db.query(models.CalculationSheet).filter(models.CalculationSheet.id == sheet_id).first()
                if not sheet:
                    errors.append(f"Sheet ID {sheet_id} not found")
                    continue
                sheet_no = sheet.calculation_sheet_no
                
                # Sync the deletion (this will handle concentration entries and BOQ items)
                sync_result = sync_service.sync_calculation_sheet_deletion(sheet_id)
                
                if not sync_result["success"]:
                    logger.warning(f"Sync failed during calculation sheet deletion {sheet_id}: {sync_result['message']}")
                    errors.append(f"Sync failed for sheet ID {sheet_id}: {sync_result['message']}")
                
                # Delete the calculation sheet
                db.delete(sheet)
                db.commit()
                
                sheets_deleted += 1
                deleted_sheet_numbers.append(sheet_no)
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

        subprojects_deleted = 0
        subproject_errors: List[str] = []
        if request.also_delete_subprojects and deleted_sheet_numbers:
            subproject_result = delete_sheets_from_subprojects(
                db, project_id, deleted_sheet_numbers
            )
            subprojects_deleted = subproject_result.get("deleted", 0)
            subproject_errors = subproject_result.get("errors", [])
            if subproject_result.get("message"):
                message += " " + subproject_result["message"]
        
        return {
            "success": sheets_deleted > 0,
            "message": message,
            "sheets_deleted": sheets_deleted,
            "total_entries_deleted": total_entries_deleted,
            "total_boq_items_updated": total_boq_items_updated,
            "errors": errors,
            "subprojects_deleted": subprojects_deleted,
            "subproject_errors": subproject_errors,
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

def _track_sheets(
    sheets: List[models.CalculationSheet],
    db: Session,
    project_id: str,
    language: str,
    entry_columns,
) -> schemas.CalculationSheetsTrackResponse:
    excel_service = ExcelService(exports_dir=get_project_export_dir(project_id))
    removed_notices: List[str] = []
    subproject_updates: List[dict] = []
    sheets_updated = 0
    sheets_skipped = 0
    entries_updated = 0
    errors: List[str] = []
    push_results: List[CalcSheetPushResult] = []

    for sheet in sheets:
        entries_refreshed, error, push_result = refresh_calculation_sheet_from_disk(
            sheet, excel_service, db, removed_notices, subproject_updates
        )
        if error:
            sheets_skipped += 1
            errors.append(error)
        else:
            sheets_updated += 1
            entries_updated += entries_refreshed
            push_results.append(push_result)

    db.commit()

    message = (
        f"Updated {sheets_updated} calculation sheet(s) "
        f"({entries_updated} entries refreshed from disk)"
    )
    if sheets_skipped:
        message += f". Skipped {sheets_skipped} sheet(s)."

    if sheets_updated > 0:
        message = finalize_calculation_sheet_changes(
            db,
            project_id,
            message,
            merge_push_results(push_results),
            language=language,
            entry_columns=entry_columns,
        )
    if removed_notices:
        message = f"{message} " + " ".join(removed_notices)

    return schemas.CalculationSheetsTrackResponse(
        success=sheets_updated > 0 or sheets_skipped == 0,
        message=message,
        sheets_updated=sheets_updated,
        sheets_skipped=sheets_skipped,
        entries_updated=entries_updated,
        errors=errors,
        subproject_updates=subproject_updates,
    )


@router.post("/track-selected", response_model=schemas.CalculationSheetsTrackResponse)
async def track_selected_calculation_sheets(
    body: schemas.TrackSelectedCalculationSheetsRequest,
    db: Session = Depends(get_db),
    project_id: str = Depends(get_project_id),
    language: str = Query("en"),
):
    """Reread only the listed calculation sheets from their files on disk."""
    sheets = (
        db.query(models.CalculationSheet)
        .filter(models.CalculationSheet.id.in_(body.sheet_ids))
        .all()
    )
    found = {sheet.id for sheet in sheets}
    missing = [sheet_id for sheet_id in body.sheet_ids if sheet_id not in found]
    result = _track_sheets(
        sheets,
        db,
        project_id,
        language,
        _entry_columns_dict(entry_columns=body.entry_columns),
    )
    if missing:
        result.errors = [
            f"Sheet ID {sheet_id} not found" for sheet_id in missing
        ] + result.errors
        result.sheets_skipped += len(missing)
    return result


@router.post("/track", response_model=schemas.CalculationSheetsTrackResponse)
async def track_calculation_sheets(
    body: Optional[schemas.AutoExportColumnsRequest] = Body(None),
    db: Session = Depends(get_db),
    project_id: str = Depends(get_project_id),
    language: str = Query("en"),
):
    """
    Reread all calculation sheets from their saved source file paths on disk
    and refresh calculation entry values.
    """
    sheets = db.query(models.CalculationSheet).all()
    return _track_sheets(
        sheets,
        db,
        project_id,
        language,
        _entry_columns_dict(body),
    )


@router.post("/sync-all", response_model=dict)
async def sync_all_calculation_sheets(
    body: Optional[schemas.AutoExportColumnsRequest] = Body(None),
    db: Session = Depends(get_db),
    project_id: str = Depends(get_project_id),
    language: str = Query("en"),
):
    """
    Synchronize all calculation sheets with concentration sheets and BOQ items
    """
    try:
        result = perform_sync_all_calculation_sheets(
            db,
            project_id,
            language=language,
            entry_columns=_entry_columns_dict(body),
        )

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
    body: Optional[schemas.AutoExportColumnsRequest] = Body(None),
    db: Session = Depends(get_db),
    project_id: str = Depends(get_project_id),
    language: str = Query("en"),
):
    """
    Populate concentration entries from calculation sheet entries
    """
    entry_columns = _entry_columns_dict(body)
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
            if calc_entry.section_number not in section_to_concentration_sheet:
                logger.warning(
                    f"No concentration sheet found for section {calc_entry.section_number}"
                )
                continue

            boq_item_id = sync_calc_entry_to_concentration(
                db, calc_entry, calculation_sheet
            )
            if boq_item_id is not None:
                entries_created += 1
                boq_items_to_export.add(boq_item_id)
                logger.info(
                    f"Synced entry for section {calc_entry.section_number} "
                    f"in concentration sheet "
                    f"{section_to_concentration_sheet[calc_entry.section_number].sheet_name}"
                )
            else:
                entries_skipped += 1
        
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
                    total_submitted = sum(
                        entry_cumulative_submitted(entry) for entry in sheet_entries
                    )
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
                boq_items_to_export, db, language=language, entry_columns=entry_columns
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
