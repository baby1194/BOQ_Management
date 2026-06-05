from fastapi import APIRouter, HTTPException, status
from typing import List

from database import project_registry
from database.database import init_project_database
from schemas import schemas

router = APIRouter()


@router.get("", response_model=List[schemas.Project])
async def list_projects():
    return project_registry.list_projects()


@router.post("", response_model=schemas.Project, status_code=status.HTTP_201_CREATED)
async def create_project(project_data: schemas.ProjectCreate):
    name = project_data.name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project name is required",
        )

    project = project_registry.create_project_entry(name)
    init_project_database(project["id"])
    return project
