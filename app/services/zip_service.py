import zipfile
from pathlib import Path
from typing import List
from app.models.entities import Certificate

class ZipService:
    def create_certificates_zip(
        self,
        certificates: List[Certificate],
        zip_output_path: Path
    ) -> Path:
        """
        Creates a ZIP archive containing all generated certificate files.
        Deduplicates filenames inside the archive if necessary.
        """
        zip_output_path.parent.mkdir(parents=True, exist_ok=True)
        used_filenames = set()

        with zipfile.ZipFile(zip_output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for cert in certificates:
                if cert.status != "generated":
                    continue
                file_path = Path(cert.file_path)
                if not file_path.exists():
                    continue

                archive_name = cert.filename
                # Handle duplicates inside zip if multiple participants share exact name and year
                stem = Path(archive_name).stem
                suffix = Path(archive_name).suffix
                counter = 2
                while archive_name.lower() in used_filenames:
                    archive_name = f"{stem}_{counter}{suffix}"
                    counter += 1
                used_filenames.add(archive_name.lower())

                zf.write(file_path, arcname=archive_name)

        return zip_output_path

zip_service = ZipService()
