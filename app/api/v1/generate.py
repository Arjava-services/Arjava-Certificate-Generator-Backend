import os
import uuid
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session
from app.config.settings import settings
from app.models.database import get_db, SessionLocal
from app.models.entities import Project, ProjectFieldMapping, Certificate, GenerationJob
from app.repositories.project_repo import ProjectRepository, FirestoreMapping
from app.services.certificate_generator_service import certificate_generator_service
from app.services.zip_service import zip_service
from app.schemas.generation import JobStatusResponse, PreviewSingleRequest
from pydantic import BaseModel, Field

router = APIRouter(prefix="/generate", tags=["generation"])

class GenerateBatchRequest(BaseModel):
    project_id: str
    rows: List[Dict[str, Any]]
    output_format: Optional[str] = "pdf"
    naming_pattern: Optional[str] = "{{name}}_Certificate_{{year}}"

class PreviewSingleResponse(BaseModel):
    preview_url: str
    participant_name: str
    filename: str

def run_certificate_generation_task(
    job_id: str,
    project_id: str,
    rows: List[Dict[str, Any]],
    output_format: str,
    naming_pattern: str
):
    """Background task executing batch certificate generation without blocking HTTP worker."""
    db: Session = SessionLocal()
    try:
        repo = ProjectRepository(db)
        project = repo.get_project(project_id)
        job = repo.get_job(job_id)
        if not project or not job:
            return

        mappings = repo.get_mappings(project_id)
        project_gen_dir = settings.GENERATED_DIR / project_id
        project_gen_dir.mkdir(parents=True, exist_ok=True)

        # Clear any prior generated certificates for this project
        repo.clear_certificates(project_id)

        # Clear any prior files in generated project directory so stale files or old runs do not linger
        for old_file in project_gen_dir.glob("*"):
            if old_file.is_file():
                try:
                    old_file.unlink()
                except Exception:
                    pass

        used_filenames_in_batch = set()
        successful_certs = []
        error_log = []

        total = len(rows)
        for idx, row in enumerate(rows):
            # Extract participant name
            participant_name = ""
            for col in ("Name", "name", "Full Name", "Participant Name", "Student Name", "Candidate Name", "Participant", "Student"):
                if col in row and str(row[col]).strip():
                    participant_name = str(row[col]).strip()
                    break
            if not participant_name:
                # Fallback to first non-empty field
                for k, v in row.items():
                    if not k.startswith("_") and str(v).strip():
                        participant_name = str(v).strip()
                        break
            if not participant_name:
                participant_name = f"Participant_{idx + 1}"

            # Update job progress in repository
            repo.update_job(
                job_id,
                current_participant=participant_name,
                processed_rows=idx + 1
            )

            try:
                # Render file
                cert_bytes = certificate_generator_service.render_certificate(
                    project=project,
                    mappings=mappings,
                    row_data=row,
                    output_format=output_format
                )

                # Build base filename
                base_filename = certificate_generator_service.build_filename(
                    naming_pattern=naming_pattern,
                    row_data=row,
                    mappings=mappings,
                    output_format=output_format,
                    row_index=idx + 1
                )

                # Deduplicate filename inside the batch so no certificate overwrites another!
                p_file = Path(base_filename)
                stem = p_file.stem
                suffix = p_file.suffix
                unique_filename = base_filename
                counter = 2
                while unique_filename.lower() in used_filenames_in_batch:
                    unique_filename = f"{stem}_{counter}{suffix}"
                    counter += 1
                used_filenames_in_batch.add(unique_filename.lower())

                file_path = project_gen_dir / unique_filename
                with open(file_path, "wb") as f:
                    f.write(cert_bytes)

                cert = Certificate(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    participant_name=participant_name,
                    row_index=row.get("_row_number", idx + 1),
                    row_data=row,
                    filename=unique_filename,
                    file_path=str(file_path),
                    file_size=len(cert_bytes),
                    output_format=output_format,
                    status="generated"
                )
                repo.add_certificate(cert)
                successful_certs.append(cert)
            except Exception as ex:
                err_msg = f"Row {idx + 1} ({participant_name}): {str(ex)}"
                print(f"[CertGen Error] {err_msg}")
                error_log.append({"row": idx + 1, "participant": participant_name, "error": str(ex)})
                failed_cert = Certificate(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    participant_name=participant_name,
                    row_index=row.get("_row_number", idx + 1),
                    row_data=row,
                    filename="",
                    file_path="",
                    file_size=0,
                    output_format=output_format,
                    status="failed",
                    error_message=str(ex)
                )
                repo.add_certificate(failed_cert)

        # Build ZIP archive of all successful certificates
        zip_filename = None
        zip_path_str = None
        if successful_certs:
            zip_filename = f"certificates_{project_id[:8]}.zip"
            zip_path = project_gen_dir / zip_filename
            zip_service.create_certificates_zip(successful_certs, zip_path)
            zip_path_str = str(zip_path)

        final_status = "completed" if len(error_log) == 0 else ("partial" if len(successful_certs) > 0 else "failed")
        now_dt = datetime.now(timezone.utc)
        repo.update_job(
            job_id,
            status=final_status,
            processed_rows=total,
            successful_count=len(successful_certs),
            failed_count=len(error_log),
            error_log=error_log,
            zip_filename=zip_filename,
            zip_path=zip_path_str,
            completed_at=now_dt
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            repo.update_job(
                job_id,
                status="failed",
                error_log=[{"error": str(e)}],
                completed_at=datetime.now(timezone.utc)
            )
        except Exception:
            pass
    finally:
        try:
            db.close()
        except Exception:
            pass

@router.post("/preview-single", response_model=PreviewSingleResponse)
def preview_single_certificate(data: PreviewSingleRequest, db: Session = Depends(get_db)):
    repo = ProjectRepository(db)
    project = repo.get_project(data.project_id)
    if not project or not project.template_filename:
        raise HTTPException(status_code=404, detail="Project or template not found")

    if data.mappings:
        # Use incoming mappings directly for in-memory preview without wiping the database on every preview card flip
        mappings = [
            FirestoreMapping(**m) if isinstance(m, dict) else m
            for m in data.mappings
        ]
    else:
        mappings = repo.get_mappings(data.project_id)
    try:
        preview_data_uri = certificate_generator_service.generate_preview_base64(
            project=project,
            mappings=mappings,
            row_data=data.row_data
        )
        
        participant = data.row_data.get("Name") or data.row_data.get("name") or "Sample Participant"
        filename = certificate_generator_service.build_filename(
            naming_pattern=data.naming_pattern or project.naming_pattern,
            row_data=data.row_data,
            mappings=mappings,
            output_format=data.output_format or "png",
            row_index=1
        )

        return PreviewSingleResponse(
            preview_url=preview_data_uri,
            participant_name=str(participant),
            filename=filename
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview generation failed: {str(e)}")

@router.post("", response_model=JobStatusResponse, status_code=status.HTTP_202_ACCEPTED)
def start_generation_job(
    data: GenerateBatchRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    repo = ProjectRepository(db)
    project = repo.get_project(data.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not data.rows:
        raise HTTPException(status_code=400, detail="Cannot generate certificates without participant rows.")

    # Save output format and naming pattern to project
    repo.update_project(
        data.project_id,
        output_format=data.output_format or "pdf",
        naming_pattern=data.naming_pattern or "{{name}}_Certificate_{{year}}"
    )

    job = repo.create_job(data.project_id, len(data.rows))

    background_tasks.add_task(
        run_certificate_generation_task,
        job_id=job.id,
        project_id=data.project_id,
        rows=data.rows,
        output_format=data.output_format or "pdf",
        naming_pattern=data.naming_pattern or "{{name}}_Certificate_{{year}}"
    )

    return JobStatusResponse(
        id=job.id,
        project_id=job.project_id,
        status=job.status,
        total_rows=job.total_rows,
        processed_rows=0,
        progress_percentage=0,
        successful_count=0,
        failed_count=0,
        current_participant=None,
        error_log=[],
        zip_ready=False,
        created_at=job.created_at,
        completed_at=None
    )

@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    repo = ProjectRepository(db)
    job = repo.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    pct = 0
    if job.total_rows > 0:
        pct = min(100, int((job.processed_rows / job.total_rows) * 100))

    return JobStatusResponse(
        id=job.id,
        project_id=job.project_id,
        status=job.status,
        total_rows=job.total_rows,
        processed_rows=job.processed_rows,
        progress_percentage=pct,
        successful_count=job.successful_count,
        failed_count=job.failed_count,
        current_participant=job.current_participant,
        error_log=job.error_log or [],
        zip_ready=bool(job.zip_path and Path(job.zip_path).exists()),
        created_at=job.created_at,
        completed_at=job.completed_at
    )
