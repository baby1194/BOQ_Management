from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging

from database.database import get_db
from models import models
from schemas import schemas

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=schemas.ProjectInfo)
async def get_project_info(db: Session = Depends(get_db)):
    """Get the current project information (creates default if none exists)"""
    try:
        # Get existing project info or create default
        project_info = db.query(models.ProjectInfo).first()
        
        if not project_info:
            # Create default project info
            project_info = models.ProjectInfo()
            db.add(project_info)
            db.commit()
            db.refresh(project_info)
            logger.info("Created default project info")
        
        return project_info
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error getting project info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.put("/", response_model=schemas.ProjectInfo)
async def update_project_info(
    project_info_update: schemas.ProjectInfoUpdate,
    db: Session = Depends(get_db)
):
    """Update project information and sync to all concentration sheets"""
    try:
        # Get existing project info or create new
        project_info = db.query(models.ProjectInfo).first()
        
        if not project_info:
            project_info = models.ProjectInfo()
            db.add(project_info)
        
        # Update fields
        update_data = project_info_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(project_info, field, value)
        
        db.commit()
        db.refresh(project_info)
        
        # Update all concentration sheets with new project info
        concentration_sheets = db.query(models.ConcentrationSheet).all()
        
        for sheet in concentration_sheets:
            # Map project info fields to concentration sheet fields
            if project_info.project_name:
                sheet.project_name = project_info.project_name
            if project_info.main_contractor_name:
                sheet.contractor_in_charge = project_info.main_contractor_name
            if project_info.contract_no:
                sheet.contract_no = project_info.contract_no
            if project_info.developer_name:
                sheet.developer_name = project_info.developer_name
        
        db.commit()
        
        logger.info(f"Updated project info and synced to {len(concentration_sheets)} concentration sheets")
        return project_info
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating project info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/sync", response_model=dict)
async def sync_project_info_to_concentration_sheets(db: Session = Depends(get_db)):
    """Manually sync project info to all concentration sheets"""
    try:
        project_info = db.query(models.ProjectInfo).first()
        if not project_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No project info found"
            )
        
        concentration_sheets = db.query(models.ConcentrationSheet).all()
        updated_count = 0
        
        for sheet in concentration_sheets:
            updated = False
            
            if project_info.project_name and sheet.project_name != project_info.project_name:
                sheet.project_name = project_info.project_name
                updated = True
                
            if project_info.main_contractor_name and sheet.contractor_in_charge != project_info.main_contractor_name:
                sheet.contractor_in_charge = project_info.main_contractor_name
                updated = True
                
            if project_info.contract_no and sheet.contract_no != project_info.contract_no:
                sheet.contract_no = project_info.contract_no
                updated = True
                
            if project_info.developer_name and sheet.developer_name != project_info.developer_name:
                sheet.developer_name = project_info.developer_name
                updated = True
            
            if updated:
                updated_count += 1
        
        db.commit()
        
        logger.info(f"Synced project info to {updated_count} concentration sheets")
        return {
            "success": True,
            "message": f"Synced project info to {updated_count} concentration sheets",
            "sheets_updated": updated_count,
            "total_sheets": len(concentration_sheets)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error syncing project info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

