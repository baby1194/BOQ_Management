from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from typing import List, Optional, Set
import json
import logging
import os
import platform
import shutil
import subprocess
from pathlib import Path

from database.database import get_db, get_project_id, get_project_upload_dir, get_project_export_dir
from models import models
from schemas import schemas
from services.excel_service import ExcelService
from routers.calculation_sheets import refresh_calculation_sheet_from_disk
from services.calculation_sheet_sync import run_auto_sync_after_calculation_sheet_changes
from utils.concentration_utils import compute_quantity_submitted
from fatina_paths import (
    copy_files_to_calc_sheet_dir,
    remove_file_from_calc_sheet_dir,
    is_upload_copy_path,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _sync_quantity_submitted(entry: models.ConcentrationEntry) -> None:
    entry.quantity_submitted = compute_quantity_submitted(
        entry.estimated_quantity,
        entry.submission_percentage if entry.submission_percentage is not None else 100.0,
    )


def _normalize_drawing_files(value) -> List[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(p) for p in value if p]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(p) for p in parsed if p]
        except json.JSONDecodeError:
            pass
    return []


def _drawing_path_is_listed(stored_paths: List[str], requested: str) -> bool:
    try:
        requested_resolved = str(Path(requested).resolve())
    except OSError:
        return False
    for stored in stored_paths:
        try:
            if str(Path(stored).resolve()) == requested_resolved:
                return True
        except OSError:
            continue
    return False


def _entry_boq_section_number(db_entry: models.ConcentrationEntry, db: Session) -> Optional[str]:
    sheet = db.query(models.ConcentrationSheet).filter(
        models.ConcentrationSheet.id == db_entry.concentration_sheet_id
    ).first()
    if sheet:
        boq_item = db.query(models.BOQItem).filter(
            models.BOQItem.id == sheet.boq_item_id
        ).first()
        if boq_item and boq_item.section_number:
            return str(boq_item.section_number).strip()
    if db_entry.section_number:
        return str(db_entry.section_number).strip()
    return None


def _fatina_drawing_still_referenced(
    db: Session,
    *,
    exclude_entry_id: int,
    section_number: str,
    calculation_sheet_no: str,
    filename: str,
) -> bool:
    """True if another entry still references the same Fatina drawing filename."""
    others = db.query(models.ConcentrationEntry).filter(
        models.ConcentrationEntry.id != exclude_entry_id,
        models.ConcentrationEntry.calculation_sheet_no == calculation_sheet_no,
    ).all()
    for other in others:
        other_section = _entry_boq_section_number(other, db)
        if other_section != section_number:
            continue
        for path in _normalize_drawing_files(other.drawing_files):
            if Path(path).name == filename:
                return True
    return False


def _drawing_path_still_referenced(
    db: Session, *, exclude_entry_id: int, resolved_path: str
) -> bool:
    """True if another entry still lists the same absolute drawing file path."""
    others = db.query(models.ConcentrationEntry).filter(
        models.ConcentrationEntry.id != exclude_entry_id
    ).all()
    for other in others:
        for path in _normalize_drawing_files(other.drawing_files):
            try:
                if str(Path(path).resolve()) == resolved_path:
                    return True
            except OSError:
                continue
    return False


def _sync_entry_drawing_files_to_fatina(
    db_entry: models.ConcentrationEntry, db: Session
) -> None:
    section_number = _entry_boq_section_number(db_entry, db)
    if not section_number or not db_entry.calculation_sheet_no:
        return
    paths = _normalize_drawing_files(db_entry.drawing_files)
    if paths:
        copy_files_to_calc_sheet_dir(
            section_number,
            db_entry.calculation_sheet_no,
            paths,
        )


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

@router.post(
    "/{sheet_id}/track-calculation-sheets",
    response_model=schemas.CalculationSheetsTrackResponse,
)
async def track_concentration_sheet_calculation_sheets(
    sheet_id: int,
    db: Session = Depends(get_db),
    project_id: str = Depends(get_project_id),
):
    """Reread calculation sheets linked to this concentration sheet from disk."""
    sheet = db.query(models.ConcentrationSheet).filter(
        models.ConcentrationSheet.id == sheet_id
    ).first()
    if not sheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Concentration sheet not found",
        )

    entries = db.query(models.ConcentrationEntry).filter(
        models.ConcentrationEntry.concentration_sheet_id == sheet_id
    ).all()

    calculation_sheet_nos: Set[str] = {
        entry.calculation_sheet_no.strip()
        for entry in entries
        if entry.calculation_sheet_no and entry.calculation_sheet_no.strip()
    }

    if not calculation_sheet_nos:
        return schemas.CalculationSheetsTrackResponse(
            success=False,
            message="No calculation sheet numbers found on this concentration sheet",
            sheets_updated=0,
            sheets_skipped=0,
            entries_updated=0,
            errors=["No calculation sheet numbers found on this concentration sheet"],
        )

    excel_service = ExcelService(exports_dir=get_project_export_dir(project_id))
    calculation_sheets = db.query(models.CalculationSheet).filter(
        models.CalculationSheet.calculation_sheet_no.in_(calculation_sheet_nos)
    ).all()

    found_nos = {cs.calculation_sheet_no for cs in calculation_sheets}
    sheets_updated = 0
    sheets_skipped = 0
    entries_updated = 0
    errors: List[str] = []

    for calc_no in sorted(calculation_sheet_nos - found_nos):
        sheets_skipped += 1
        errors.append(f"{calc_no} - Calculation sheet not found in database")

    for calc_sheet in calculation_sheets:
        entries_refreshed, error = refresh_calculation_sheet_from_disk(
            calc_sheet, excel_service, db
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
            submission_percentage=entry.submission_percentage,
            internal_quantity=entry.internal_quantity,
            approved_by_project_manager=entry.approved_by_project_manager,
            notes=entry.notes,
            supervisor_notes=entry.supervisor_notes,
            drawing_files=entry.drawing_files or [],
            is_manual=True  # Mark as manually created
        )
        _sync_quantity_submitted(db_entry)

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
        update_data.pop("quantity_submitted", None)

        if not db_entry.is_manual:
            allowed_for_auto = {
                "notes",
                "supervisor_notes",
                "internal_quantity",
                "approved_by_project_manager",
                "submission_percentage",
            }
            update_data = {
                k: v for k, v in update_data.items() if k in allowed_for_auto
            }

        for field, value in update_data.items():
            setattr(db_entry, field, value)

        if db_entry.is_manual or "submission_percentage" in update_data:
            _sync_quantity_submitted(db_entry)
        
        db.commit()
        db.refresh(db_entry)
        
        # Update BOQ Item totals
        src_sheet = db.query(models.ConcentrationSheet).filter(
            models.ConcentrationSheet.id == db_entry.concentration_sheet_id
        ).first()
        if src_sheet:
            await _update_boq_item_totals(src_sheet.boq_item_id, db)
        
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
        entry_section = db_entry.section_number
        db.delete(db_entry)
        db.commit()
        
        # Update BOQ Item totals
        del_sheet = db.query(models.ConcentrationSheet).filter(
            models.ConcentrationSheet.id == concentration_sheet_id
        ).first()
        if del_sheet:
            await _update_boq_item_totals(del_sheet.boq_item_id, db)
        
        logger.info(f"Deleted concentration entry: {entry_section}")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting concentration entry {entry_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


def _get_or_create_concentration_sheet_for_boq(
    boq_item_id: int, db: Session
) -> Optional[models.ConcentrationSheet]:
    sheet = (
        db.query(models.ConcentrationSheet)
        .filter(models.ConcentrationSheet.boq_item_id == boq_item_id)
        .first()
    )
    if sheet:
        return sheet
    boq_item = (
        db.query(models.BOQItem).filter(models.BOQItem.id == boq_item_id).first()
    )
    if not boq_item:
        return None
    sheet = models.ConcentrationSheet(
        boq_item_id=boq_item_id,
        sheet_name=f"Concentration Sheet - {boq_item.section_number}",
    )
    db.add(sheet)
    db.flush()
    return sheet


@router.post(
    "/entries/{entry_id}/copy-to-boq-items",
    response_model=schemas.CopyConcentrationEntryToBOQItemsResponse,
)
async def copy_concentration_entry_to_boq_items(
    entry_id: int,
    body: schemas.CopyConcentrationEntryToBOQItemsRequest,
    db: Session = Depends(get_db),
):
    """Copy a manual concentration entry's field values onto other BOQ items (new row per target sheet)."""
    try:
        db_entry = (
            db.query(models.ConcentrationEntry)
            .filter(models.ConcentrationEntry.id == entry_id)
            .first()
        )
        if not db_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Concentration entry not found",
            )
        if not db_entry.is_manual:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only manually added entries can be copied to other BOQ items",
            )

        src_sheet = (
            db.query(models.ConcentrationSheet)
            .filter(
                models.ConcentrationSheet.id == db_entry.concentration_sheet_id
            )
            .first()
        )
        if not src_sheet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Concentration sheet not found for this entry",
            )

        source_boq_id = src_sheet.boq_item_id
        unique_ids: List[int] = []
        seen: Set[int] = set()
        for bid in body.boq_item_ids:
            if bid not in seen:
                seen.add(bid)
                unique_ids.append(bid)

        target_boq_ids: List[int] = [
            bid for bid in unique_ids if bid != source_boq_id
        ]
        if not target_boq_ids:
            return schemas.CopyConcentrationEntryToBOQItemsResponse(
                success=True,
                message="No target BOQ items selected (current item excluded).",
                entries_created=0,
            )

        created = 0
        updated_boq_ids: Set[int] = set()
        for boq_item_id in target_boq_ids:
            boq_item = (
                db.query(models.BOQItem)
                .filter(models.BOQItem.id == boq_item_id)
                .first()
            )
            if not boq_item:
                continue
            target_sheet = _get_or_create_concentration_sheet_for_boq(
                boq_item_id, db
            )
            if not target_sheet:
                continue
            clone = models.ConcentrationEntry(
                concentration_sheet_id=target_sheet.id,
                section_number=boq_item.section_number,
                description=db_entry.description,
                calculation_sheet_no=db_entry.calculation_sheet_no,
                drawing_no=db_entry.drawing_no,
                estimated_quantity=db_entry.estimated_quantity,
                submission_percentage=db_entry.submission_percentage,
                quantity_submitted=db_entry.quantity_submitted,
                internal_quantity=db_entry.internal_quantity,
                approved_by_project_manager=db_entry.approved_by_project_manager,
                notes=db_entry.notes,
                supervisor_notes=db_entry.supervisor_notes,
                drawing_files=_normalize_drawing_files(db_entry.drawing_files),
                is_manual=True,
            )
            db.add(clone)
            created += 1
            updated_boq_ids.add(boq_item_id)

        db.commit()

        for bid in updated_boq_ids:
            await _update_boq_item_totals(bid, db)

        return schemas.CopyConcentrationEntryToBOQItemsResponse(
            success=True,
            message=f"Created {created} concentration entr{'y' if created == 1 else 'ies'} on selected BOQ items.",
            entries_created=created,
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(
            f"Error copying concentration entry {entry_id} to BOQ items: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post(
    "/entries/{entry_id}/drawing-files",
    response_model=schemas.ConcentrationEntry,
)
async def upload_entry_drawing_files(
    entry_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    project_id: str = Depends(get_project_id),
):
    """Attach one or more drawing files to a concentration entry."""
    db_entry = db.query(models.ConcentrationEntry).filter(
        models.ConcentrationEntry.id == entry_id
    ).first()
    if not db_entry:
        raise HTTPException(status_code=404, detail="Concentration entry not found")
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    upload_root = get_project_upload_dir(project_id)
    dest_dir = upload_root / "drawing-files" / str(entry_id)
    dest_dir.mkdir(parents=True, exist_ok=True)

    stored_paths = _normalize_drawing_files(db_entry.drawing_files)
    added = 0

    for upload in files:
        if not upload.filename:
            continue
        safe_name = Path(upload.filename).name
        dest_path = dest_dir / safe_name
        counter = 1
        while dest_path.exists():
            stem = Path(safe_name).stem
            suffix = Path(safe_name).suffix
            dest_path = dest_dir / f"{stem}_{counter}{suffix}"
            counter += 1
        try:
            with open(dest_path, "wb") as buffer:
                shutil.copyfileobj(upload.file, buffer)
            stored_paths.append(str(dest_path.resolve()))
            added += 1
        except OSError as exc:
            logger.error(f"Failed to save drawing file {safe_name}: {exc}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save drawing file: {safe_name}",
            )

    if added == 0:
        raise HTTPException(status_code=400, detail="No valid files uploaded")

    db_entry.drawing_files = stored_paths
    db.commit()
    db.refresh(db_entry)
    _sync_entry_drawing_files_to_fatina(db_entry, db)
    return db_entry


@router.post("/entries/{entry_id}/open-drawing-file")
async def open_entry_drawing_file(
    entry_id: int,
    body: schemas.DrawingFilePathRequest,
    db: Session = Depends(get_db),
):
    """Open an attached drawing file in the default OS application."""
    db_entry = db.query(models.ConcentrationEntry).filter(
        models.ConcentrationEntry.id == entry_id
    ).first()
    if not db_entry:
        raise HTTPException(status_code=404, detail="Concentration entry not found")

    stored_paths = _normalize_drawing_files(db_entry.drawing_files)
    if not _drawing_path_is_listed(stored_paths, body.path):
        raise HTTPException(status_code=403, detail="File path not attached to this entry")

    file_path = body.path
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    try:
        if platform.system() == "Windows":
            os.startfile(file_path)
        elif platform.system() == "Darwin":
            subprocess.call(["open", file_path])
        else:
            subprocess.call(["xdg-open", file_path])
        return {"success": True, "message": f"Opening file: {file_path}"}
    except Exception as exc:
        logger.error(f"Error opening drawing file: {exc}")
        raise HTTPException(status_code=500, detail=f"Error opening file: {exc}")


@router.delete(
    "/entries/{entry_id}/drawing-files",
    response_model=schemas.ConcentrationEntry,
)
async def remove_entry_drawing_file(
    entry_id: int,
    body: schemas.DrawingFilePathRequest,
    db: Session = Depends(get_db),
    project_id: str = Depends(get_project_id),
):
    """Remove a drawing file from an entry and delete its upload and Fatina copies."""
    db_entry = db.query(models.ConcentrationEntry).filter(
        models.ConcentrationEntry.id == entry_id
    ).first()
    if not db_entry:
        raise HTTPException(status_code=404, detail="Concentration entry not found")

    stored_paths = _normalize_drawing_files(db_entry.drawing_files)
    if not _drawing_path_is_listed(stored_paths, body.path):
        raise HTTPException(status_code=404, detail="File not attached to this entry")

    try:
        requested_resolved = str(Path(body.path).resolve())
    except OSError:
        raise HTTPException(status_code=400, detail="Invalid file path")

    filename = Path(body.path).name
    section_number = _entry_boq_section_number(db_entry, db)
    calculation_sheet_no = db_entry.calculation_sheet_no

    db_entry.drawing_files = [
        p for p in stored_paths
        if str(Path(p).resolve()) != requested_resolved
    ]
    db.commit()
    db.refresh(db_entry)

    still_referenced = _drawing_path_still_referenced(
        db, exclude_entry_id=entry_id, resolved_path=requested_resolved
    )

    if not still_referenced:
        upload_root = get_project_upload_dir(project_id)
        if is_upload_copy_path(requested_resolved, upload_root):
            try:
                Path(requested_resolved).unlink(missing_ok=True)
                logger.info(f"Removed drawing upload file: {requested_resolved}")
            except OSError as exc:
                logger.warning(
                    f"Could not remove drawing upload file {requested_resolved}: {exc}"
                )

    if (
        not still_referenced
        and section_number
        and calculation_sheet_no
        and filename
        and not _fatina_drawing_still_referenced(
            db,
            exclude_entry_id=entry_id,
            section_number=section_number,
            calculation_sheet_no=calculation_sheet_no,
            filename=filename,
        )
    ):
        remove_file_from_calc_sheet_dir(
            section_number,
            calculation_sheet_no,
            body.path,
        )

    return db_entry


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