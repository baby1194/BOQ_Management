"""
Synchronization Service for Calculation Sheets, Concentration Sheets, and BOQ Items

This service handles automatic synchronization when calculation sheets are modified,
ensuring that changes propagate to concentration sheets and BOQ items.
"""

from sqlalchemy.orm import Session
from typing import List, Dict, Optional
import logging
from models import models
from utils.concentration_utils import (
    entry_cumulative_submitted,
    prune_stale_concentration_entries_for_calc_sheet,
    sync_calc_entry_to_concentration,
)
from utils.period_details_utils import (
    entry_total_approved_quantity,
    entry_total_internal_quantity,
)

logger = logging.getLogger(__name__)

class SyncService:
    """Service for synchronizing data between calculation sheets, concentration sheets, and BOQ items"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def sync_calculation_sheet_deletion(self, calculation_sheet_id: int) -> Dict[str, any]:
        """
        Handle synchronization when a calculation sheet is deleted.
        This will remove related concentration entries and update BOQ items.
        """
        try:
            # Get the calculation sheet before deletion to get its details
            calculation_sheet = self.db.query(models.CalculationSheet).filter(
                models.CalculationSheet.id == calculation_sheet_id
            ).first()
            
            if not calculation_sheet:
                logger.warning(f"Calculation sheet {calculation_sheet_id} not found for sync")
                return {"success": False, "message": "Calculation sheet not found"}
            
            calculation_sheet_no = calculation_sheet.calculation_sheet_no
            
            logger.info(f"Syncing deletion of calculation sheet {calculation_sheet_no} (ID: {calculation_sheet_id})")
            
            # Find all concentration entries that reference this calculation sheet
            concentration_entries = self.db.query(models.ConcentrationEntry).filter(
                models.ConcentrationEntry.calculation_sheet_no == calculation_sheet_no,
            ).all()
            
            entries_deleted = 0
            boq_items_updated = 0
            
            if concentration_entries:
                # Group entries by concentration sheet
                concentration_sheets_affected = {}
                for entry in concentration_entries:
                    sheet_id = entry.concentration_sheet_id
                    if sheet_id not in concentration_sheets_affected:
                        concentration_sheets_affected[sheet_id] = []
                    concentration_sheets_affected[sheet_id].append(entry)
                
                # Delete concentration entries first
                for sheet_id, entries in concentration_sheets_affected.items():
                    for entry in entries:
                        self.db.delete(entry)
                        entries_deleted += 1
                
                # Commit the deletions first
                self.db.commit()
                
                # Update BOQ item totals after deletions are committed
                for sheet_id, entries in concentration_sheets_affected.items():
                    concentration_sheet = self.db.query(models.ConcentrationSheet).filter(
                        models.ConcentrationSheet.id == sheet_id
                    ).first()
                    
                    if concentration_sheet:
                        updated = self._update_boq_item_totals(concentration_sheet.boq_item_id)
                        if updated:
                            boq_items_updated += 1
                
                logger.info(f"Deleted {entries_deleted} concentration entries and updated {boq_items_updated} BOQ items")
            
            return {
                "success": True,
                "message": f"Successfully synced deletion of calculation sheet {calculation_sheet_no}",
                "entries_deleted": entries_deleted,
                "boq_items_updated": boq_items_updated
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error syncing calculation sheet deletion: {str(e)}")
            return {"success": False, "message": f"Error syncing deletion: {str(e)}"}
    
    def sync_calculation_entry_deletion(self, calculation_entry_id: int) -> Dict[str, any]:
        """
        Handle synchronization when a calculation entry is deleted.
        This will remove related concentration entries and update BOQ items.
        """
        try:
            # Get the calculation entry before deletion
            calculation_entry = self.db.query(models.CalculationEntry).filter(
                models.CalculationEntry.id == calculation_entry_id
            ).first()
            
            if not calculation_entry:
                logger.warning(f"Calculation entry {calculation_entry_id} not found for sync")
                return {"success": False, "message": "Calculation entry not found"}
            
            # Get the calculation sheet details
            calculation_sheet = self.db.query(models.CalculationSheet).filter(
                models.CalculationSheet.id == calculation_entry.calculation_sheet_id
            ).first()
            
            if not calculation_sheet:
                logger.warning(f"Calculation sheet for entry {calculation_entry_id} not found")
                return {"success": False, "message": "Calculation sheet not found"}
            
            section_number = calculation_entry.section_number
            calculation_sheet_no = calculation_sheet.calculation_sheet_no
            
            logger.info(f"Syncing deletion of calculation entry for section {section_number}")
            
            # Find the corresponding concentration entry
            concentration_entry = self.db.query(models.ConcentrationEntry).filter(
                models.ConcentrationEntry.section_number == section_number,
                models.ConcentrationEntry.calculation_sheet_no == calculation_sheet_no,
            ).first()
            
            entries_deleted = 0
            boq_items_updated = 0
            
            if concentration_entry:
                concentration_sheet_id = concentration_entry.concentration_sheet_id
                
                # Delete the concentration entry
                self.db.delete(concentration_entry)
                entries_deleted = 1
                
                # Commit the deletion first
                self.db.commit()
                
                # Update BOQ item totals after deletion is committed
                concentration_sheet = self.db.query(models.ConcentrationSheet).filter(
                    models.ConcentrationSheet.id == concentration_sheet_id
                ).first()
                
                if concentration_sheet:
                    updated = self._update_boq_item_totals(concentration_sheet.boq_item_id)
                    if updated:
                        boq_items_updated = 1
                
                logger.info(f"Deleted concentration entry for section {section_number} and updated BOQ item")
            
            return {
                "success": True,
                "message": f"Successfully synced deletion of calculation entry for section {section_number}",
                "entries_deleted": entries_deleted,
                "boq_items_updated": boq_items_updated
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error syncing calculation entry deletion: {str(e)}")
            return {"success": False, "message": f"Error syncing deletion: {str(e)}"}
    
    def sync_calculation_entry_update(self, calculation_entry_id: int) -> Dict[str, any]:
        """
        Handle synchronization when a calculation entry is updated.
        This will update related concentration entries and BOQ items.
        """
        try:
            # Get the updated calculation entry
            calculation_entry = self.db.query(models.CalculationEntry).filter(
                models.CalculationEntry.id == calculation_entry_id
            ).first()
            
            if not calculation_entry:
                logger.warning(f"Calculation entry {calculation_entry_id} not found for sync")
                return {"success": False, "message": "Calculation entry not found"}
            
            # Get the calculation sheet details
            calculation_sheet = self.db.query(models.CalculationSheet).filter(
                models.CalculationSheet.id == calculation_entry.calculation_sheet_id
            ).first()
            
            if not calculation_sheet:
                logger.warning(f"Calculation sheet for entry {calculation_entry_id} not found")
                return {"success": False, "message": "Calculation sheet not found"}
            
            logger.info(f"Syncing update of calculation entry for section {calculation_entry.section_number}")

            boq_item_id = sync_calc_entry_to_concentration(
                self.db, calculation_entry, calculation_sheet
            )
            entries_updated = 1 if boq_item_id is not None else 0
            boq_items_updated = 0

            if boq_item_id is not None:
                updated = self._update_boq_item_totals(boq_item_id)
                if updated:
                    boq_items_updated = 1
                self.db.commit()
                logger.info(
                    f"Updated concentration entry for section {calculation_entry.section_number} and updated BOQ item"
                )

            return {
                "success": True,
                "message": f"Successfully synced update of calculation entry for section {calculation_entry.section_number}",
                "entries_updated": entries_updated,
                "boq_items_updated": boq_items_updated
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error syncing calculation entry update: {str(e)}")
            return {"success": False, "message": f"Error syncing update: {str(e)}"}
    
    def _update_boq_item_totals(self, boq_item_id: int) -> bool:
        """
        Helper function to update BOQ Item totals based on concentration entries.
        Returns True if the BOQ item was updated, False otherwise.
        """
        try:
            # Get the BOQ item
            boq_item = self.db.query(models.BOQItem).filter(models.BOQItem.id == boq_item_id).first()
            if not boq_item:
                return False
            
            # Get all concentration entries for this BOQ item's concentration sheet
            concentration_sheet = self.db.query(models.ConcentrationSheet).filter(
                models.ConcentrationSheet.boq_item_id == boq_item_id
            ).first()
            
            if not concentration_sheet:
                return False

            self.db.flush()

            entries = self.db.query(models.ConcentrationEntry).filter(
                models.ConcentrationEntry.concentration_sheet_id == concentration_sheet.id
            ).all()
            
            # Calculate totals (even if no entries, totals will be 0)
            total_estimated = sum(entry.estimated_quantity for entry in entries)
            total_submitted = sum(entry_cumulative_submitted(entry) for entry in entries)
            total_internal = sum(entry_total_internal_quantity(entry) for entry in entries)
            total_approved = sum(entry_total_approved_quantity(entry) for entry in entries)
            
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
            
            logger.info(f"Updated BOQ item {boq_item.section_number} totals: Est={total_estimated}, Submitted={total_submitted}, Internal={total_internal}, Approved={total_approved}")
            self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error updating BOQ item totals: {str(e)}")
            return False
    
    def sync_all_calculation_sheets(self) -> Dict[str, any]:
        """
        Synchronize all calculation sheets with concentration sheets and BOQ items.
        This is useful for ensuring data consistency across the entire system.
        """
        try:
            logger.info("Starting full synchronization of all calculation sheets")
            
            # Get all calculation sheets
            calculation_sheets = self.db.query(models.CalculationSheet).all()
            
            total_entries_updated = 0
            total_boq_items_updated = 0
            processed_sheets = 0
            boq_items_to_export: set[int] = set()
            
            for calculation_sheet in calculation_sheets:
                try:
                    # Get all calculation entries for this sheet
                    calculation_entries = self.db.query(models.CalculationEntry).filter(
                        models.CalculationEntry.calculation_sheet_id == calculation_sheet.id
                    ).all()

                    # For each calculation entry, find and update the corresponding concentration entry
                    for calc_entry in calculation_entries:
                        boq_item_id = sync_calc_entry_to_concentration(
                            self.db, calc_entry, calculation_sheet
                        )
                        if boq_item_id is not None:
                            total_entries_updated += 1
                            boq_items_to_export.add(boq_item_id)

                    removed, pruned_boq_item_ids = (
                        prune_stale_concentration_entries_for_calc_sheet(
                            self.db, calculation_sheet
                        )
                    )
                    if removed:
                        total_entries_updated += removed
                        logger.info(
                            "Removed %s stale concentration entries for calc sheet %s",
                            removed,
                            calculation_sheet.calculation_sheet_no,
                        )

                    # Update BOQ items for this sheet
                    section_numbers = [
                        entry.section_number for entry in calculation_entries
                    ]
                    matching_boq_items = self.db.query(models.BOQItem).filter(
                        models.BOQItem.section_number.in_(section_numbers)
                    ).all() if section_numbers else []

                    boq_ids_to_update = pruned_boq_item_ids | {
                        boq_item.id for boq_item in matching_boq_items
                    }
                    for boq_item_id in boq_ids_to_update:
                        updated = self._update_boq_item_totals(boq_item_id)
                        if updated:
                            total_boq_items_updated += 1
                            boq_items_to_export.add(boq_item_id)
                    
                    processed_sheets += 1
                    
                except Exception as e:
                    logger.error(f"Error processing calculation sheet {calculation_sheet.calculation_sheet_no}: {str(e)}")
                    continue
            
            self.db.commit()
            
            logger.info(f"Full synchronization completed. Processed {processed_sheets} sheets, updated {total_entries_updated} entries, updated {total_boq_items_updated} BOQ items")
            
            return {
                "success": True,
                "message": f"Successfully synchronized {processed_sheets} calculation sheets",
                "entries_updated": total_entries_updated,
                "boq_items_updated": total_boq_items_updated,
                "sheets_processed": processed_sheets,
                "boq_items_to_export": list(boq_items_to_export),
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error in full synchronization: {str(e)}")
            return {"success": False, "message": f"Error in full synchronization: {str(e)}"}
