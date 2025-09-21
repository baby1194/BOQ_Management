from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging
import os
from pathlib import Path
from datetime import datetime

from database.database import get_db
from models import models
from schemas import schemas
from services.pdf_service import PDFService
from services.excel_service import ExcelService

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/concentration-sheets", response_model=schemas.PDFExportResponse)
async def export_concentration_sheets(
    request: schemas.PDFExportRequest,
    db: Session = Depends(get_db)
):
    """Export concentration sheets to PDF"""
    try:
        pdf_service = PDFService()
        
        # Get concentration sheets to export
        if request.export_all:
            sheets = db.query(models.ConcentrationSheet).all()
        else:
            # This would need to be implemented based on item_codes
            sheets = db.query(models.ConcentrationSheet).all()
        
        # Filter out empty sheets if requested
        if request.export_non_empty_only:
            sheets = [sheet for sheet in sheets if sheet.total_estimate > 0 or sheet.total_submitted > 0]
        
        if not sheets:
            return schemas.PDFExportResponse(
                success=False,
                message="No concentration sheets found to export",
                sheets_exported=0
            )
        
        # Generate PDF
        pdf_path = pdf_service.export_concentration_sheets(sheets, db)
        
        return schemas.PDFExportResponse(
            success=True,
            message=f"Successfully exported {len(sheets)} concentration sheets",
            pdf_path=pdf_path,
            sheets_exported=len(sheets)
        )
        
    except Exception as e:
        logger.error(f"Error exporting concentration sheets: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/concentration-sheet/{sheet_id}", response_model=schemas.PDFExportResponse)
async def export_single_concentration_sheet(
    sheet_id: int,
    db: Session = Depends(get_db)
):
    """Export a single concentration sheet to PDF"""
    try:
        # Get the concentration sheet with BOQ item and entries
        sheet = db.query(models.ConcentrationSheet).filter(
            models.ConcentrationSheet.id == sheet_id
        ).first()
        
        if not sheet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Concentration sheet not found"
            )
        
        # Get BOQ item
        boq_item = db.query(models.BOQItem).filter(
            models.BOQItem.id == sheet.boq_item_id
        ).first()
        
        # Get entries
        entries = db.query(models.ConcentrationEntry).filter(
            models.ConcentrationEntry.concentration_sheet_id == sheet_id
        ).order_by(models.ConcentrationEntry.id).all()
        
        pdf_service = PDFService()
        pdf_path = pdf_service.export_single_concentration_sheet(sheet, boq_item, entries, db)
        
        # Return the filename for download
        filename = pdf_path.split('/')[-1] if '/' in pdf_path else pdf_path.split('\\')[-1]
        return schemas.PDFExportResponse(
            success=True,
            message=f"Successfully exported concentration sheet: {sheet.sheet_name}",
            pdf_path=f"/export/download/{filename}",
            sheets_exported=1
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting concentration sheet {sheet_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/concentration-sheet/{sheet_id}/excel", response_model=schemas.PDFExportResponse)
async def export_single_concentration_sheet_excel(
    sheet_id: int,
    db: Session = Depends(get_db)
):
    """Export a single concentration sheet to Excel"""
    try:
        # Get the concentration sheet with BOQ item and entries
        sheet = db.query(models.ConcentrationSheet).filter(
            models.ConcentrationSheet.id == sheet_id
        ).first()
        
        if not sheet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Concentration sheet not found"
            )
        
        # Get BOQ item
        boq_item = db.query(models.BOQItem).filter(
            models.BOQItem.id == sheet.boq_item_id
        ).first()
        
        # Get entries
        entries = db.query(models.ConcentrationEntry).filter(
            models.ConcentrationEntry.concentration_sheet_id == sheet_id
        ).order_by(models.ConcentrationEntry.id).all()
        
        excel_service = ExcelService()
        excel_path = excel_service.export_single_concentration_sheet(sheet, boq_item, entries)
        
        # Return the filename for download
        filename = excel_path.split('/')[-1] if '/' in excel_path else excel_path.split('\\')[-1]
        return schemas.PDFExportResponse(
            success=True,
            message=f"Successfully exported concentration sheet to Excel: {sheet.sheet_name}",
            pdf_path=f"/export/download/{filename}",
            sheets_exported=1
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting concentration sheet to Excel {sheet_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/summary", response_model=schemas.PDFExportResponse)
async def export_summary(db: Session = Depends(get_db)):
    """Export summary report to PDF"""
    try:
        pdf_service = PDFService()
        
        # Get summary data
        from sqlalchemy import func
        
        summary_data = db.query(
            models.BOQItem.subsection,
            func.count(models.BOQItem.id).label('item_count'),
            func.sum(models.BOQItem.total_estimate).label('total_estimate'),
            func.sum(models.BOQItem.total_submitted).label('total_submitted'),
            func.sum(models.BOQItem.internal_total).label('total_pnimi'),
            func.sum(models.BOQItem.total_approved_by_project_manager).label('total_approved')
        ).filter(
            models.BOQItem.subsection.isnot(None)
        ).group_by(models.BOQItem.subsection).all()
        
        # Generate PDF
        pdf_path = pdf_service.export_summary(summary_data, db)
        
        return schemas.PDFExportResponse(
            success=True,
            message=f"Successfully exported summary report",
            pdf_path=pdf_path,
            sheets_exported=len(summary_data)
        )
        
    except Exception as e:
        logger.error(f"Error exporting summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/structures-summary", response_model=schemas.PDFExportResponse)
async def export_structures_summary(
    request: schemas.SummaryExportRequest,
    db: Session = Depends(get_db)
):
    """Export structures summary to PDF"""
    try:
        pdf_service = PDFService()
        
        # Use the data passed from frontend if available, otherwise fetch from database
        if request.data:
            summaries = request.data
        else:
            from routers.structures import get_structure_summaries
            summaries = await get_structure_summaries(db)
        
        # Get contract updates for dynamic columns
        contract_updates = db.query(models.ContractQuantityUpdate).order_by(models.ContractQuantityUpdate.update_index).all()
        
        # Filter columns based on request
        filtered_summaries = []
        for summary in summaries:
            filtered_summary = {}
            # Handle both dictionary and object access
            if request.include_structure:
                filtered_summary["structure"] = summary.get("structure") if isinstance(summary, dict) else summary.structure
            if request.include_description:
                filtered_summary["description"] = summary.get("description") if isinstance(summary, dict) else summary.description
            if request.include_total_contract_sum:
                filtered_summary["total_contract_sum"] = summary.get("total_contract_sum") if isinstance(summary, dict) else summary.total_contract_sum
            if request.include_total_estimate:
                filtered_summary["total_estimate"] = summary.get("total_estimate") if isinstance(summary, dict) else summary.total_estimate
            if request.include_total_submitted:
                filtered_summary["total_submitted"] = summary.get("total_submitted") if isinstance(summary, dict) else summary.total_submitted
            if request.include_internal_total:
                filtered_summary["internal_total"] = summary.get("internal_total") if isinstance(summary, dict) else summary.internal_total
            if request.include_total_approved:
                filtered_summary["total_approved"] = summary.get("total_approved") if isinstance(summary, dict) else summary.total_approved
            if request.include_approved_signed_total:
                filtered_summary["approved_signed_total"] = summary.get("approved_signed_total") if isinstance(summary, dict) else summary.approved_signed_total
            if request.include_item_count:
                filtered_summary["item_count"] = summary.get("item_count") if isinstance(summary, dict) else summary.item_count
            
            # Add contract update columns if requested
            if request.include_contract_updates:
                contract_update_sums = summary.get("contract_update_sums") if isinstance(summary, dict) else summary.contract_update_sums
                logger.info(f"Processing contract updates for summary {summary.get('structure', 'unknown')}: {contract_update_sums}")
                if contract_update_sums:
                    for update in contract_updates:
                        update_id = update.id
                        # Convert update_id to string to match contract_update_sums keys
                        if str(update_id) in contract_update_sums:
                            column_name = f"total_updated_contract_sum_{update_id}"
                            filtered_summary[column_name] = contract_update_sums[str(update_id)]
                            logger.info(f"Added column {column_name} = {contract_update_sums[str(update_id)]}")
            
            if filtered_summary:  # Only add if at least one column is selected
                filtered_summaries.append(filtered_summary)
        
        logger.info(f"Final filtered summaries keys: {[list(s.keys()) for s in filtered_summaries]}")
        logger.info(f"First filtered summary: {filtered_summaries[0] if filtered_summaries else 'None'}")
        
        # Generate PDF
        pdf_path = pdf_service.export_structures_summary(filtered_summaries, db)
        
        # Return the filename for download using the download endpoint
        filename = pdf_path.split('/')[-1] if '/' in pdf_path else pdf_path.split('\\')[-1]
        return schemas.PDFExportResponse(
            success=True,
            message=f"Successfully exported structures summary",
            pdf_path=f"/export/download/{filename}",
            sheets_exported=len(filtered_summaries)
        )
        
    except Exception as e:
        logger.error(f"Error exporting structures summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/systems-summary", response_model=schemas.PDFExportResponse)
async def export_systems_summary(
    request: schemas.SummaryExportRequest,
    db: Session = Depends(get_db)
):
    """Export systems summary to PDF"""
    try:
        pdf_service = PDFService()
        
        # Use the data passed from frontend if available, otherwise fetch from database
        if request.data:
            summaries = request.data
        else:
            from routers.systems import get_system_summaries
            summaries = await get_system_summaries(db)
        
        # Get contract updates for dynamic columns
        contract_updates = db.query(models.ContractQuantityUpdate).order_by(models.ContractQuantityUpdate.update_index).all()
        
        # Filter columns based on request
        filtered_summaries = []
        for summary in summaries:
            filtered_summary = {}
            # Handle both dictionary and object access
            if request.include_structure:
                filtered_summary["system"] = summary.get("system") if isinstance(summary, dict) else summary.system
            if request.include_description:
                filtered_summary["description"] = summary.get("description") if isinstance(summary, dict) else summary.description
            if request.include_total_contract_sum:
                filtered_summary["total_contract_sum"] = summary.get("total_contract_sum") if isinstance(summary, dict) else summary.total_contract_sum
            if request.include_total_estimate:
                filtered_summary["total_estimate"] = summary.get("total_estimate") if isinstance(summary, dict) else summary.total_estimate
            if request.include_total_submitted:
                filtered_summary["total_submitted"] = summary.get("total_submitted") if isinstance(summary, dict) else summary.total_submitted
            if request.include_internal_total:
                filtered_summary["internal_total"] = summary.get("internal_total") if isinstance(summary, dict) else summary.internal_total
            if request.include_total_approved:
                filtered_summary["total_approved"] = summary.get("total_approved") if isinstance(summary, dict) else summary.total_approved
            if request.include_approved_signed_total:
                filtered_summary["approved_signed_total"] = summary.get("approved_signed_total") if isinstance(summary, dict) else summary.approved_signed_total
            if request.include_item_count:
                filtered_summary["item_count"] = summary.get("item_count") if isinstance(summary, dict) else summary.item_count
            
            # Add contract update columns if requested
            if request.include_contract_updates:
                contract_update_sums = summary.get("contract_update_sums") if isinstance(summary, dict) else summary.contract_update_sums
                if contract_update_sums:
                    for update in contract_updates:
                        update_id = update.id
                        if str(update_id) in contract_update_sums:
                            filtered_summary[f"total_updated_contract_sum_{update_id}"] = contract_update_sums[str(update_id)]
            
            if filtered_summary:  # Only add if at least one column is selected
                filtered_summaries.append(filtered_summary)
        
        # Generate PDF
        pdf_path = pdf_service.export_systems_summary(filtered_summaries, db)
        
        # Return the filename for download using the download endpoint
        filename = pdf_path.split('/')[-1] if '/' in pdf_path else pdf_path.split('\\')[-1]
        return schemas.PDFExportResponse(
            success=True,
            message=f"Successfully exported systems summary",
            pdf_path=f"/export/download/{filename}",
            sheets_exported=len(filtered_summaries)
        )
        
    except Exception as e:
        logger.error(f"Error exporting systems summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/subsections-summary", response_model=schemas.PDFExportResponse)
async def export_subsections_summary(
    request: schemas.SummaryExportRequest,
    db: Session = Depends(get_db)
):
    """Export subsections summary to PDF"""
    try:
        pdf_service = PDFService()
        
        # Use the data passed from frontend if available, otherwise fetch from database
        if request.data:
            summaries = request.data
        else:
            from routers.subsections import get_subsection_summaries
            summaries = await get_subsection_summaries(db)
        
        # Get contract updates for dynamic columns
        contract_updates = db.query(models.ContractQuantityUpdate).order_by(models.ContractQuantityUpdate.update_index).all()
        
        # Filter columns based on request
        filtered_summaries = []
        for summary in summaries:
            filtered_summary = {}
            # Handle both dictionary and object access
            if request.include_structure:
                filtered_summary["subsection"] = summary.get("subsection") if isinstance(summary, dict) else summary.subsection
            if request.include_description:
                filtered_summary["description"] = summary.get("description") if isinstance(summary, dict) else summary.description
            if request.include_total_contract_sum:
                filtered_summary["total_contract_sum"] = summary.get("total_contract_sum") if isinstance(summary, dict) else summary.total_contract_sum
            if request.include_total_estimate:
                filtered_summary["total_estimate"] = summary.get("total_estimate") if isinstance(summary, dict) else summary.total_estimate
            if request.include_total_submitted:
                filtered_summary["total_submitted"] = summary.get("total_submitted") if isinstance(summary, dict) else summary.total_submitted
            if request.include_internal_total:
                filtered_summary["internal_total"] = summary.get("internal_total") if isinstance(summary, dict) else summary.internal_total
            if request.include_total_approved:
                filtered_summary["total_approved"] = summary.get("total_approved") if isinstance(summary, dict) else summary.total_approved
            if request.include_approved_signed_total:
                filtered_summary["approved_signed_total"] = summary.get("approved_signed_total") if isinstance(summary, dict) else summary.approved_signed_total
            if request.include_item_count:
                filtered_summary["item_count"] = summary.get("item_count") if isinstance(summary, dict) else summary.item_count
            
            # Add contract update columns if requested
            if request.include_contract_updates:
                contract_update_sums = summary.get("contract_update_sums") if isinstance(summary, dict) else summary.contract_update_sums
                if contract_update_sums:
                    for update in contract_updates:
                        update_id = update.id
                        if str(update_id) in contract_update_sums:
                            filtered_summary[f"total_updated_contract_sum_{update_id}"] = contract_update_sums[str(update_id)]
            
            if filtered_summary:  # Only add if at least one column is selected
                filtered_summaries.append(filtered_summary)
        
        # Generate PDF
        pdf_path = pdf_service.export_subsections_summary(filtered_summaries, db)
        
        # Return the filename for download using the download endpoint
        filename = pdf_path.split('/')[-1] if '/' in pdf_path else pdf_path.split('\\')[-1]
        return schemas.PDFExportResponse(
            success=True,
            message=f"Successfully exported subsections summary",
            pdf_path=f"/export/download/{filename}",
            sheets_exported=len(filtered_summaries)
        )
        
    except Exception as e:
        logger.error(f"Error exporting subsections summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/structures-summary/excel", response_model=schemas.PDFExportResponse)
async def export_structures_summary_excel(
    request: schemas.SummaryExportRequest,
    db: Session = Depends(get_db)
):
    """Export structures summary to Excel"""
    try:
        excel_service = ExcelService()
        
        # Use the data passed from frontend if available, otherwise fetch from database
        if request.data:
            summaries = request.data
        else:
            from routers.structures import get_structure_summaries
            summaries = await get_structure_summaries(db)
        
        # Get contract updates for dynamic columns
        contract_updates = db.query(models.ContractQuantityUpdate).order_by(models.ContractQuantityUpdate.update_index).all()
        
        # Filter columns based on request
        filtered_summaries = []
        for summary in summaries:
            filtered_summary = {}
            # Handle both dictionary and object access
            if request.include_structure:
                filtered_summary["structure"] = summary.get("structure") if isinstance(summary, dict) else summary.structure
            if request.include_description:
                filtered_summary["description"] = summary.get("description") if isinstance(summary, dict) else summary.description
            if request.include_total_contract_sum:
                filtered_summary["total_contract_sum"] = summary.get("total_contract_sum") if isinstance(summary, dict) else summary.total_contract_sum
            if request.include_total_estimate:
                filtered_summary["total_estimate"] = summary.get("total_estimate") if isinstance(summary, dict) else summary.total_estimate
            if request.include_total_submitted:
                filtered_summary["total_submitted"] = summary.get("total_submitted") if isinstance(summary, dict) else summary.total_submitted
            if request.include_internal_total:
                filtered_summary["internal_total"] = summary.get("internal_total") if isinstance(summary, dict) else summary.internal_total
            if request.include_total_approved:
                filtered_summary["total_approved"] = summary.get("total_approved") if isinstance(summary, dict) else summary.total_approved
            if request.include_approved_signed_total:
                filtered_summary["approved_signed_total"] = summary.get("approved_signed_total") if isinstance(summary, dict) else summary.approved_signed_total
            if request.include_item_count:
                filtered_summary["item_count"] = summary.get("item_count") if isinstance(summary, dict) else summary.item_count
            
            # Add contract update columns if requested
            if request.include_contract_updates:
                contract_update_sums = summary.get("contract_update_sums") if isinstance(summary, dict) else summary.contract_update_sums
                if contract_update_sums:
                    for update in contract_updates:
                        update_id = update.id
                        if str(update_id) in contract_update_sums:
                            filtered_summary[f"total_updated_contract_sum_{update_id}"] = contract_update_sums[str(update_id)]
            
            if filtered_summary:  # Only add if at least one column is selected
                filtered_summaries.append(filtered_summary)
        
        # Generate Excel
        excel_path = excel_service.export_structures_summary(filtered_summaries)
        
        # Return the filename for download using the download endpoint
        filename = excel_path.split('/')[-1] if '/' in excel_path else excel_path.split('\\')[-1]
        return schemas.PDFExportResponse(
            success=True,
            message=f"Successfully exported structures summary to Excel",
            pdf_path=f"/export/download/{filename}",
            sheets_exported=len(filtered_summaries)
        )
        
    except Exception as e:
        logger.error(f"Error exporting structures summary to Excel: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/systems-summary/excel", response_model=schemas.PDFExportResponse)
async def export_systems_summary_excel(
    request: schemas.SummaryExportRequest,
    db: Session = Depends(get_db)
):
    """Export systems summary to Excel"""
    try:
        excel_service = ExcelService()
        
        # Use the data passed from frontend if available, otherwise fetch from database
        if request.data:
            summaries = request.data
        else:
            from routers.systems import get_system_summaries
            summaries = await get_system_summaries(db)
        
        # Get contract updates for dynamic columns
        contract_updates = db.query(models.ContractQuantityUpdate).order_by(models.ContractQuantityUpdate.update_index).all()
        
        # Filter columns based on request
        filtered_summaries = []
        for summary in summaries:
            filtered_summary = {}
            # Handle both dictionary and object access
            if request.include_structure:
                filtered_summary["system"] = summary.get("system") if isinstance(summary, dict) else summary.system
            if request.include_description:
                filtered_summary["description"] = summary.get("description") if isinstance(summary, dict) else summary.description
            if request.include_total_contract_sum:
                filtered_summary["total_contract_sum"] = summary.get("total_contract_sum") if isinstance(summary, dict) else summary.total_contract_sum
            if request.include_total_estimate:
                filtered_summary["total_estimate"] = summary.get("total_estimate") if isinstance(summary, dict) else summary.total_estimate
            if request.include_total_submitted:
                filtered_summary["total_submitted"] = summary.get("total_submitted") if isinstance(summary, dict) else summary.total_submitted
            if request.include_internal_total:
                filtered_summary["internal_total"] = summary.get("internal_total") if isinstance(summary, dict) else summary.internal_total
            if request.include_total_approved:
                filtered_summary["total_approved"] = summary.get("total_approved") if isinstance(summary, dict) else summary.total_approved
            if request.include_approved_signed_total:
                filtered_summary["approved_signed_total"] = summary.get("approved_signed_total") if isinstance(summary, dict) else summary.approved_signed_total
            if request.include_item_count:
                filtered_summary["item_count"] = summary.get("item_count") if isinstance(summary, dict) else summary.item_count
            
            # Add contract update columns if requested
            if request.include_contract_updates:
                contract_update_sums = summary.get("contract_update_sums") if isinstance(summary, dict) else summary.contract_update_sums
                if contract_update_sums:
                    for update in contract_updates:
                        update_id = update.id
                        if str(update_id) in contract_update_sums:
                            filtered_summary[f"total_updated_contract_sum_{update_id}"] = contract_update_sums[str(update_id)]
            
            if filtered_summary:  # Only add if at least one column is selected
                filtered_summaries.append(filtered_summary)
        
        # Generate Excel
        excel_path = excel_service.export_systems_summary(filtered_summaries)
        
        # Return the filename for download using the download endpoint
        filename = excel_path.split('/')[-1] if '/' in excel_path else excel_path.split('\\')[-1]
        return schemas.PDFExportResponse(
            success=True,
            message=f"Successfully exported systems summary to Excel",
            pdf_path=f"/export/download/{filename}",
            sheets_exported=len(filtered_summaries)
        )
        
    except Exception as e:
        logger.error(f"Error exporting systems summary to Excel: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/subsections-summary/excel", response_model=schemas.PDFExportResponse)
async def export_subsections_summary_excel(
    request: schemas.SummaryExportRequest,
    db: Session = Depends(get_db)
):
    """Export subsections summary to Excel"""
    try:
        excel_service = ExcelService()
        
        # Use the data passed from frontend if available, otherwise fetch from database
        if request.data:
            summaries = request.data
        else:
            from routers.subsections import get_subsection_summaries
            summaries = await get_subsection_summaries(db)
        
        # Get contract updates for dynamic columns
        contract_updates = db.query(models.ContractQuantityUpdate).order_by(models.ContractQuantityUpdate.update_index).all()
        
        # Filter columns based on request
        filtered_summaries = []
        for summary in summaries:
            filtered_summary = {}
            # Handle both dictionary and object access
            if request.include_structure:
                filtered_summary["subsection"] = summary.get("subsection") if isinstance(summary, dict) else summary.subsection
            if request.include_description:
                filtered_summary["description"] = summary.get("description") if isinstance(summary, dict) else summary.description
            if request.include_total_contract_sum:
                filtered_summary["total_contract_sum"] = summary.get("total_contract_sum") if isinstance(summary, dict) else summary.total_contract_sum
            if request.include_total_estimate:
                filtered_summary["total_estimate"] = summary.get("total_estimate") if isinstance(summary, dict) else summary.total_estimate
            if request.include_total_submitted:
                filtered_summary["total_submitted"] = summary.get("total_submitted") if isinstance(summary, dict) else summary.total_submitted
            if request.include_internal_total:
                filtered_summary["internal_total"] = summary.get("internal_total") if isinstance(summary, dict) else summary.internal_total
            if request.include_total_approved:
                filtered_summary["total_approved"] = summary.get("total_approved") if isinstance(summary, dict) else summary.total_approved
            if request.include_approved_signed_total:
                filtered_summary["approved_signed_total"] = summary.get("approved_signed_total") if isinstance(summary, dict) else summary.approved_signed_total
            if request.include_item_count:
                filtered_summary["item_count"] = summary.get("item_count") if isinstance(summary, dict) else summary.item_count
            
            # Add contract update columns if requested
            if request.include_contract_updates:
                contract_update_sums = summary.get("contract_update_sums") if isinstance(summary, dict) else summary.contract_update_sums
                if contract_update_sums:
                    for update in contract_updates:
                        update_id = update.id
                        if str(update_id) in contract_update_sums:
                            filtered_summary[f"total_updated_contract_sum_{update_id}"] = contract_update_sums[str(update_id)]
            
            if filtered_summary:  # Only add if at least one column is selected
                filtered_summaries.append(filtered_summary)
        
        # Generate Excel
        excel_path = excel_service.export_subsections_summary(filtered_summaries)
        
        # Return the filename for download using the download endpoint
        filename = excel_path.split('/')[-1] if '/' in excel_path else excel_path.split('\\')[-1]
        return schemas.PDFExportResponse(
            success=True,
            message=f"Successfully exported subsections summary to Excel",
            pdf_path=f"/export/download/{filename}",
            sheets_exported=len(filtered_summaries)
        )
        
    except Exception as e:
        logger.error(f"Error exporting subsections summary to Excel: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/boq-items/pdf", response_model=schemas.PDFExportResponse)
async def export_boq_items_pdf(
    request: dict,
    db: Session = Depends(get_db)
):
    """Export BOQ items to PDF"""
    try:
        pdf_service = PDFService()
        
        # Use the data passed from frontend if available, otherwise fetch from database
        if "data" in request and request["data"]:
            # Frontend sends filtered data with contract updates included
            filtered_items = request["data"]
        else:
            # Fallback: fetch from database and apply filtering
            items = db.query(models.BOQItem).all()
            contract_updates = db.query(models.ContractQuantityUpdate).order_by(models.ContractQuantityUpdate.update_index).all()
            
            filtered_items = []
            for item in items:
                filtered_item = {}
                
                # Process columns in BOQ table order
                if request.get("include_serial_number"):
                    filtered_item["serial_number"] = item.serial_number
                if request.get("include_structure"):
                    filtered_item["structure"] = item.structure
                if request.get("include_system"):
                    filtered_item["system"] = item.system
                if request.get("include_section_number"):
                    filtered_item["section_number"] = item.section_number
                if request.get("include_description"):
                    filtered_item["description"] = item.description
                if request.get("include_unit"):
                    filtered_item["unit"] = item.unit
                if request.get("include_original_contract_quantity"):
                    filtered_item["original_contract_quantity"] = item.original_contract_quantity
                
                # Add contract update quantity columns in order
                for update in contract_updates:
                    quantity_key = f"updated_contract_quantity_{update.id}"
                    if request.get(f"include_{quantity_key}"):
                        boq_item_update = db.query(models.BOQItemQuantityUpdate).filter(
                            models.BOQItemQuantityUpdate.boq_item_id == item.id,
                            models.BOQItemQuantityUpdate.contract_update_id == update.id
                        ).first()
                        filtered_item[quantity_key] = boq_item_update.updated_contract_quantity if boq_item_update else 0
                
                if request.get("include_price"):
                    filtered_item["price"] = item.price
                
                # Add contract update sum columns in order
                for update in contract_updates:
                    sum_key = f"updated_contract_sum_{update.id}"
                    if request.get(f"include_{sum_key}"):
                        boq_item_update = db.query(models.BOQItemQuantityUpdate).filter(
                            models.BOQItemQuantityUpdate.boq_item_id == item.id,
                            models.BOQItemQuantityUpdate.contract_update_id == update.id
                        ).first()
                        filtered_item[sum_key] = boq_item_update.updated_contract_sum if boq_item_update else 0
                
                if request.get("include_total_contract_sum"):
                    filtered_item["total_contract_sum"] = item.total_contract_sum
                if request.get("include_estimated_quantity"):
                    filtered_item["estimated_quantity"] = item.estimated_quantity
                if request.get("include_quantity_submitted"):
                    filtered_item["quantity_submitted"] = item.quantity_submitted
                if request.get("include_internal_quantity"):
                    filtered_item["internal_quantity"] = item.internal_quantity
                if request.get("include_approved_by_project_manager"):
                    filtered_item["approved_by_project_manager"] = item.approved_by_project_manager
                if request.get("include_approved_signed_quantity"):
                    filtered_item["approved_signed_quantity"] = item.approved_signed_quantity
                if request.get("include_total_estimate"):
                    filtered_item["total_estimate"] = item.total_estimate
                if request.get("include_total_submitted"):
                    filtered_item["total_submitted"] = item.total_submitted
                if request.get("include_internal_total"):
                    filtered_item["internal_total"] = item.internal_total
                if request.get("include_total_approved_by_project_manager"):
                    filtered_item["total_approved_by_project_manager"] = item.total_approved_by_project_manager
                if request.get("include_approved_signed_total"):
                    filtered_item["approved_signed_total"] = item.approved_signed_total
                if request.get("include_subsection"):
                    filtered_item["subsection"] = item.subsection
                if request.get("include_notes"):
                    filtered_item["notes"] = item.notes
                
                if filtered_item:
                    filtered_items.append(filtered_item)
        
        # Generate PDF
        pdf_path = pdf_service.export_boq_items(filtered_items, db)
        
        # Return the filename for download using the download endpoint
        filename = pdf_path.split('/')[-1] if '/' in pdf_path else pdf_path.split('\\')[-1]
        return schemas.PDFExportResponse(
            success=True,
            message=f"Successfully exported BOQ items",
            pdf_path=f"/export/download/{filename}",
            sheets_exported=len(filtered_items)
        )
        
    except Exception as e:
        logger.error(f"Error exporting BOQ items: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/boq-items/excel", response_model=schemas.PDFExportResponse)
async def export_boq_items_excel(
    request: dict,
    db: Session = Depends(get_db)
):
    """Export BOQ items to Excel"""
    try:
        excel_service = ExcelService()
        
        # Use the data passed from frontend if available, otherwise fetch from database
        if "data" in request and request["data"]:
            # Frontend sends filtered data with contract updates included
            filtered_items = request["data"]
        else:
            # Fallback: fetch from database and apply filtering
            items = db.query(models.BOQItem).all()
            contract_updates = db.query(models.ContractQuantityUpdate).order_by(models.ContractQuantityUpdate.update_index).all()
            
            filtered_items = []
            for item in items:
                filtered_item = {}
                
                # Process columns in BOQ table order
                if request.get("include_serial_number"):
                    filtered_item["serial_number"] = item.serial_number
                if request.get("include_structure"):
                    filtered_item["structure"] = item.structure
                if request.get("include_system"):
                    filtered_item["system"] = item.system
                if request.get("include_section_number"):
                    filtered_item["section_number"] = item.section_number
                if request.get("include_description"):
                    filtered_item["description"] = item.description
                if request.get("include_unit"):
                    filtered_item["unit"] = item.unit
                if request.get("include_original_contract_quantity"):
                    filtered_item["original_contract_quantity"] = item.original_contract_quantity
                
                # Add contract update quantity columns in order
                for update in contract_updates:
                    quantity_key = f"updated_contract_quantity_{update.id}"
                    if request.get(f"include_{quantity_key}"):
                        boq_item_update = db.query(models.BOQItemQuantityUpdate).filter(
                            models.BOQItemQuantityUpdate.boq_item_id == item.id,
                            models.BOQItemQuantityUpdate.contract_update_id == update.id
                        ).first()
                        filtered_item[quantity_key] = boq_item_update.updated_contract_quantity if boq_item_update else 0
                
                if request.get("include_price"):
                    filtered_item["price"] = item.price
                
                # Add contract update sum columns in order
                for update in contract_updates:
                    sum_key = f"updated_contract_sum_{update.id}"
                    if request.get(f"include_{sum_key}"):
                        boq_item_update = db.query(models.BOQItemQuantityUpdate).filter(
                            models.BOQItemQuantityUpdate.boq_item_id == item.id,
                            models.BOQItemQuantityUpdate.contract_update_id == update.id
                        ).first()
                        filtered_item[sum_key] = boq_item_update.updated_contract_sum if boq_item_update else 0
                
                if request.get("include_total_contract_sum"):
                    filtered_item["total_contract_sum"] = item.total_contract_sum
                if request.get("include_estimated_quantity"):
                    filtered_item["estimated_quantity"] = item.estimated_quantity
                if request.get("include_quantity_submitted"):
                    filtered_item["quantity_submitted"] = item.quantity_submitted
                if request.get("include_internal_quantity"):
                    filtered_item["internal_quantity"] = item.internal_quantity
                if request.get("include_approved_by_project_manager"):
                    filtered_item["approved_by_project_manager"] = item.approved_by_project_manager
                if request.get("include_approved_signed_quantity"):
                    filtered_item["approved_signed_quantity"] = item.approved_signed_quantity
                if request.get("include_total_estimate"):
                    filtered_item["total_estimate"] = item.total_estimate
                if request.get("include_total_submitted"):
                    filtered_item["total_submitted"] = item.total_submitted
                if request.get("include_internal_total"):
                    filtered_item["internal_total"] = item.internal_total
                if request.get("include_total_approved_by_project_manager"):
                    filtered_item["total_approved_by_project_manager"] = item.total_approved_by_project_manager
                if request.get("include_approved_signed_total"):
                    filtered_item["approved_signed_total"] = item.approved_signed_total
                if request.get("include_subsection"):
                    filtered_item["subsection"] = item.subsection
                if request.get("include_notes"):
                    filtered_item["notes"] = item.notes
                
                if filtered_item:
                    filtered_items.append(filtered_item)
        
        # Generate Excel
        excel_path = excel_service.export_boq_items(filtered_items)
        
        # Return the filename for download using the download endpoint
        filename = excel_path.split('/')[-1] if '/' in excel_path else excel_path.split('\\')[-1]
        return schemas.PDFExportResponse(
            success=True,
            message=f"Successfully exported BOQ items to Excel",
            pdf_path=f"/export/download/{filename}",
            sheets_exported=len(filtered_items)
        )
        
    except Exception as e:
        logger.error(f"Error exporting BOQ items to Excel: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/download/{filename}")
async def download_file(filename: str):
    """Download a generated file (PDF or Excel)"""
    try:
        exports_dir = Path("exports")
        file_path = exports_dir / filename
        
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Determine content type based on file extension
        if filename.lower().endswith('.pdf'):
            content_type = "application/pdf"
        elif filename.lower().endswith('.xlsx'):
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif filename.lower().endswith('.xls'):
            content_type = "application/vnd.ms-excel"
        else:
            content_type = "application/octet-stream"
        
        from fastapi.responses import FileResponse
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type=content_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file {filename}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/list", response_model=List[str])
async def list_pdfs():
    """List all available PDF files"""
    try:
        exports_dir = Path("exports")
        if not exports_dir.exists():
            return []
        
        pdf_files = list(exports_dir.glob("*.pdf"))
        return [f.name for f in pdf_files]
        
    except Exception as e:
        logger.error(f"Error listing PDFs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.delete("/cleanup")
async def cleanup_pdfs(days: int = 7):
    """Clean up old PDF files"""
    try:
        exports_dir = Path("exports")
        if not exports_dir.exists():
            return {"message": "No exports directory found"}
        
        cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
        deleted_count = 0
        
        for pdf_file in exports_dir.glob("*.pdf"):
            if pdf_file.stat().st_mtime < cutoff_date:
                pdf_file.unlink()
                deleted_count += 1
        
        return {
            "message": f"Deleted {deleted_count} old PDF files",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up PDFs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) 