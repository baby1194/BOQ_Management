"""Run full calculation-sheet → concentration → BOQ synchronization."""

from __future__ import annotations

import logging
from typing import Any, Dict

from sqlalchemy.orm import Session

from database.database import get_project_export_dir
from models import models
from services.pdf_service import PDFService
from services.sync_service import SyncService
from utils.concentration_utils import apply_calculation_entry_quantities
from utils.calculation_sheet_utils import resolve_calc_entry_current_invoice_id

logger = logging.getLogger(__name__)


def push_calculation_sheet_to_concentration_entries(
    db: Session,
    calculation_sheet: models.CalculationSheet,
    *,
    lookup_calculation_sheet_no: str | None = None,
) -> int:
    """
    Copy estimated/submitted quantities from calc entries to matching concentration entries.
    Used immediately after import or track so concentration values stay in sync.
    """
    lookup_no = lookup_calculation_sheet_no or calculation_sheet.calculation_sheet_no
    db.flush()

    calculation_entries = (
        db.query(models.CalculationEntry)
        .filter(models.CalculationEntry.calculation_sheet_id == calculation_sheet.id)
        .all()
    )

    updated = 0
    for calc_entry in calculation_entries:
        concentration_entry = (
            db.query(models.ConcentrationEntry)
            .filter(
                models.ConcentrationEntry.section_number == calc_entry.section_number,
                models.ConcentrationEntry.calculation_sheet_no == lookup_no,
            )
            .first()
        )
        if not concentration_entry:
            continue

        apply_calculation_entry_quantities(concentration_entry, calc_entry)
        concentration_entry.calculation_sheet_no = calculation_sheet.calculation_sheet_no
        concentration_entry.drawing_no = resolve_calc_entry_current_invoice_id(
            calc_entry, calculation_sheet
        )
        concentration_entry.description = calculation_sheet.description
        concentration_entry.is_manual = False
        updated += 1

    if updated:
        logger.info(
            "Pushed calc sheet %s quantities to %s concentration entries",
            calculation_sheet.calculation_sheet_no,
            updated,
        )
    return updated


def perform_sync_all_calculation_sheets(
    db: Session, project_id: str
) -> Dict[str, Any]:
    """
    Same work as POST /calculation-sheets/sync-all:
    sync all calc sheets to concentration entries and BOQ items, then export PDFs.
    """
    sync_service = SyncService(db)
    result = sync_service.sync_all_calculation_sheets()

    if not result.get("success"):
        return {
            "success": False,
            "message": result.get("message", "Synchronization failed"),
            "details": {
                "sheets_processed": 0,
                "entries_updated": 0,
                "boq_items_updated": 0,
                "concentration_sheets_exported": 0,
            },
        }

    concentration_sheets_exported = 0
    boq_items_to_export = result.get("boq_items_to_export") or []
    if boq_items_to_export:
        pdf_service = PDFService(exports_dir=get_project_export_dir(project_id))
        concentration_sheets_exported = pdf_service.export_concentration_sheets_for_boq_items(
            boq_items_to_export, db
        )

    return {
        "success": True,
        "message": result["message"],
        "details": {
            "sheets_processed": result.get("sheets_processed", 0),
            "entries_updated": result.get("entries_updated", 0),
            "boq_items_updated": result.get("boq_items_updated", 0),
            "concentration_sheets_exported": concentration_sheets_exported,
        },
    }


def append_sync_summary_message(base_message: str, sync_result: Dict[str, Any]) -> str:
    """Append a human-readable sync summary to an import/track message."""
    if not sync_result.get("success"):
        logger.warning(
            "Auto-sync after import/track failed: %s",
            sync_result.get("message"),
        )
        return (
            f"{base_message} Auto-sync failed: "
            f"{sync_result.get('message', 'unknown error')}."
        )

    details = sync_result.get("details") or {}
    return (
        f"{base_message} Synced: {details.get('entries_updated', 0)} concentration "
        f"entries updated, {details.get('boq_items_updated', 0)} BOQ items updated, "
        f"{details.get('concentration_sheets_exported', 0)} concentration sheet PDFs exported."
    )


def run_auto_sync_after_calculation_sheet_changes(
    db: Session, project_id: str, base_message: str
) -> str:
    """Run full sync and return message with summary appended."""
    sync_result = perform_sync_all_calculation_sheets(db, project_id)
    return append_sync_summary_message(base_message, sync_result)
