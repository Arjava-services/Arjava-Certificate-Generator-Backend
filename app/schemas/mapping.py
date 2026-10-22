from typing import Optional, List
from pydantic import BaseModel, Field

class FieldMappingItem(BaseModel):
    id: Optional[str] = None
    placeholder: str = Field(..., description="Template placeholder, e.g. {{name}}")
    sheet_column: Optional[str] = Field(None, description="Mapped Google Sheet column name")
    
    font_family: str = Field("Helvetica", description="Font name")
    font_size: int = Field(24, ge=8, le=120)
    font_color: str = Field("#1e293b", description="Hex color")
    font_weight: str = Field("normal", description="normal, medium, bold, etc.")
    is_italic: bool = Field(False, description="Whether text is italicized")
    opacity: float = Field(1.0, ge=0.0, le=1.0, description="Text opacity from 0.0 to 1.0")
    text_case: str = Field("none", description="none, uppercase, lowercase, capitalize")
    letter_spacing: int = Field(0, ge=-5, le=50, description="Letter spacing in pt")
    text_effect: str = Field("none", description="none, drop, soft")
    
    x_pos: float = Field(..., description="X coordinate (points or percentage)")
    y_pos: float = Field(..., description="Y coordinate (points or percentage)")
    width: float = Field(300.0, description="Bounding box width")
    height: float = Field(40.0, description="Bounding box height")
    alignment: str = Field("center", description="center, left, right")
    
    is_auto_detected: bool = False
    is_required: bool = True

    class Config:
        from_attributes = True

class FieldMappingUpdateRequest(BaseModel):
    mappings: List[FieldMappingItem]
