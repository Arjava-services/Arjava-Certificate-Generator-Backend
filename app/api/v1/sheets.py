from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.repositories.project_repo import ProjectRepository
from app.services.google_sheets_service import google_sheets_service
from app.services.validation_service import validation_service
from app.schemas.sheets import (
    SheetConnectRequest, SheetTabListResponse, SheetTabInfo,
    SheetDataRequest, SheetDataResponse, SheetValidationResult
)
from pydantic import BaseModel

router = APIRouter(prefix="/sheets", tags=["sheets"])

class SheetValidateInput(BaseModel):
    project_id: str
    rows: List[Dict[str, Any]]

@router.post("/connect", response_model=SheetTabListResponse)
def connect_sheet(data: SheetConnectRequest):
    try:
        title, tabs = google_sheets_service.get_spreadsheet_tabs(data.sheet_url)
        spreadsheet_id = google_sheets_service.extract_spreadsheet_id(data.sheet_url)
        tab_infos = [SheetTabInfo(**t) for t in tabs]
        return SheetTabListResponse(
            spreadsheet_id=spreadsheet_id,
            spreadsheet_title=title,
            tabs=tab_infos
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to connect to Google Sheet: {str(e)}")

@router.post("/data", response_model=SheetDataResponse)
def get_sheet_data(data: SheetDataRequest):
    try:
        headers, rows = google_sheets_service.read_sheet_data(data.sheet_url, data.tab_name)
        spreadsheet_id = google_sheets_service.extract_spreadsheet_id(data.sheet_url)
        preview_rows = rows[:data.max_preview_rows]
        return SheetDataResponse(
            spreadsheet_id=spreadsheet_id,
            tab_name=data.tab_name,
            headers=headers,
            total_rows=len(rows),
            preview_rows=preview_rows,
            all_rows=rows
        )
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/demo", response_model=SheetDataResponse)
def get_demo_participants():
    """Returns sample participant data for immediate zero-config testing."""
    headers, rows = google_sheets_service.get_demo_participants()
    return SheetDataResponse(
        spreadsheet_id="demo-sheet-competition-2026",
        tab_name="Participants",
        headers=headers,
        total_rows=len(rows),
        preview_rows=rows[:5],
        all_rows=rows
    )

@router.post("/validate", response_model=SheetValidationResult)
def validate_sheet(data: SheetValidateInput, db: Session = Depends(get_db)):
    repo = ProjectRepository(db)
    project = repo.get_project(data.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    mappings = repo.get_mappings(data.project_id)
    result = validation_service.validate_spreadsheet_data(data.rows, mappings)
    return result
