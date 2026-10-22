from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.config.settings import settings
from app.models.database import get_db
from app.repositories.project_repo import ProjectRepository
from app.services.template_service import template_service
from app.schemas.template import TemplateUploadResponse

router = APIRouter(prefix="/templates", tags=["templates"])

@router.get("/samples")
def get_sample_templates():
    samples_dir = settings.DATA_DIR / "sample_templates"
    samples = []
    if samples_dir.exists():
        for f in samples_dir.iterdir():
            if f.suffix.lower() in settings.ALLOWED_EXTENSIONS:
                samples.append({
                    "filename": f.name,
                    "title": f.stem.replace("_", " ").title(),
                    "file_type": f.suffix.lower().lstrip("."),
                    "size": f.stat().st_size
                })
    return samples

@router.post("/use-sample")
def use_sample_template(
    project_id: str = Form(...),
    sample_filename: str = Form(...),
    db: Session = Depends(get_db)
):
    repo = ProjectRepository(db)
    project = repo.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    sample_path = settings.DATA_DIR / "sample_templates" / sample_filename
    if not sample_path.exists():
        raise HTTPException(status_code=404, detail="Sample template not found")

    with open(sample_path, "rb") as f:
        content = f.read()

    (
        template_filename,
        file_type,
        preview_image,
        width,
        height,
        detected_placeholders
    ) = template_service.process_uploaded_template(content, sample_filename)

    repo.update_project(
        project_id,
        template_filename=template_filename,
        template_original_name=sample_filename,
        template_file_type=file_type,
        template_preview_image=preview_image,
        template_width=width,
        template_height=height
    )

    existing_mappings = repo.get_mappings(project_id)
    if not existing_mappings and detected_placeholders:
        mappings_data = []
        for ph in detected_placeholders:
            mappings_data.append({
                "placeholder": ph.placeholder,
                "sheet_column": None,
                "font_family": ph.font_name or "Helvetica",
                "font_size": ph.font_size or 24,
                "font_color": "#1e293b",
                "font_weight": "normal",
                "x_pos": ph.x_pos,
                "y_pos": ph.y_pos,
                "width": ph.width,
                "height": ph.height,
                "alignment": ph.alignment or "center",
                "is_auto_detected": True,
                "is_required": True
            })
        repo.set_mappings(project_id, mappings_data)

    return TemplateUploadResponse(
        project_id=project_id,
        template_filename=template_filename,
        template_original_name=sample_filename,
        template_file_type=file_type,
        template_preview_image=preview_image,
        template_width=width,
        template_height=height,
        detected_placeholders=detected_placeholders
    )

@router.post("/upload", response_model=TemplateUploadResponse)
async def upload_template(
    project_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    repo = ProjectRepository(db)
    project = repo.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Validate file extension
    ext = Path(file.filename or "").suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed formats: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )

    # Read bytes and validate size limit
    content = await file.read()
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB."
        )

    try:
        (
            template_filename,
            file_type,
            preview_image,
            width,
            height,
            detected_placeholders
        ) = template_service.process_uploaded_template(content, file.filename or f"template{ext}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Failed to process template: {str(e)}")

    # Update project with template details
    repo.update_project(
        project_id,
        template_filename=template_filename,
        template_original_name=file.filename,
        template_file_type=file_type,
        template_preview_image=preview_image,
        template_width=width,
        template_height=height
    )

    # Populate initial field mappings if project doesn't have any
    existing_mappings = repo.get_mappings(project_id)
    if not existing_mappings and detected_placeholders:
        mappings_data = []
        for ph in detected_placeholders:
            mappings_data.append({
                "placeholder": ph.placeholder,
                "sheet_column": None,
                "font_family": ph.font_name or "Helvetica",
                "font_size": ph.font_size or 24,
                "font_color": "#1e293b",
                "font_weight": "normal",
                "x_pos": ph.x_pos,
                "y_pos": ph.y_pos,
                "width": ph.width,
                "height": ph.height,
                "alignment": ph.alignment or "center",
                "is_auto_detected": True,
                "is_required": True
            })
        repo.set_mappings(project_id, mappings_data)

    return TemplateUploadResponse(
        project_id=project_id,
        template_filename=template_filename,
        template_original_name=file.filename or "",
        template_file_type=file_type,
        template_preview_image=preview_image,
        template_width=width,
        template_height=height,
        detected_placeholders=detected_placeholders
    )

@router.get("/{project_id}/preview")
def get_template_preview(project_id: str, db: Session = Depends(get_db)):
    repo = ProjectRepository(db)
    project = repo.get_project(project_id)
    if not project or not (project.template_preview_image or project.template_filename):
        raise HTTPException(status_code=404, detail="Template preview not found.")

    preview_path = None
    if project.template_preview_image:
        preview_path = settings.TEMPLATES_DIR / project.template_preview_image

    if not preview_path or not preview_path.exists():
        # Auto-regenerate preview if template file exists on disk
        if project.template_filename:
            tmpl_path = settings.TEMPLATES_DIR / project.template_filename
            if tmpl_path.exists():
                try:
                    with open(tmpl_path, "rb") as f:
                        b = f.read()
                    _, _, new_preview, _, _, _ = template_service.process_uploaded_template(b, project.template_filename)
                    repo.update_project(project_id, template_preview_image=new_preview)
                    preview_path = settings.TEMPLATES_DIR / new_preview
                except Exception as e:
                    pass

    if not preview_path or not preview_path.exists():
        raise HTTPException(status_code=404, detail="Preview file missing on disk.")

    return FileResponse(preview_path, media_type="image/png")
