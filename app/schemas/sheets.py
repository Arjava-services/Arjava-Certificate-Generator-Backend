from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class SheetConnectRequest(BaseModel):
    sheet_url: str = Field(..., description="Google Sheet full URL or spreadsheet ID")

class SheetTabInfo(BaseModel):
    title: str
    sheet_id: Optional[int] = 0
    row_count: Optional[int] = 0

class SheetTabListResponse(BaseModel):
    spreadsheet_id: str
    spreadsheet_title: str
    tabs: List[SheetTabInfo]

class SheetDataRequest(BaseModel):
    sheet_url: str
    tab_name: str
    max_preview_rows: Optional[int] = 5

class SheetDataResponse(BaseModel):
    spreadsheet_id: str
    tab_name: str
    headers: List[str]
    total_rows: int
    preview_rows: List[Dict[str, Any]]
    all_rows: Optional[List[Dict[str, Any]]] = None

class ValidationErrorItem(BaseModel):
    row_number: int
    column_name: Optional[str] = None
    issue_type: str # missing_value, empty_row, duplicate_participant, invalid_format
    message: str
    severity: str = "error" # error, warning
    row_data: Optional[Dict[str, Any]] = None

class SheetValidationResult(BaseModel):
    is_valid: bool
    total_rows: int
    valid_rows_count: int
    error_count: int
    warning_count: int
    issues: List[ValidationErrorItem]
