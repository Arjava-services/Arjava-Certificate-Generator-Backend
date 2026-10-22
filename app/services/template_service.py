import os
import re
import uuid
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
from PIL import Image
import pymupdf as fitz
from app.config.settings import settings
from app.schemas.template import PlaceholderInfo

PLACEHOLDER_REGEX = re.compile(r'(\{\{\s*([a-zA-Z0-9_\-\.]+)\s*\}\})')

class TemplateService:
    def process_uploaded_template(
        self,
        file_bytes: bytes,
        original_filename: str
    ) -> Tuple[str, str, str, float, float, List[PlaceholderInfo]]:
        """
        Processes uploaded template file (PDF, PNG, JPG).
        Returns:
            (template_filename, file_type, preview_image_filename, width, height, detected_placeholders)
        """
        ext = Path(original_filename).suffix.lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported file format '{ext}'. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}")

        unique_id = str(uuid.uuid4())
        template_filename = f"{unique_id}{ext}"
        target_path = settings.TEMPLATES_DIR / template_filename

        with open(target_path, "wb") as f:
            f.write(file_bytes)

        if ext == ".pdf":
            return self._process_pdf_template(target_path, template_filename, unique_id)
        else:
            return self._process_image_template(target_path, template_filename, unique_id, ext)

    def _process_pdf_template(
        self,
        pdf_path: Path,
        template_filename: str,
        unique_id: str
    ) -> Tuple[str, str, str, float, float, List[PlaceholderInfo]]:
        """Extracts PDF dimensions, page 1 preview image, and embedded placeholders."""
        doc = fitz.open(pdf_path)
        if len(doc) == 0:
            raise ValueError("The uploaded PDF has no pages.")

        page = doc[0]
        rect = page.rect
        width = float(rect.width)
        height = float(rect.height)

        # Render preview image at 2.0x scale (approx 144 DPI) for crisp frontend rendering
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        preview_filename = f"{unique_id}_preview.png"
        preview_path = settings.TEMPLATES_DIR / preview_filename
        pix.save(str(preview_path))

        # Detect placeholders inside PDF text
        detected: List[PlaceholderInfo] = []
        text_page = page.get_text("words")  # list of (x0, y0, x1, y1, "word", block_no, line_no, word_no)
        
        # Also inspect full text blocks for {{placeholder}} patterns
        text_blocks = page.get_text("blocks")
        found_keys = set()

        for b in text_blocks:
            block_text = b[4]
            matches = PLACEHOLDER_REGEX.findall(block_text)
            for full_match, key in matches:
                clean_key = f"{{{{{key.strip()}}}}}"
                if clean_key not in found_keys:
                    found_keys.add(clean_key)
                    # Search rect for this placeholder
                    rects = page.search_for(full_match)
                    if rects:
                        r = rects[0]
                        detected.append(PlaceholderInfo(
                            placeholder=clean_key,
                            raw_text=full_match,
                            x_pos=round(float(r.x0 + r.width / 2.0), 1),
                            y_pos=round(float(r.y0 + r.height / 2.0), 1),
                            width=round(float(r.width), 1),
                            height=round(float(r.height), 1),
                            font_size=max(16, min(48, int(r.height * 0.85))),
                            font_name="Helvetica",
                            alignment="center"
                        ))

        # If no explicit {{...}} detected in PDF, provide default intelligent template placeholders
        if not detected:
            detected = self._get_default_placeholders(width, height)

        doc.close()
        return (template_filename, "pdf", preview_filename, width, height, detected)

    def _process_image_template(
        self,
        image_path: Path,
        template_filename: str,
        unique_id: str,
        ext: str
    ) -> Tuple[str, str, str, float, float, List[PlaceholderInfo]]:
        """Extracts dimensions from image and creates web preview."""
        with Image.open(image_path) as img:
            width, height = img.size
            # Convert RGBA/P to RGB if JPEG
            preview_filename = f"{unique_id}_preview.png"
            preview_path = settings.TEMPLATES_DIR / preview_filename
            img.save(preview_path, format="PNG")

        detected = self._get_default_placeholders(float(width), float(height))
        return (template_filename, ext.lstrip("."), preview_filename, float(width), float(height), detected)

    def _get_default_placeholders(self, width: float, height: float) -> List[PlaceholderInfo]:
        """Returns only 2 standard certificate placeholder positions (Name, Title)."""
        center_x = round(width / 2.0, 1)
        return [
            PlaceholderInfo(
                placeholder="{{name}}",
                x_pos=center_x,
                y_pos=round(height * 0.46, 1),
                width=round(width * 0.7, 1),
                height=round(height * 0.08, 1),
                font_name="Helvetica",
                font_size=32,
                alignment="center"
            ),
            PlaceholderInfo(
                placeholder="{{title}}",
                x_pos=center_x,
                y_pos=round(height * 0.60, 1),
                width=round(width * 0.6, 1),
                height=round(height * 0.06, 1),
                font_name="Helvetica",
                font_size=22,
                alignment="center"
            ),
        ]

template_service = TemplateService()
