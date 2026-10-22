from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Project name")

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    sheet_url: Optional[str] = None
    sheet_id: Optional[str] = None
    sheet_tab_name: Optional[str] = None
    naming_pattern: Optional[str] = None
    output_format: Optional[str] = None

class ProjectListItem(BaseModel):
    id: str
    name: str
    template_original_name: Optional[str] = None
    template_file_type: Optional[str] = None
    template_preview_image: Optional[str] = None
    sheet_tab_name: Optional[str] = None
    certificates_count: int = 0
    last_generated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ProjectDetailResponse(BaseModel):
    id: str
    name: str
    template_filename: Optional[str] = None
    template_original_name: Optional[str] = None
    template_file_type: Optional[str] = None
    template_preview_image: Optional[str] = None
    template_width: float
    template_height: float
    sheet_url: Optional[str] = None
    sheet_id: Optional[str] = None
    sheet_tab_name: Optional[str] = None
    naming_pattern: str
    output_format: str
    certificates_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
