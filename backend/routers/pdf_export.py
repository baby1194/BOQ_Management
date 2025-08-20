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
        pdf_path = pdf_service.export_concentration_sheets(sheets)
        
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
        pdf_path = pdf_service.export_single_concentration_sheet(sheet, boq_item, entries)
        
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
        pdf_path = pdf_service.export_summary(summary_data)
        
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