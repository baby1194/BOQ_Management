"""Copy BOQ items (with concentration sheets/entries) between project databases."""

from __future__ import annotations

import copy
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import models
from services.non_boq_service import remove_non_boq_item_by_section

logger = logging.getLogger(__name__)


def _normalize_drawing_files(value: Any) -> List[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(path) for path in value if path]
    return []


def _unique_dest_path(dest_dir: Path, filename: str) -> Path:
    dest = dest_dir / filename
    if not dest.exists():
        return dest
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 1
    while True:
        candidate = dest_dir / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def copy_drawing_files_to_project(
    paths: Sequence[str],
    target_upload_dir: Path,
    new_entry_id: int,
) -> List[str]:
    """Copy drawing files into the target project's upload folder; return new paths."""
    normalized = _normalize_drawing_files(list(paths))
    if not normalized:
        return []

    dest_dir = target_upload_dir / "drawing-files" / str(new_entry_id)
    dest_dir.mkdir(parents=True, exist_ok=True)

    new_paths: List[str] = []
    for path_str in normalized:
        src = Path(path_str)
        if not src.is_file():
            logger.warning("Drawing file missing during transfer, skipping: %s", path_str)
            continue
        dest = _unique_dest_path(dest_dir, src.name)
        try:
            shutil.copy2(src, dest)
            new_paths.append(str(dest.resolve()))
        except OSError as exc:
            logger.error("Failed to copy drawing file %s: %s", path_str, exc)
    return new_paths


def rewrite_breakdown_drawing_files(
    breakdown: Any,
    target_upload_dir: Path,
    new_entry_id: int,
) -> Any:
    """Deep-copy submission_breakdown and remap drawing_files paths."""
    if not isinstance(breakdown, dict):
        return breakdown

    cloned = copy.deepcopy(breakdown)
    period_details = cloned.get("period_details")
    if not isinstance(period_details, dict):
        return cloned

    for period_key, detail in period_details.items():
        if not isinstance(detail, dict):
            continue
        files = detail.get("drawing_files")
        if files:
            detail["drawing_files"] = copy_drawing_files_to_project(
                _normalize_drawing_files(files),
                target_upload_dir,
                new_entry_id,
            )
    return cloned


def classify_transfer_items(
    source_db: Session,
    target_db: Session,
    boq_item_ids: Sequence[int],
) -> Tuple[List[models.BOQItem], List[Dict[str, Any]], List[int]]:
    """
    Split requested ids into copyable items vs section_number conflicts.

    Returns (to_copy, conflicts, missing_ids).
    conflicts: [{boq_item_id, section_number, description}, ...]
    """
    unique_ids: List[int] = []
    seen = set()
    for item_id in boq_item_ids:
        if item_id not in seen:
            seen.add(item_id)
            unique_ids.append(item_id)

    if not unique_ids:
        return [], [], []

    source_items = (
        source_db.query(models.BOQItem)
        .filter(models.BOQItem.id.in_(unique_ids))
        .all()
    )
    by_id = {item.id: item for item in source_items}
    missing_ids = [item_id for item_id in unique_ids if item_id not in by_id]

    section_numbers = [by_id[i].section_number for i in unique_ids if i in by_id]
    existing_sections = set()
    if section_numbers:
        existing_sections = {
            row[0]
            for row in target_db.query(models.BOQItem.section_number)
            .filter(models.BOQItem.section_number.in_(section_numbers))
            .all()
        }

    to_copy: List[models.BOQItem] = []
    conflicts: List[Dict[str, Any]] = []
    for item_id in unique_ids:
        item = by_id.get(item_id)
        if not item:
            continue
        if item.section_number in existing_sections:
            conflicts.append(
                {
                    "boq_item_id": item.id,
                    "section_number": item.section_number,
                    "description": item.description,
                }
            )
        else:
            to_copy.append(item)

    return to_copy, conflicts, missing_ids


def _copy_boq_item_row(source: models.BOQItem, display_order: int) -> models.BOQItem:
    return models.BOQItem(
        display_order=display_order,
        serial_number=source.serial_number,
        structure=source.structure,
        system=source.system,
        section_number=source.section_number,
        description=source.description,
        unit=source.unit,
        original_contract_quantity=source.original_contract_quantity,
        price=source.price,
        total_contract_sum=source.total_contract_sum,
        estimated_quantity=source.estimated_quantity or 0.0,
        quantity_submitted=source.quantity_submitted or 0.0,
        internal_quantity=source.internal_quantity or 0.0,
        approved_by_project_manager=source.approved_by_project_manager or 0.0,
        total_estimate=source.total_estimate or 0.0,
        total_submitted=source.total_submitted or 0.0,
        internal_total=source.internal_total or 0.0,
        total_approved_by_project_manager=source.total_approved_by_project_manager
        or 0.0,
        approved_signed_quantity=source.approved_signed_quantity or 0.0,
        approved_signed_total=source.approved_signed_total or 0.0,
        notes=source.notes,
        internal_field_1=source.internal_field_1,
        internal_field_2=source.internal_field_2,
        subsection=source.subsection,
    )


def _copy_concentration_sheet(
    source_sheet: models.ConcentrationSheet,
    new_boq_item_id: int,
    target_project_info: Optional[models.ProjectInfo],
) -> models.ConcentrationSheet:
    project_name = source_sheet.project_name
    contractor = source_sheet.contractor_in_charge
    contract_no = source_sheet.contract_no
    developer = source_sheet.developer_name
    if target_project_info:
        project_name = target_project_info.project_name or project_name
        contractor = (
            target_project_info.main_contractor_name
            or target_project_info.subcontractor_name
            or contractor
        )
        contract_no = target_project_info.contract_no or contract_no
        developer = target_project_info.developer_name or developer

    return models.ConcentrationSheet(
        boq_item_id=new_boq_item_id,
        sheet_name=source_sheet.sheet_name,
        project_name=project_name,
        contractor_in_charge=contractor,
        contract_no=contract_no,
        developer_name=developer,
        total_estimate=source_sheet.total_estimate or 0.0,
        total_submitted=source_sheet.total_submitted or 0.0,
        total_pnimi=source_sheet.total_pnimi or 0.0,
        total_approved=source_sheet.total_approved or 0.0,
    )


def copy_boq_items_to_project(
    source_db: Session,
    target_db: Session,
    boq_item_ids: Sequence[int],
    target_upload_dir: Path,
) -> Dict[str, Any]:
    """
    Copy selected BOQ items + concentration data into target project.

    Items whose section_number already exists in the target are skipped (not overwritten).
    """
    to_copy, conflicts, missing_ids = classify_transfer_items(
        source_db, target_db, boq_item_ids
    )

    transferred: List[Dict[str, Any]] = []
    if not to_copy:
        return {
            "transferred": transferred,
            "skipped_conflicts": conflicts,
            "missing_ids": missing_ids,
            "transferred_count": 0,
            "skipped_count": len(conflicts),
        }

    max_order = target_db.query(func.max(models.BOQItem.display_order)).scalar()
    next_order = (max_order if max_order is not None else -1) + 1

    target_project_info = target_db.query(models.ProjectInfo).first()

    for source_item in to_copy:
        new_item = _copy_boq_item_row(source_item, next_order)
        next_order += 1
        target_db.add(new_item)
        target_db.flush()

        if new_item.serial_number is None:
            new_item.serial_number = new_item.id

        source_sheet = (
            source_db.query(models.ConcentrationSheet)
            .filter(models.ConcentrationSheet.boq_item_id == source_item.id)
            .first()
        )
        if source_sheet:
            new_sheet = _copy_concentration_sheet(
                source_sheet, new_item.id, target_project_info
            )
        else:
            # Always give the target a concentration sheet so the item is usable
            # without a separate "Create Concentration Sheets" step.
            new_sheet = models.ConcentrationSheet(
                boq_item_id=new_item.id,
                sheet_name=f"Concentration Sheet - {new_item.section_number}",
            )
            if target_project_info:
                new_sheet.project_name = target_project_info.project_name
                new_sheet.contractor_in_charge = (
                    target_project_info.main_contractor_name
                    or target_project_info.subcontractor_name
                )
                new_sheet.contract_no = target_project_info.contract_no
                new_sheet.developer_name = target_project_info.developer_name

        target_db.add(new_sheet)
        target_db.flush()

        if source_sheet:
            source_entries = (
                source_db.query(models.ConcentrationEntry)
                .filter(
                    models.ConcentrationEntry.concentration_sheet_id
                    == source_sheet.id
                )
                .order_by(models.ConcentrationEntry.id.asc())
                .all()
            )
            for source_entry in source_entries:
                # Mark as manual so orphan-purge (which deletes auto entries whose
                # calculation_sheet_no is missing in the target) does not wipe
                # transferred concentration data. Calc sheets are not copied in v1.
                new_entry = models.ConcentrationEntry(
                    concentration_sheet_id=new_sheet.id,
                    section_number=source_entry.section_number,
                    description=source_entry.description,
                    calculation_sheet_no=source_entry.calculation_sheet_no,
                    drawing_no=source_entry.drawing_no,
                    invoice_description=source_entry.invoice_description,
                    estimated_quantity=source_entry.estimated_quantity or 0.0,
                    submission_percentage=source_entry.submission_percentage
                    if source_entry.submission_percentage is not None
                    else 100.0,
                    quantity_submitted=source_entry.quantity_submitted or 0.0,
                    submission_breakdown=None,
                    internal_quantity=source_entry.internal_quantity or 0.0,
                    approved_by_project_manager=source_entry.approved_by_project_manager
                    or 0.0,
                    notes=source_entry.notes,
                    supervisor_notes=source_entry.supervisor_notes,
                    drawing_files=[],
                    is_manual=True,
                )
                target_db.add(new_entry)
                target_db.flush()

                new_entry.drawing_files = copy_drawing_files_to_project(
                    _normalize_drawing_files(source_entry.drawing_files),
                    target_upload_dir,
                    new_entry.id,
                )
                new_entry.submission_breakdown = rewrite_breakdown_drawing_files(
                    source_entry.submission_breakdown,
                    target_upload_dir,
                    new_entry.id,
                )

        remove_non_boq_item_by_section(target_db, new_item.section_number)

        transferred.append(
            {
                "source_boq_item_id": source_item.id,
                "target_boq_item_id": new_item.id,
                "section_number": new_item.section_number,
                "description": new_item.description,
            }
        )

    target_db.commit()

    return {
        "transferred": transferred,
        "skipped_conflicts": conflicts,
        "missing_ids": missing_ids,
        "transferred_count": len(transferred),
        "skipped_count": len(conflicts),
    }
