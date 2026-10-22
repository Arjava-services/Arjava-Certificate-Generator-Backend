import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from google.cloud.firestore_v1.base_query import FieldFilter
from app.config.settings import settings
from app.services.firebase_service import firebase_service
from app.models.entities import Project, ProjectFieldMapping, Certificate, GenerationJob

def parse_datetime(val) -> Optional[datetime]:
    if val is None:
        return None
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val.astimezone(timezone.utc)
    try:
        dt = datetime.fromisoformat(str(val).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)

def format_datetime(val) -> str:
    if val is None:
        return datetime.now(timezone.utc).isoformat()
    if isinstance(val, datetime):
        return val.isoformat()
    return str(val)

class FirestoreEntity:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __getattr__(self, name):
        return None

class FirestoreProject(FirestoreEntity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.created_at = parse_datetime(getattr(self, "created_at", None)) or datetime.now(timezone.utc)
        self.updated_at = parse_datetime(getattr(self, "updated_at", None)) or datetime.now(timezone.utc)
        if not hasattr(self, "field_mappings") or self.field_mappings is None:
            self.field_mappings = []
        if not hasattr(self, "certificates") or self.certificates is None:
            self.certificates = []
        if not hasattr(self, "jobs") or self.jobs is None:
            self.jobs = []
        if not hasattr(self, "template_width") or self.template_width is None:
            self.template_width = 842.0
        if not hasattr(self, "template_height") or self.template_height is None:
            self.template_height = 595.0
        if not hasattr(self, "naming_pattern") or not self.naming_pattern:
            self.naming_pattern = "{{name}}_Certificate_{{year}}"
        if not hasattr(self, "output_format") or not self.output_format:
            self.output_format = "pdf"
        if not hasattr(self, "certificates_count") or self.certificates_count is None:
            self.certificates_count = 0

class FirestoreMapping(FirestoreEntity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.created_at = parse_datetime(getattr(self, "created_at", None)) or datetime.now(timezone.utc)

class FirestoreCertificate(FirestoreEntity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.created_at = parse_datetime(getattr(self, "created_at", None)) or datetime.now(timezone.utc)
        if not hasattr(self, "output_format") or not self.output_format:
            self.output_format = "pdf"
        if not hasattr(self, "file_size") or self.file_size is None:
            self.file_size = 0
        if not hasattr(self, "status") or not self.status:
            self.status = "generated"

class FirestoreJob(FirestoreEntity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.created_at = parse_datetime(getattr(self, "created_at", None)) or datetime.now(timezone.utc)
        self.completed_at = parse_datetime(getattr(self, "completed_at", None))
        if not hasattr(self, "status") or not self.status:
            self.status = "pending"
        if not hasattr(self, "total_rows") or self.total_rows is None:
            self.total_rows = 0
        if not hasattr(self, "processed_rows") or self.processed_rows is None:
            self.processed_rows = 0
        if not hasattr(self, "successful_count") or self.successful_count is None:
            self.successful_count = 0
        if not hasattr(self, "failed_count") or self.failed_count is None:
            self.failed_count = 0
        if not hasattr(self, "error_log") or self.error_log is None:
            self.error_log = []

class ProjectRepository:
    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self.use_firebase = settings.USE_FIREBASE and (firebase_service.db is not None)
        self.fs = firebase_service.db if self.use_firebase else None

    # -------------------------------------------------------------------------
    # PROJECTS
    # -------------------------------------------------------------------------
    def list_projects(self) -> List[Dict[str, Any]]:
        if self.use_firebase:
            projects_ref = self.fs.collection("projects").stream()
            projects_data = []
            for doc in projects_ref:
                p_dict = doc.to_dict()
                p_id = p_dict.get("id", doc.id)
                p_dict["id"] = p_id

                cert_count = p_dict.get("certificates_count", 0)
                last_generated = parse_datetime(p_dict.get("last_generated_at"))

                projects_data.append({
                    "id": p_id,
                    "name": p_dict.get("name", "Untitled Project"),
                    "template_original_name": p_dict.get("template_original_name"),
                    "template_file_type": p_dict.get("template_file_type"),
                    "template_preview_image": p_dict.get("template_preview_image"),
                    "sheet_tab_name": p_dict.get("sheet_tab_name"),
                    "certificates_count": cert_count,
                    "last_generated_at": last_generated,
                    "created_at": parse_datetime(p_dict.get("created_at")),
                    "updated_at": parse_datetime(p_dict.get("updated_at"))
                })
            # Sort by updated_at descending
            min_utc = datetime.min.replace(tzinfo=timezone.utc)
            projects_data.sort(key=lambda x: x["updated_at"] or min_utc, reverse=True)
            return projects_data

        # Fallback to SQLite
        projects = self.db.query(Project).order_by(Project.updated_at.desc()).all()
        results = []
        for p in projects:
            cert_count = self.db.query(func.count(Certificate.id)).filter(
                Certificate.project_id == p.id,
                Certificate.status == "generated"
            ).scalar() or 0
            
            latest_cert = self.db.query(Certificate.created_at).filter(
                Certificate.project_id == p.id
            ).order_by(Certificate.created_at.desc()).first()

            results.append({
                "id": p.id,
                "name": p.name,
                "template_original_name": p.template_original_name,
                "template_file_type": p.template_file_type,
                "template_preview_image": p.template_preview_image,
                "sheet_tab_name": p.sheet_tab_name,
                "certificates_count": cert_count,
                "last_generated_at": latest_cert[0] if latest_cert else None,
                "created_at": p.created_at,
                "updated_at": p.updated_at
            })
        return results

    def get_project(self, project_id: str) -> Optional[Any]:
        if self.use_firebase:
            doc = self.fs.collection("projects").document(project_id).get()
            if not doc.exists:
                return None
            data = doc.to_dict()
            data["id"] = data.get("id", doc.id)

            # Load mappings
            mappings_docs = self.fs.collection("projects").document(project_id).collection("mappings").order_by("created_at").stream()
            field_mappings = [FirestoreMapping(**m.to_dict()) for m in mappings_docs]
            data["field_mappings"] = field_mappings

            # Load certificates
            certs_docs = self.fs.collection("certificates").where(
                filter=FieldFilter("project_id", "==", project_id)
            ).stream()
            certificates = [FirestoreCertificate(**c.to_dict()) for c in certs_docs]
            data["certificates"] = certificates
            data["certificates_count"] = len([c for c in certificates if getattr(c, "status", None) == "generated"])

            # Load jobs
            jobs_docs = self.fs.collection("generation_jobs").where(
                filter=FieldFilter("project_id", "==", project_id)
            ).stream()
            data["jobs"] = [FirestoreJob(**j.to_dict()) for j in jobs_docs]

            return FirestoreProject(**data)

        # Fallback to SQLite
        return self.db.query(Project).filter(Project.id == project_id).first()

    def create_project(self, name: str) -> Any:
        now_iso = datetime.now(timezone.utc).isoformat()
        new_id = str(uuid.uuid4())
        if self.use_firebase:
            project_data = {
                "id": new_id,
                "name": name,
                "template_filename": None,
                "template_original_name": None,
                "template_file_type": None,
                "template_preview_image": None,
                "template_width": 842.0,
                "template_height": 595.0,
                "sheet_url": None,
                "sheet_id": None,
                "sheet_tab_name": None,
                "naming_pattern": "{{name}}_Certificate_{{year}}",
                "output_format": "pdf",
                "created_at": now_iso,
                "updated_at": now_iso
            }
            self.fs.collection("projects").document(new_id).set(project_data)
            return FirestoreProject(**project_data)

        # Fallback to SQLite
        project = Project(name=name)
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def update_project(self, project_id: str, **kwargs) -> Optional[Any]:
        if self.use_firebase:
            doc_ref = self.fs.collection("projects").document(project_id)
            doc = doc_ref.get()
            if not doc.exists:
                return None
            updates = {k: v for k, v in kwargs.items() if v is not None}
            updates["updated_at"] = datetime.now(timezone.utc).isoformat()
            doc_ref.update(updates)
            return self.get_project(project_id)

        # Fallback to SQLite
        project = self.get_project(project_id)
        if not project:
            return None
        for key, value in kwargs.items():
            if hasattr(project, key) and value is not None:
                setattr(project, key, value)
        project.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(project)
        return project

    def delete_project(self, project_id: str) -> bool:
        if self.use_firebase:
            doc_ref = self.fs.collection("projects").document(project_id)
            if not doc_ref.get().exists:
                return False
            # Delete mappings
            for m in doc_ref.collection("mappings").stream():
                m.reference.delete()
            # Delete certificates
            for c in self.fs.collection("certificates").where(filter=FieldFilter("project_id", "==", project_id)).stream():
                c.reference.delete()
            # Delete jobs
            for j in self.fs.collection("generation_jobs").where(filter=FieldFilter("project_id", "==", project_id)).stream():
                j.reference.delete()
            doc_ref.delete()
            return True

        # Fallback to SQLite
        project = self.get_project(project_id)
        if not project:
            return False
        self.db.delete(project)
        self.db.commit()
        return True

    # -------------------------------------------------------------------------
    # FIELD MAPPINGS
    # -------------------------------------------------------------------------
    def get_mappings(self, project_id: str) -> List[Any]:
        if self.use_firebase:
            docs = self.fs.collection("projects").document(project_id).collection("mappings").order_by("created_at").stream()
            return [FirestoreMapping(**d.to_dict()) for d in docs]

        # Fallback to SQLite
        return self.db.query(ProjectFieldMapping).filter(
            ProjectFieldMapping.project_id == project_id
        ).order_by(ProjectFieldMapping.created_at.asc()).all()

    def set_mappings(self, project_id: str, mappings_data: List[Dict[str, Any]]) -> List[Any]:
        if self.use_firebase:
            mappings_col = self.fs.collection("projects").document(project_id).collection("mappings")
            # Clear existing
            for doc in mappings_col.stream():
                doc.reference.delete()

            now_iso = datetime.now(timezone.utc).isoformat()
            saved_mappings = []
            for m in mappings_data:
                m_id = str(uuid.uuid4())
                m_dict = {
                    "id": m_id,
                    "project_id": project_id,
                    "placeholder": str(m.get("placeholder", "")).strip(),
                    "sheet_column": m.get("sheet_column"),
                    "font_family": m.get("font_family", "Helvetica"),
                    "font_size": int(m.get("font_size", 24)),
                    "font_color": m.get("font_color", "#1e293b"),
                    "font_weight": m.get("font_weight", "normal"),
                    "is_italic": bool(m.get("is_italic", False)),
                    "opacity": float(m.get("opacity", 1.0) if m.get("opacity") is not None else 1.0),
                    "text_case": str(m.get("text_case", "none")),
                    "letter_spacing": int(m.get("letter_spacing", 0) if m.get("letter_spacing") is not None else 0),
                    "text_effect": str(m.get("text_effect", "none")),
                    "x_pos": float(m.get("x_pos", 421.0)),
                    "y_pos": float(m.get("y_pos", 297.0)),
                    "width": float(m.get("width", 300.0)),
                    "height": float(m.get("height", 40.0)),
                    "alignment": m.get("alignment", "center"),
                    "is_auto_detected": bool(m.get("is_auto_detected", False)),
                    "is_required": bool(m.get("is_required", True)),
                    "created_at": now_iso
                }
                mappings_col.document(m_id).set(m_dict)
                saved_mappings.append(FirestoreMapping(**m_dict))
            return saved_mappings

        # Fallback to SQLite
        self.db.query(ProjectFieldMapping).filter(ProjectFieldMapping.project_id == project_id).delete()
        new_mappings = []
        for m in mappings_data:
            mapping = ProjectFieldMapping(
                project_id=project_id,
                placeholder=m.get("placeholder", "").strip(),
                sheet_column=m.get("sheet_column"),
                font_family=m.get("font_family", "Helvetica"),
                font_size=m.get("font_size", 24),
                font_color=m.get("font_color", "#1e293b"),
                font_weight=m.get("font_weight", "normal"),
                is_italic=bool(m.get("is_italic", False)),
                opacity=float(m.get("opacity", 1.0) if m.get("opacity") is not None else 1.0),
                text_case=str(m.get("text_case", "none")),
                letter_spacing=int(m.get("letter_spacing", 0) if m.get("letter_spacing") is not None else 0),
                text_effect=str(m.get("text_effect", "none")),
                x_pos=float(m.get("x_pos", 421.0)),
                y_pos=float(m.get("y_pos", 297.0)),
                width=float(m.get("width", 300.0)),
                height=float(m.get("height", 40.0)),
                alignment=m.get("alignment", "center"),
                is_auto_detected=bool(m.get("is_auto_detected", False)),
                is_required=bool(m.get("is_required", True))
            )
            self.db.add(mapping)
            new_mappings.append(mapping)
        self.db.commit()
        return new_mappings

    # -------------------------------------------------------------------------
    # CERTIFICATES
    # -------------------------------------------------------------------------
    def get_certificates(self, project_id: str) -> List[Any]:
        if self.use_firebase:
            docs = self.fs.collection("certificates").where(
                filter=FieldFilter("project_id", "==", project_id)
            ).stream()
            certs = [FirestoreCertificate(**d.to_dict()) for d in docs]
            certs.sort(key=lambda c: getattr(c, "row_index", 0) or 0)
            return certs

        # Fallback to SQLite
        return self.db.query(Certificate).filter(
            Certificate.project_id == project_id
        ).order_by(Certificate.row_index.asc()).all()

    def get_certificate(self, certificate_id: str) -> Optional[Any]:
        if self.use_firebase:
            doc = self.fs.collection("certificates").document(certificate_id).get()
            if not doc.exists:
                return None
            return FirestoreCertificate(**doc.to_dict())

        # Fallback to SQLite
        return self.db.query(Certificate).filter(Certificate.id == certificate_id).first()

    def clear_certificates(self, project_id: str) -> None:
        if self.use_firebase:
            for doc in self.fs.collection("certificates").where(filter=FieldFilter("project_id", "==", project_id)).stream():
                doc.reference.delete()
            return

        # Fallback to SQLite
        self.db.query(Certificate).filter(Certificate.project_id == project_id).delete()
        self.db.commit()

    def add_certificate(self, certificate: Any) -> Any:
        if self.use_firebase:
            c_dict = {
                "id": getattr(certificate, "id", str(uuid.uuid4())),
                "project_id": getattr(certificate, "project_id", None),
                "participant_name": getattr(certificate, "participant_name", ""),
                "row_index": getattr(certificate, "row_index", 0),
                "row_data": getattr(certificate, "row_data", {}),
                "filename": getattr(certificate, "filename", ""),
                "file_path": getattr(certificate, "file_path", ""),
                "file_size": getattr(certificate, "file_size", 0),
                "output_format": getattr(certificate, "output_format", "pdf"),
                "status": getattr(certificate, "status", "generated"),
                "error_message": getattr(certificate, "error_message", None),
                "created_at": format_datetime(getattr(certificate, "created_at", None))
            }
            self.fs.collection("certificates").document(c_dict["id"]).set(c_dict)
            return FirestoreCertificate(**c_dict)

        # Fallback to SQLite
        self.db.add(certificate)
        self.db.commit()
        self.db.refresh(certificate)
        return certificate

    # -------------------------------------------------------------------------
    # GENERATION JOBS
    # -------------------------------------------------------------------------
    def create_job(self, project_id: str, total_rows: int) -> Any:
        job_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        if self.use_firebase:
            job_dict = {
                "id": job_id,
                "project_id": project_id,
                "status": "processing",
                "total_rows": total_rows,
                "processed_rows": 0,
                "successful_count": 0,
                "failed_count": 0,
                "current_participant": None,
                "error_log": [],
                "zip_filename": None,
                "zip_path": None,
                "created_at": now_iso,
                "completed_at": None
            }
            self.fs.collection("generation_jobs").document(job_id).set(job_dict)
            return FirestoreJob(**job_dict)

        # Fallback to SQLite
        job = GenerationJob(
            project_id=project_id,
            status="processing",
            total_rows=total_rows,
            processed_rows=0,
            successful_count=0,
            failed_count=0
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_job(self, job_id: str) -> Optional[Any]:
        if self.use_firebase:
            doc = self.fs.collection("generation_jobs").document(job_id).get()
            if not doc.exists:
                return None
            return FirestoreJob(**doc.to_dict())

        # Fallback to SQLite
        return self.db.query(GenerationJob).filter(GenerationJob.id == job_id).first()

    def update_job(self, job_id: str, **kwargs) -> Optional[Any]:
        if self.use_firebase:
            doc_ref = self.fs.collection("generation_jobs").document(job_id)
            if not doc_ref.get().exists:
                return None
            updates = dict(kwargs)
            if "completed_at" in updates and isinstance(updates["completed_at"], datetime):
                updates["completed_at"] = updates["completed_at"].isoformat()
            doc_ref.update(updates)
            return self.get_job(job_id)

        # Fallback to SQLite
        job = self.get_job(job_id)
        if not job:
            return None
        for key, value in kwargs.items():
            if hasattr(job, key):
                setattr(job, key, value)
        self.db.commit()
        self.db.refresh(job)
        return job
