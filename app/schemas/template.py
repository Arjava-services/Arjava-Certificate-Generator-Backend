from typing import Optional, List
from pydantic import BaseModel, Field

class PlaceholderInfo(BaseModel):
    placeholder: str # e.g. {{name}}
    raw_text: Optional[str] = None
    x_pos: float
    y_pos: float
    width: float
    height: float
    font_name: Optional[str] = "Helvetica"
    font_size: Optional[int] = 24
    alignment: Optional[str] = "center"

class TemplateUploadResponse(BaseModel):
    project_id: str
    template_filename: str
    template_original_name: str
    template_file_type: str
    template_preview_image: str
    template_width: float
    template_height: float
    detected_placeholders: List[PlaceholderInfo]
