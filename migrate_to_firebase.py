import os
from pathlib import Path
from datetime import datetime, timezone
from app.models.database import SessionLocal
from app.models.entities import Project, ProjectFieldMapping, Certificate, GenerationJob
from app.services.firebase_service import firebase_service
from app.config.settings import settings

def to_iso(dt):
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)

def migrate():
    print("Starting migration to Firebase Firestore and Cloud Storage...")
    db_session = SessionLocal()
    fs = firebase_service.db
    bucket = firebase_service.bucket

    projects = db_session.query(Project).all()
    print(f"Found {len(projects)} projects in local SQLite database.")

    # 1. Migrate projects and mappings
    for p in projects:
        print(f"Migrating project '{p.name}' (ID: {p.id})...")
        proj_data = {
            "id": p.id,
            "name": p.name,
            "template_filename": p.template_filename,
            "template_original_name": p.template_original_name,
            "template_file_type": p.template_file_type,
            "template_preview_image": p.template_preview_image,
            "template_width": float(p.template_width) if p.template_width else 842.0,
            "template_height": float(p.template_height) if p.template_height else 595.0,
            "sheet_url": p.sheet_url,
            "sheet_id": p.sheet_id,
            "sheet_tab_name": p.sheet_tab_name,
            "naming_pattern": p.naming_pattern or "{{name}}_Certificate_{{year}}",
            "output_format": p.output_format or "pdf",
            "created_at": to_iso(p.created_at),
            "updated_at": to_iso(p.updated_at),
        }
        fs.collection("projects").document(p.id).set(proj_data, merge=True)

        # Migrate mappings for this project
        mappings = db_session.query(ProjectFieldMapping).filter_by(project_id=p.id).all()
        for m in mappings:
            m_data = {
                "id": m.id,
                "project_id": m.project_id,
                "placeholder": m.placeholder,
                "sheet_column": m.sheet_column,
                "font_family": m.font_family,
                "font_size": m.font_size,
                "font_color": m.font_color,
                "font_weight": m.font_weight,
                "is_italic": m.is_italic,
                "opacity": m.opacity,
                "text_case": m.text_case,
                "letter_spacing": m.letter_spacing,
                "x_pos": float(m.x_pos) if m.x_pos is not None else 421.0,
                "y_pos": float(m.y_pos) if m.y_pos is not None else 297.0,
                "width": float(m.width) if m.width is not None else 300.0,
                "height": float(m.height) if m.height is not None else 40.0,
                "alignment": m.alignment,
                "is_auto_detected": bool(m.is_auto_detected),
                "is_required": bool(m.is_required),
                "created_at": to_iso(m.created_at)
            }
            fs.collection("projects").document(p.id).collection("mappings").document(m.id).set(m_data, merge=True)

        # Upload template file to storage if exists and bucket available
        if p.template_filename and bucket and bucket.exists():
            tmpl_path = settings.TEMPLATES_DIR / p.template_filename
            if tmpl_path.exists():
                try:
                    blob_name = f"templates/{p.template_filename}"
                    print(f"Uploading template {p.template_filename} to Firebase Storage...")
                    bucket.blob(blob_name).upload_from_filename(str(tmpl_path))
                except Exception as e:
                    print(f"Storage upload skipped: {e}")

        # Upload preview image to storage if exists and bucket available
        if p.template_preview_image and bucket and bucket.exists():
            prev_path = settings.TEMPLATES_DIR / p.template_preview_image
            if prev_path.exists():
                try:
                    blob_name = f"templates/{p.template_preview_image}"
                    print(f"Uploading preview image {p.template_preview_image} to Firebase Storage...")
                    bucket.blob(blob_name).upload_from_filename(str(prev_path), content_type="image/png")
                except Exception as e:
                    print(f"Storage upload skipped: {e}")

    # 2. Migrate certificates
    certificates = db_session.query(Certificate).all()
    print(f"Found {len(certificates)} certificates in local SQLite database.")
    for c in certificates:
        c_data = {
            "id": c.id,
            "project_id": c.project_id,
            "participant_name": c.participant_name,
            "row_index": c.row_index,
            "row_data": c.row_data,
            "filename": c.filename,
            "file_path": c.file_path,
            "file_size": c.file_size,
            "output_format": c.output_format,
            "status": c.status,
            "error_message": c.error_message,
            "created_at": to_iso(c.created_at)
        }
        fs.collection("certificates").document(c.id).set(c_data, merge=True)

        # Upload certificate file if exists and bucket available
        local_cpath = Path(c.file_path) if c.file_path else None
        if local_cpath and local_cpath.exists() and bucket and bucket.exists():
            try:
                blob_name = f"certificates/{c.project_id}/{c.filename}"
                bucket.blob(blob_name).upload_from_filename(str(local_cpath))
            except Exception as e:
                print(f"Certificate storage upload skipped: {e}")

    # 3. Migrate generation jobs
    jobs = db_session.query(GenerationJob).all()
    print(f"Found {len(jobs)} jobs in local SQLite database.")
    for j in jobs:
        j_data = {
            "id": j.id,
            "project_id": j.project_id,
            "status": j.status,
            "total_rows": j.total_rows,
            "processed_rows": j.processed_rows,
            "successful_count": j.successful_count,
            "failed_count": j.failed_count,
            "current_participant": j.current_participant,
            "error_log": j.error_log or [],
            "zip_filename": j.zip_filename,
            "zip_path": j.zip_path,
            "created_at": to_iso(j.created_at),
            "completed_at": to_iso(j.completed_at)
        }
        fs.collection("generation_jobs").document(j.id).set(j_data, merge=True)

    print("Migration completed successfully! All data is now in Firebase Firestore!")

if __name__ == "__main__":
    migrate()
