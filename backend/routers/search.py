from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Optional
import logging

from database.database import get_db
from models import models
from schemas import schemas

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/", response_model=schemas.SearchResponse)
async def search_boq_items(
    q: str = Query(..., min_length=1, description="Search query"),
    search_type: str = Query("both", pattern="^(code|description|both)$", description="Search type"),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10000, ge=1, le=50000, description="Maximum number of items to return"),
    db: Session = Depends(get_db)
):
    """Search BOQ items by code or description"""
    try:
        query = db.query(models.BOQItem)
        
        # Build search filter based on search type
        if search_type == "code":
            query = query.filter(models.BOQItem.section_number.ilike(f"%{q}%"))
        elif search_type == "description":
            query = query.filter(models.BOQItem.description.ilike(f"%{q}%"))
        else:  # both
            query = query.filter(
                or_(
                    models.BOQItem.section_number.ilike(f"%{q}%"),
                    models.BOQItem.description.ilike(f"%{q}%")
                )
            )
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        items = query.offset(skip).limit(limit).all()
        
        logger.info(f"Search for '{q}' returned {len(items)} items (total: {total_count})")
        
        return schemas.SearchResponse(
            items=items,
            total_count=total_count,
            query=q
        )
        
    except Exception as e:
        logger.error(f"Error searching BOQ items: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/subchapter/{sub_chapter}", response_model=List[schemas.BOQItem])
async def get_items_by_subchapter(
    sub_chapter: str,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10000, ge=1, le=50000, description="Maximum number of items to return"),
    db: Session = Depends(get_db)
):
    """Get BOQ items by sub-chapter"""
    try:
        items = db.query(models.BOQItem).filter(
            models.BOQItem.subsection == sub_chapter
        ).offset(skip).limit(limit).all()
        
        logger.info(f"Found {len(items)} items for sub-chapter: {sub_chapter}")
        return items
        
    except Exception as e:
        logger.error(f"Error fetching items by sub-chapter {sub_chapter}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/subchapters", response_model=List[str])
async def get_all_subchapters(db: Session = Depends(get_db)):
    """Get all unique sub-chapters"""
    try:
        subchapters = db.query(models.BOQItem.subsection).filter(
            models.BOQItem.subsection.isnot(None)
        ).distinct().all()
        
        # Extract sub-chapter names from query result
        subchapter_list = [sc[0] for sc in subchapters if sc[0]]
        
        logger.info(f"Found {len(subchapter_list)} unique sub-chapters")
        return subchapter_list
        
    except Exception as e:
        logger.error(f"Error fetching sub-chapters: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/filter", response_model=List[schemas.BOQItem])
async def filter_boq_items(
    section_number: Optional[str] = Query(None, description="Filter by section number"),
    description: Optional[str] = Query(None, description="Filter by description"),
    unit: Optional[str] = Query(None, description="Filter by unit"),
    subsection: Optional[str] = Query(None, description="Filter by subsection"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum unit price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum unit price"),
    min_quantity: Optional[float] = Query(None, ge=0, description="Minimum original contract quantity"),
    max_quantity: Optional[float] = Query(None, ge=0, description="Maximum original contract quantity"),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10000, ge=1, le=50000, description="Maximum number of items to return"),
    db: Session = Depends(get_db)
):
    """Filter BOQ items by multiple criteria"""
    try:
        query = db.query(models.BOQItem)
        
        # Apply filters
        if section_number:
            query = query.filter(models.BOQItem.section_number.ilike(f"%{section_number}%"))
        
        if description:
            query = query.filter(models.BOQItem.description.ilike(f"%{description}%"))
        
        if unit:
            query = query.filter(models.BOQItem.unit == unit)
        
        if subsection:
            query = query.filter(models.BOQItem.subsection == subsection)
        
        if min_price is not None:
            query = query.filter(models.BOQItem.price >= min_price)
        
        if max_price is not None:
            query = query.filter(models.BOQItem.price <= max_price)
        
        if min_quantity is not None:
            query = query.filter(models.BOQItem.original_contract_quantity >= min_quantity)
        
        if max_quantity is not None:
            query = query.filter(models.BOQItem.original_contract_quantity <= max_quantity)
        
        # Apply pagination
        items = query.offset(skip).limit(limit).all()
        
        logger.info(f"Filter returned {len(items)} items")
        return items
        
    except Exception as e:
        logger.error(f"Error filtering BOQ items: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/summary", response_model=schemas.SummaryResponse)
async def get_subchapter_summary(db: Session = Depends(get_db)):
    """Get summary of all sub-chapters with totals"""
    try:
        # Get all items grouped by sub-chapter
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
        
        # Convert to response format
        summaries = []
        grand_totals = {
            'estimate': 0.0,
            'submitted': 0.0,
            'pnimi': 0.0,
            'approved': 0.0
        }
        
        for row in summary_data:
            summary = schemas.SubChapterSummary(
                sub_chapter=row.subsection,
                description=None,  # Could be enhanced to include descriptions
                item_count=row.item_count,
                total_estimate=float(row.total_estimate or 0),
                total_submitted=float(row.total_submitted or 0),
                total_pnimi=float(row.total_pnimi or 0),
                total_approved=float(row.total_approved or 0)
            )
            summaries.append(summary)
            
            # Update grand totals
            grand_totals['estimate'] += summary.total_estimate
            grand_totals['submitted'] += summary.total_submitted
            grand_totals['pnimi'] += summary.total_pnimi
            grand_totals['approved'] += summary.total_approved
        
        logger.info(f"Generated summary for {len(summaries)} sub-chapters")
        
        return schemas.SummaryResponse(
            summaries=summaries,
            grand_total_estimate=grand_totals['estimate'],
            grand_total_submitted=grand_totals['submitted'],
            grand_total_pnimi=grand_totals['pnimi'],
            grand_total_approved=grand_totals['approved']
        )
        
    except Exception as e:
        logger.error(f"Error generating sub-chapter summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) 