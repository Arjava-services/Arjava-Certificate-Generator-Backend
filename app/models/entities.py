import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON
)
from sqlalchemy.orm import relationship
from app.models.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=True)
    name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    name = Column(String(255), nullable=False)
    
    # Template information
    template_filename = Column(String(255), nullable=True)
    template_original_name = Column(String(255), nullable=True)
    template_file_type = Column(String(32), nullable=True) # pdf, png, jpg
    template_preview_image = Column(String(255), nullable=True) # rendered preview image file name
    template_width = Column(Float, default=842.0) # default A4 landscape points (595 x 842)
    template_height = Column(Float, default=595.0)
    
    # Google Sheet details
    sheet_url = Column(Text, nullable=True)
    sheet_id = Column(String(255), nullable=True)
    sheet_tab_name = Column(String(255), nullable=True)
    
    # Generation settings
    naming_pattern = Column(String(255), default="{{name}}_Certificate_{{year}}")
    output_format = Column(String(16), default="pdf") # pdf, png, jpg
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="projects")
    field_mappings = relationship("ProjectFieldMapping", back_populates="project", cascade="all, delete-orphan", order_by="ProjectFieldMapping.created_at")
    certificates = relationship("Certificate", back_populates="project", cascade="all, delete-orphan", order_by="Certificate.row_index")
    jobs = relationship("GenerationJob", back_populates="project", cascade="all, delete-orphan", order_by="GenerationJob.created_at.desc()")

class ProjectFieldMapping(Base):
    __tablename__ = "project_field_mappings"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    
    placeholder = Column(String(100), nullable=False) # e.g. {{name}}
    sheet_column = Column(String(100), nullable=True)  # e.g. Name
    
    # Visual positioning on template
    font_family = Column(String(64), default="Helvetica")
    font_size = Column(Integer, default=24)
    font_color = Column(String(16), default="#112D32")
    font_weight = Column(String(16), default="normal") # normal, bold
    is_italic = Column(Boolean, default=False)
    opacity = Column(Float, default=1.0) # 0.1 to 1.0
    text_case = Column(String(16), default="none") # none, uppercase, lowercase, capitalize
    letter_spacing = Column(Integer, default=0)
    text_effect = Column(String(16), default="none") # none, drop, soft
    
    x_pos = Column(Float, default=421.0) # Center coordinate or left
    y_pos = Column(Float, default=297.0)
    width = Column(Float, default=300.0)
    height = Column(Float, default=40.0)
    alignment = Column(String(16), default="center") # center, left, right
    
    is_auto_detected = Column(Boolean, default=False)
    is_required = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="field_mappings")

class Certificate(Base):
    __tablename__ = "certificates"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    
    participant_name = Column(String(255), nullable=False)
    row_index = Column(Integer, nullable=False)
    row_data = Column(JSON, nullable=True) # Full row dictionary
    
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, default=0)
    output_format = Column(String(16), default="pdf")
    
    status = Column(String(32), default="generated") # generated, failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="certificates")

class GenerationJob(Base):
    __tablename__ = "generation_jobs"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    
    status = Column(String(32), default="pending") # pending, processing, completed, failed, cancelled
    total_rows = Column(Integer, default=0)
    processed_rows = Column(Integer, default=0)
    successful_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    current_participant = Column(String(255), nullable=True)
    
    error_log = Column(JSON, default=list)
    zip_filename = Column(String(255), nullable=True)
    zip_path = Column(String(512), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    project = relationship("Project", back_populates="jobs")
