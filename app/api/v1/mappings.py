from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.repositories.project_repo import ProjectRepository
from app.schemas.mapping import FieldMappingItem, FieldMappingUpdateRequest

router = APIRouter(prefix="/mappings", tags=["mappings"])

@router.get("/{project_id}", response_model=List[FieldMappingItem])
def get_project_mappings(project_id: str, db: Session = Depends(get_db)):
    repo = ProjectRepository(db)
    project = repo.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    mappings = repo.get_mappings(project_id)
    return mappings

@router.put("/{project_id}", response_model=List[FieldMappingItem])
def save_project_mappings(
    project_id: str,
    data: FieldMappingUpdateRequest,
    db: Session = Depends(get_db)
):
    repo = ProjectRepository(db)
    project = repo.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    mappings_dicts = [m.dict() for m in data.mappings]
    updated = repo.set_mappings(project_id, mappings_dicts)
    return updated
