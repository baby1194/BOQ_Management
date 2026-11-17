from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, sessionmaker
from typing import List

from database import project_registry
from database.database import get_db, get_project_engine, get_project_id, init_project_database
from schemas import schemas
from services.project_info_copy import copy_project_info
from services.project_rollup import linked_subproject_totals

router = APIRouter()


def copy_project_info_between(source_project_id: str, target_project_id: str) -> None:
    Source = sessionmaker(bind=get_project_engine(source_project_id))
    Target = sessionmaker(bind=get_project_engine(target_project_id))
    source = Source()
    target = Target()
    try:
        copy_project_info(source, target)
        target.commit()
    except Exception:
        target.rollback()
        raise
    finally:
        source.close()
        target.close()


@router.get("", response_model=List[schemas.Project])
async def list_projects():
    return project_registry.list_projects()


@router.get("/subproject-totals", response_model=schemas.SubprojectTotals)
async def subproject_totals(
    project_id: str = Depends(get_project_id),
    db: Session = Depends(get_db),
):
    """BOQ, sheet, and money totals of the projects linked to the open project."""
    return linked_subproject_totals(db, project_id)


@router.post("", response_model=schemas.Project, status_code=status.HTTP_201_CREATED)
async def create_project(project_data: schemas.ProjectCreate):
    name = project_data.name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project name is required",
        )

    copy_from = (project_data.copy_from_project_id or "").strip() or None
    if copy_from and not project_registry.get_project(copy_from):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source project not found",
        )

    project = project_registry.create_project_entry(name)
    init_project_database(project["id"])
    if copy_from:
        copy_project_info_between(copy_from, project["id"])
    return project
