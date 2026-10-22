import os
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.config.settings import settings
from app.models.database import get_db
from app.repositories.project_repo import ProjectRepository
from app.schemas.generation import CertificateItemResponse, CertificateListResponse

router = APIRouter(prefix="/certificates", tags=["certificates"])

@router.get("/{project_id}", response_model=CertificateListResponse)
def list_project_certificates(project_id: str, db: Session = Depends(get_db)):
    repo = ProjectRepository(db)
    certs = repo.get_certificates(project_id)
    items = [CertificateItemResponse.from_orm(c) for c in certs]
    return CertificateListResponse(total=len(items), certificates=items)

@router.get("/{certificate_id}/download")
def download_single_certificate(certificate_id: str, db: Session = Depends(get_db)):
    repo = ProjectRepository(db)
    cert = repo.get_certificate(certificate_id)
    if not cert or not cert.file_path:
        raise HTTPException(status_code=404, detail="Certificate not found")

    path = Path(cert.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Certificate file missing on disk")

    media_type = "application/pdf" if cert.output_format == "pdf" else f"image/{cert.output_format}"
    return FileResponse(
        path,
        media_type=media_type,
        filename=cert.filename,
        headers={"Content-Disposition": f'attachment; filename="{cert.filename}"'}
    )

@router.get("/{certificate_id}/preview")
def preview_single_certificate(certificate_id: str, db: Session = Depends(get_db)):
    repo = ProjectRepository(db)
    cert = repo.get_certificate(certificate_id)
    if not cert or not cert.file_path:
        raise HTTPException(status_code=404, detail="Certificate not found")

    path = Path(cert.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Certificate file missing on disk")

    media_type = "application/pdf" if cert.output_format == "pdf" else f"image/{cert.output_format}"
    return FileResponse(
        path,
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{cert.filename}"'}
    )

@router.get("/{project_id}/download-all")
def download_all_certificates(project_id: str, db: Session = Depends(get_db)):
    repo = ProjectRepository(db)
    project = repo.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project_gen_dir = settings.GENERATED_DIR / project_id
    zip_path = project_gen_dir / f"certificates_{project_id[:8]}.zip"
    
    # Check if zip exists or any certificates exist to zip on the fly
    if not zip_path.exists():
        certs = repo.get_certificates(project_id)
        if not certs:
            raise HTTPException(status_code=404, detail="No certificates found to download.")
        from app.services.zip_service import zip_service
        zip_service.create_certificates_zip(certs, zip_path)

    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename="certificates.zip",
        headers={"Content-Disposition": 'attachment; filename="certificates.zip"'}
    )
