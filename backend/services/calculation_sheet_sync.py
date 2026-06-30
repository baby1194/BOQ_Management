"""Run calculation-sheet → concentration → BOQ synchronization."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Set

from sqlalchemy.orm import Session

from database.database import get_project_export_dir
from models import models
from services.pdf_service import PDFService
from services.sync_service import SyncService
from utils.concentration_utils import (
    prune_stale_concentration_entries_for_calc_sheet,
    sync_calc_entry_to_concentration,
)

logger = logging.getLogger(__name__)


@dataclass
class CalcSheetPushResult:
    entries_updated: int = 0
    affected_boq_item_ids: Set[int] = field(default_factory=set)

    def merge(self, other: "CalcSheetPushResult") -> "CalcSheetPushResult":
        return CalcSheetPushResult(
            entries_updated=self.entries_updated + other.entries_updated,
            affected_boq_item_ids=self.affected_boq_item_ids | other.affected_boq_item_ids,
        )


def merge_push_results(results: Iterable[CalcSheetPushResult]) -> CalcSheetPushResult:
    merged = CalcSheetPushResult()
    for result in results:
        merged = merged.merge(result)
    return merged


def push_calculation_sheet_to_concentration_entries(
    db: Session,
    calculation_sheet: models.CalculationSheet,
    *,
    lookup_calculation_sheet_no: str | None = None,
) -> CalcSheetPushResult:
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
    affected_boq_item_ids: Set[int] = set()
    for calc_entry in calculation_entries:
        boq_item_id = sync_calc_entry_to_concentration(
            db,
            calc_entry,
            calculation_sheet,
            lookup_calculation_sheet_no=lookup_no,
        )
        if boq_item_id is not None:
            affected_boq_item_ids.add(boq_item_id)
            updated += 1

    removed, pruned_boq_item_ids = prune_stale_concentration_entries_for_calc_sheet(
        db,
        calculation_sheet,
        lookup_calculation_sheet_no=lookup_no,
    )
    affected_boq_item_ids |= pruned_boq_item_ids

    if removed:
        logger.info(
            "Removed %s stale concentration entries for calc sheet %s",
            removed,
            calculation_sheet.calculation_sheet_no,
        )

    if affected_boq_item_ids:
        sync_service = SyncService(db)
        for boq_item_id in affected_boq_item_ids:
            sync_service._update_boq_item_totals(boq_item_id)

    if updated:
        logger.info(
            "Pushed calc sheet %s quantities to %s concentration entries",
            calculation_sheet.calculation_sheet_no,
            updated,
        )
    return CalcSheetPushResult(
        entries_updated=updated,
        affected_boq_item_ids=affected_boq_item_ids,
    )


def export_pdfs_for_boq_items(
    db: Session, project_id: str, boq_item_ids: Set[int]
) -> int:
    """Export concentration sheet PDFs for the given BOQ items."""
    if not boq_item_ids:
        return 0
    pdf_service = PDFService(exports_dir=get_project_export_dir(project_id))
    return pdf_service.export_concentration_sheets_for_boq_items(
        list(boq_item_ids), db
    )


def finalize_calculation_sheet_changes(
    db: Session,
    project_id: str,
    base_message: str,
    push_result: CalcSheetPushResult,
) -> str:
    """
    After a calc sheet push, export PDFs only for affected BOQ items.
    Does not re-sync unrelated calculation sheets (use sync-all for that).
    """
    if not push_result.entries_updated and not push_result.affected_boq_item_ids:
        return base_message

    try:
        pdfs_exported = export_pdfs_for_boq_items(
            db, project_id, push_result.affected_boq_item_ids
        )
    except Exception as e:
        logger.error("PDF export after calc sheet push failed: %s", e)
        return f"{base_message} PDF export failed: {e}."

    boq_count = len(push_result.affected_boq_item_ids)
    return (
        f"{base_message} Updated {push_result.entries_updated} concentration "
        f"entries, {boq_count} BOQ item(s), exported {pdfs_exported} concentration sheet PDF(s)."
    )


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
        concentration_sheets_exported = export_pdfs_for_boq_items(
            db, project_id, set(boq_items_to_export)
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
    """Append a human-readable sync summary to a sync-all message."""
    if not sync_result.get("success"):
        logger.warning(
            "Sync-all failed: %s",
            sync_result.get("message"),
        )
        return (
            f"{base_message} Sync failed: "
            f"{sync_result.get('message', 'unknown error')}."
        )

    details = sync_result.get("details") or {}
    return (
        f"{base_message} Synced: {details.get('entries_updated', 0)} concentration "
        f"entries updated, {details.get('boq_items_updated', 0)} BOQ items updated, "
        f"{details.get('concentration_sheets_exported', 0)} concentration sheet PDFs exported."
    )
