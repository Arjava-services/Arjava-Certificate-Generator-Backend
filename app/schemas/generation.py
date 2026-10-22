from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class GenerateRequest(BaseModel):
    project_id: str
    output_format: Optional[str] = "pdf" # pdf, png, jpg
    naming_pattern: Optional[str] = "{{name}}_Certificate_{{year}}"

class JobStatusResponse(BaseModel):
    id: str
    project_id: str
    status: str # pending, processing, completed, failed, cancelled
    total_rows: int
    processed_rows: int
    progress_percentage: int
    successful_count: int
    failed_count: int
    current_participant: Optional[str] = None
    error_log: List[Dict[str, Any]] = []
    zip_ready: bool = False
    created_at: datetime
    completed_at: Optional[datetime] = None

class CertificateItemResponse(BaseModel):
    id: str
    project_id: str
    participant_name: str
    row_index: int
    filename: str
    output_format: str
    file_size: int
    status: str
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class CertificateListResponse(BaseModel):
    total: int
    certificates: List[CertificateItemResponse]

class PreviewSingleRequest(BaseModel):
    project_id: str
    row_data: Dict[str, Any]
    output_format: Optional[str] = "png" # Usually png for instant browser preview
    mappings: Optional[List[Dict[str, Any]]] = None
    naming_pattern: Optional[str] = None

