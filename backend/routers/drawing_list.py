from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
import os
import platform
import subprocess

from database.database import get_db
from models import models
from schemas import schemas

router = APIRouter()
logger = logging.getLogger(__name__)

VALID_EXECUTION_STATUSES = {None, "", "to_be_executed", "cancelled"}


def _clean_str(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_execution_status(value: Optional[str]) -> Optional[str]:
    cleaned = _clean_str(value)
    if cleaned not in VALID_EXECUTION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='execution_status must be "to_be_executed", "cancelled", or empty',
        )
    return cleaned


def _to_response(row: models.DrawingListItem) -> schemas.DrawingListItem:
    return schemas.DrawingListItem(
        id=row.id,
        no=row.display_order,
        drawing_type=row.drawing_type,
        planning_office=row.planning_office,
        drawing_name=row.drawing_name,
        cross_sections=row.cross_sections,
        element=row.element,
        sheet_name=row.sheet_name,
        edition=row.edition,
        release_date=row.release_date,
        update_description=row.update_description,
        folder_date=row.folder_date,
        file_path=row.file_path,
        notes=row.notes,
        execution_status=row.execution_status,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _ordered_rows(db: Session) -> List[models.DrawingListItem]:
    return (
        db.query(models.DrawingListItem)
        .order_by(
            models.DrawingListItem.display_order.asc(),
            models.DrawingListItem.id.asc(),
        )
        .all()
    )


def _renumber(rows: List[models.DrawingListItem]) -> None:
    for index, row in enumerate(rows, start=1):
        row.display_order = index


def _insert_at(
    rows: List[models.DrawingListItem],
    item: models.DrawingListItem,
    target_no: Optional[int],
) -> None:
    """Place item at 1-based target_no; append if missing/invalid/too large."""
    count = len(rows)
    if target_no is None or target_no < 1 or target_no > count + 1:
        rows.append(item)
    else:
        rows.insert(target_no - 1, item)
    _renumber(rows)


def _apply_fields(db_item: models.DrawingListItem, data: dict) -> None:
    field_map = {
        "drawing_type": _clean_str,
        "planning_office": _clean_str,
        "drawing_name": _clean_str,
        "cross_sections": _clean_str,
        "element": _clean_str,
        "sheet_name": _clean_str,
        "edition": _clean_str,
        "release_date": _clean_str,
        "update_description": _clean_str,
        "folder_date": _clean_str,
        "file_path": _clean_str,
        "notes": _clean_str,
    }
    for key, cleaner in field_map.items():
        if key in data:
            setattr(db_item, key, cleaner(data[key]))
    if "execution_status" in data:
        db_item.execution_status = _normalize_execution_status(data["execution_status"])


@router.post("/measure-plan")
def measure_plan_file(body: dict):
    from pathlib import Path

    from services.dxf_quantities import measure_plan

    raw = str(body.get("file_path") or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="file_path is required")
    return measure_plan(Path(raw))


@router.post("/assign-plan-quantity")
def assign_plan_quantity(body: dict, db: Session = Depends(get_db)):
    section = str(body.get("section_number") or "").strip()
    quantity = float(body.get("quantity") or 0)
    if not section:
        raise HTTPException(status_code=400, detail="section_number is required")
    item = (
        db.query(models.BOQItem)
        .filter(models.BOQItem.section_number == section)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="BOQ item not found")
    item.estimated_quantity = float(item.estimated_quantity or 0) + quantity
    item.total_estimate = float(item.estimated_quantity or 0) * float(item.price or 0)
    db.commit()
    return {
        "section_number": item.section_number,
        "estimated_quantity": item.estimated_quantity,
        "added": quantity,
    }


@router.get("/elements")
def list_elements(db: Session = Depends(get_db)):
    from services.element_progress import element_names_from_entries

    names = {}
    for (element,) in db.query(models.DrawingListItem.element).all():
        if element and str(element).strip():
            names.setdefault(str(element).strip().casefold(), str(element).strip())
    entries = db.query(
        models.ConcentrationEntry.description,
        models.ConcentrationEntry.invoice_description,
    ).all()
    for name in element_names_from_entries(
        {"description": description, "invoice_description": invoice_description}
        for description, invoice_description in entries
    ):
        names.setdefault(name.casefold(), name)
    return sorted(names.values(), key=str.casefold)


@router.get("/element-submission")
def element_submission(element: str, db: Session = Depends(get_db)):
    from services.element_progress import items_for_element

    needle = element.strip()
    boq_items, entries_by_section, drawing_names_by_element, _updates = _element_lookup(db)
    drawing_names = drawing_names_by_element.get(needle.casefold(), [])
    rows = items_for_element(needle, boq_items, entries_by_section, drawing_names)
    return {
        "element": needle,
        "submitted_count": sum(1 for row in rows if row["submitted"]),
        "not_submitted_count": sum(1 for row in rows if not row["submitted"]),
        "items": rows,
    }


class WordItemsRequest(BaseModel):
    words: str = ""
    language: str = Field("en", pattern="^(en|he)$")


def _element_lookup(db: Session):
    from services.element_progress import boq_table_fields

    contract_updates = (
        db.query(models.ContractQuantityUpdate)
        .order_by(models.ContractQuantityUpdate.update_index)
        .all()
    )
    updates_by_item = {}
    for row in db.query(models.BOQItemQuantityUpdate).all():
        updates_by_item.setdefault(row.boq_item_id, {})[row.contract_update_id] = row
    boq_items = []
    for item in db.query(models.BOQItem).all():
        item_updates = updates_by_item.get(item.id, {})
        boq_items.append(
            boq_table_fields(
                {
                    "serial_number": item.serial_number,
                    "structure": item.structure,
                    "system": item.system,
                    "section_number": item.section_number,
                    "description": item.description,
                    "unit": item.unit,
                    "original_contract_quantity": item.original_contract_quantity,
                    "price": item.price,
                    "submitted_price": item.submitted_price,
                    "submitted_to_supervisor": item.submitted_to_supervisor,
                    "submitted_to_supervisor_date": item.submitted_to_supervisor_date,
                    "total_contract_sum": item.total_contract_sum,
                    "estimated_quantity": item.estimated_quantity,
                    "quantity_submitted": item.quantity_submitted,
                    "internal_quantity": item.internal_quantity,
                    "approved_by_project_manager": item.approved_by_project_manager,
                    "approved_signed_quantity": item.approved_signed_quantity,
                    "submitted_increase_quantity": item.submitted_increase_quantity,
                    "total_estimate": item.total_estimate,
                    "total_submitted": item.total_submitted,
                    "internal_total": item.internal_total,
                    "total_approved_by_project_manager": item.total_approved_by_project_manager,
                    "approved_signed_total": item.approved_signed_total,
                    "subsection": item.subsection,
                    "notes": item.notes,
                },
                [
                    {
                        "id": update.id,
                        "quantity": item_updates[update.id].updated_contract_quantity
                        if update.id in item_updates
                        else None,
                        "sum": item_updates[update.id].updated_contract_sum
                        if update.id in item_updates
                        else None,
                    }
                    for update in contract_updates
                ],
            )
        )
    entries_by_section = {}
    for entry in db.query(models.ConcentrationEntry).all():
        entries_by_section.setdefault(entry.section_number, []).append(
            {
                "description": entry.description,
                "invoice_description": entry.invoice_description,
                "drawing_no": entry.drawing_no,
                "calculation_sheet_no": entry.calculation_sheet_no,
                "estimated_quantity": entry.estimated_quantity,
                "quantity_submitted": entry.quantity_submitted,
            }
        )
    drawing_names_by_element = {}
    for row in db.query(models.DrawingListItem).all():
        if not row.element or not row.drawing_name:
            continue
        drawing_names_by_element.setdefault(str(row.element).strip().casefold(), []).append(
            row.drawing_name
        )
    return boq_items, entries_by_section, drawing_names_by_element, contract_updates


@router.post("/word-items/excel")
def word_items_excel(body: WordItemsRequest, db: Session = Depends(get_db)):
    from services.element_progress import rows_for_words, split_search_words, word_items_workbook

    if not split_search_words(body.words):
        raise HTTPException(status_code=400, detail="Enter at least one word")
    boq_items, entries_by_section, drawing_names, contract_updates = _element_lookup(db)
    rows = rows_for_words(body.words, boq_items, entries_by_section, drawing_names)
    content = word_items_workbook(rows, body.language, contract_updates)
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="word-items.xlsx"'},
    )


@router.get("/", response_model=List[schemas.DrawingListItem])
async def list_drawings(db: Session = Depends(get_db)):
    try:
        return [_to_response(row) for row in _ordered_rows(db)]
    except Exception as e:
        logger.error("Error listing drawings: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post(
    "/",
    response_model=schemas.DrawingListItem,
    status_code=status.HTTP_201_CREATED,
)
async def create_drawing(
    body: schemas.DrawingListItemCreate,
    db: Session = Depends(get_db),
):
    try:
        data = body.model_dump(exclude={"no"})
        db_item = models.DrawingListItem(display_order=1)
        _apply_fields(db_item, data)

        rows = _ordered_rows(db)
        _insert_at(rows, db_item, body.no)
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return _to_response(db_item)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Error creating drawing: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.put("/{item_id}", response_model=schemas.DrawingListItem)
async def update_drawing(
    item_id: int,
    body: schemas.DrawingListItemUpdate,
    db: Session = Depends(get_db),
):
    try:
        db_item = (
            db.query(models.DrawingListItem)
            .filter(models.DrawingListItem.id == item_id)
            .first()
        )
        if not db_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Drawing not found",
            )

        data = body.model_dump(exclude_unset=True, exclude={"no"})
        _apply_fields(db_item, data)

        if body.no is not None and body.no != db_item.display_order:
            rows = [r for r in _ordered_rows(db) if r.id != item_id]
            _insert_at(rows, db_item, body.no)

        db.commit()
        db.refresh(db_item)
        return _to_response(db_item)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Error updating drawing %s: %s", item_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_drawing(item_id: int, db: Session = Depends(get_db)):
    try:
        db_item = (
            db.query(models.DrawingListItem)
            .filter(models.DrawingListItem.id == item_id)
            .first()
        )
        if not db_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Drawing not found",
            )
        db.delete(db_item)
        db.flush()
        _renumber(_ordered_rows(db))
        db.commit()
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Error deleting drawing %s: %s", item_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/{item_id}/open")
async def open_drawing_file(item_id: int, db: Session = Depends(get_db)):
    db_item = (
        db.query(models.DrawingListItem)
        .filter(models.DrawingListItem.id == item_id)
        .first()
    )
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drawing not found",
        )
    file_path = db_item.file_path
    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file path set for this drawing",
        )
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {file_path}",
        )

    try:
        if platform.system() == "Windows":
            os.startfile(file_path)
        elif platform.system() == "Darwin":
            subprocess.call(["open", file_path])
        else:
            subprocess.call(["xdg-open", file_path])
        return {"success": True, "message": f"Opening file: {file_path}"}
    except Exception as exc:
        logger.error("Error opening drawing file: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error opening file: {exc}",
        )
