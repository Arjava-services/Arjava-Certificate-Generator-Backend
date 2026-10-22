import re
import os
import io
import base64
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont
import pymupdf as fitz
from app.config.settings import settings
from app.models.entities import Project, ProjectFieldMapping

# Safe filename regex
FILENAME_SAFE_REGEX = re.compile(r'[^a-zA-Z0-9_\-\.]')

def hex_to_rgb(color_val: str) -> Tuple[int, int, int]:
    """Convert hex or rgb string like #1e293b, #fff, rgb(17, 45, 50) to (R, G, B) tuple."""
    if not color_val:
        return (17, 45, 50)
    s = str(color_val).strip()
    if s.lower().startswith("rgb"):
        m = re.search(r'rgba?\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)', s, re.IGNORECASE)
        if m:
            return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    s = s.lstrip("#")
    if len(s) == 3:
        s = "".join([c * 2 for c in s])
    if len(s) >= 6:
        try:
            return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
        except ValueError:
            pass
    return (17, 45, 50)

def hex_to_pdf_color(color_val: str) -> Tuple[float, float, float]:
    """Convert hex color string like #1e293b to (r, g, b) float tuple 0.0-1.0."""
    r, g, b = hex_to_rgb(color_val)
    return (r / 255.0, g / 255.0, b / 255.0)

BASE_FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
WIN_FONTS_DIR = Path("C:/Windows/Fonts")

# Fonts whose files genuinely contain bold glyph outlines.
# For all other fonts, if bold is requested, a faux-bold stroke is applied
# so that all fonts render consistently bold and never revert to thin/regular.
GENUINE_BOLD_FONTS = {
    "timesbd", "georgiab", "bod_b", "garabd", "courbd", "arialbd", "calibrib",
    "poppins-bold", "cinzeldecorative-bold", "tangerine-bold", "roboto-bold",
    "consolab", "trebucbd", "segoeuib", "verdanab", "cambriab"
}

def resolve_font_path(family: str, font_weight: str = "normal", is_italic: bool = False) -> str:
    fam = (family or "").lower().strip()
    is_bold = str(font_weight).lower() in ["bold", "700", "800", "900", "semibold"]
    is_italic = bool(is_italic)

    def check_asset(name: str) -> Optional[str]:
        p = BASE_FONTS_DIR / name
        return str(p) if p.exists() else None

    def check_win(name: str) -> Optional[str]:
        p = WIN_FONTS_DIR / name
        return str(p) if p.exists() else None

    # 1. Cinzel Decorative
    if "cinzel decorative" in fam or "cinzeldecorative" in fam:
        if is_bold:
            f = check_asset("CinzelDecorative-Bold.ttf")
            if f: return f
        f = check_asset("CinzelDecorative-Regular.ttf")
        if f: return f

    # 2. Cinzel
    if "cinzel" in fam:
        if is_bold:
            f = check_asset("Cinzel-Bold.ttf")
            if f: return f
        f = check_asset("Cinzel-Regular.ttf")
        if f: return f

    # 3. Playfair Display
    if "playfair" in fam:
        if is_bold:
            f = check_asset("PlayfairDisplay-Bold.ttf")
            if f: return f
        if is_italic:
            f = check_asset("PlayfairDisplay-Italic.ttf")
            if f: return f
        f = check_asset("PlayfairDisplay-Regular.ttf")
        if f: return f

    # 4. Oswald
    if "oswald" in fam:
        if is_bold:
            f = check_asset("Oswald-Bold.ttf")
            if f: return f
        f = check_asset("Oswald-Regular.ttf")
        if f: return f

    # 5. EB Garamond
    if "eb garamond" in fam or "ebgaramond" in fam:
        if is_italic:
            f = check_asset("EBGaramond-Italic.ttf")
            if f: return f
        f = check_asset("EBGaramond-Regular.ttf")
        if f: return f

    # 6. Garamond / Cormorant Garamond
    if "garamond" in fam:
        if is_bold:
            f = check_win("GARABD.TTF")
            if f: return f
        if is_italic:
            f = check_win("GARAIT.TTF") or check_asset("EBGaramond-Italic.ttf")
            if f: return f
        f = check_win("GARA.TTF") or check_asset("EBGaramond-Regular.ttf")
        if f: return f

    # 7. Dancing Script
    if "dancing" in fam:
        f = check_asset("DancingScript-Regular.ttf")
        if f: return f

    # 8. Great Vibes
    if "vibes" in fam:
        f = check_asset("GreatVibes-Regular.ttf")
        if f: return f

    # 9. Alex Brush / Brush Script
    if "alex" in fam or "brush" in fam:
        f = check_asset("AlexBrush-Regular.ttf") or check_win("BRUSHSCI.TTF")
        if f: return f

    # 10. Allura
    if "allura" in fam:
        f = check_asset("Allura-Regular.ttf")
        if f: return f

    # 11. Parisienne
    if "parisienne" in fam:
        f = check_asset("Parisienne-Regular.ttf")
        if f: return f

    # 12. Italianno
    if "italianno" in fam:
        f = check_asset("Italianno-Regular.ttf")
        if f: return f

    # 13. Sacramento
    if "sacramento" in fam:
        f = check_asset("Sacramento-Regular.ttf")
        if f: return f

    # 14. Tangerine
    if "tangerine" in fam:
        if is_bold:
            f = check_asset("Tangerine-Bold.ttf")
            if f: return f
        f = check_asset("Tangerine-Regular.ttf")
        if f: return f

    # 15. Prata
    if "prata" in fam:
        f = check_asset("Prata-Regular.ttf")
        if f: return f

    # 16. Marcellus
    if "marcellus" in fam:
        f = check_asset("Marcellus-Regular.ttf")
        if f: return f

    # 17. Lora
    if "lora" in fam:
        if is_bold:
            f = check_asset("Lora-Bold.ttf")
            if f: return f
        f = check_asset("Lora-Regular.ttf")
        if f: return f

    # 18. Poppins
    if "poppins" in fam:
        if is_bold:
            f = check_asset("Poppins-Bold.ttf")
            if f: return f
        f = check_asset("Poppins-Regular.ttf")
        if f: return f

    # 19. Montserrat
    if "montserrat" in fam:
        if is_bold:
            f = check_asset("Montserrat-Bold.ttf")
            if f: return f
        f = check_asset("Montserrat-Regular.ttf")
        if f: return f

    # 20. Raleway
    if "raleway" in fam:
        if is_bold:
            f = check_asset("Raleway-Bold.ttf")
            if f: return f
        f = check_asset("Raleway-Regular.ttf")
        if f: return f

    # 21. Roboto
    if "roboto" in fam:
        if is_bold:
            f = check_asset("Roboto-Bold.ttf") or check_win("arialbd.ttf")
            if f: return f
        f = check_asset("Roboto-Regular.ttf") or check_win("arial.ttf")
        if f: return f

    # 22. Inter / Modern Sans
    if "inter" in fam or "outfit" in fam or "jakarta" in fam:
        if is_bold:
            f = check_asset("Inter-Bold.ttf") or check_win("arialbd.ttf")
            if f: return f
        f = check_asset("Inter-Regular.ttf") or check_win("arial.ttf")
        if f: return f

    # 23. Abril Fatface
    if "abril" in fam:
        f = check_asset("AbrilFatface-Regular.ttf")
        if f: return f

    # 24. Bodoni
    if "bodoni" in fam:
        if is_bold:
            f = check_win("BOD_B.TTF")
            if f: return f
        f = check_win("BOD_R.TTF")
        if f: return f

    # 25. Georgia
    if "georgia" in fam:
        if is_bold and is_italic:
            f = check_win("georgiaz.ttf")
            if f: return f
        if is_bold:
            f = check_win("georgiab.ttf")
            if f: return f
        if is_italic:
            f = check_win("georgiai.ttf")
            if f: return f
        f = check_win("georgia.ttf")
        if f: return f

    # 26. Times New Roman
    if "times" in fam:
        if is_bold and is_italic:
            f = check_win("timesbi.ttf")
            if f: return f
        if is_bold:
            f = check_win("timesbd.ttf")
            if f: return f
        if is_italic:
            f = check_win("timesi.ttf")
            if f: return f
        f = check_win("times.ttf")
        if f: return f

    # 27. Courier New
    if "courier" in fam:
        if is_bold:
            f = check_win("courbd.ttf")
            if f: return f
        if is_italic:
            f = check_win("couri.ttf")
            if f: return f
        f = check_win("cour.ttf")
        if f: return f

    # 28. Monospace
    if "mono" in fam or "space" in fam or "jetbrains" in fam:
        if is_bold:
            f = check_win("consolab.ttf") or check_win("courbd.ttf")
            if f: return f
        f = check_win("consola.ttf") or check_win("cour.ttf")
        if f: return f

    # 29. Any cursive / script
    if any(s in fam for s in ["script", "cursive", "signature", "callig", "edward"]):
        f = check_win("segoesc.ttf") or check_win("BRUSHSCI.TTF") or check_asset("GreatVibes-Regular.ttf")
        if f: return f

    # 30. Any generic serif
    if "serif" in fam:
        if is_bold:
            f = check_asset("PlayfairDisplay-Bold.ttf") or check_win("georgiab.ttf") or check_win("timesbd.ttf")
            if f: return f
        f = check_win("georgia.ttf") or check_win("times.ttf")
        if f: return f

    # 31. Modern Sans fallback (Inter / Arial / Calibri)
    if is_bold and is_italic:
        f = check_win("arialbi.ttf") or check_win("calibriz.ttf")
        if f: return f
    if is_bold:
        f = check_asset("Inter-Bold.ttf") or check_win("arialbd.ttf") or check_win("calibrib.ttf")
        if f: return f
    if is_italic:
        f = check_win("ariali.ttf") or check_win("calibrii.ttf")
        if f: return f
    f = check_asset("Inter-Regular.ttf") or check_win("arial.ttf") or check_win("calibri.ttf")
    if f: return f

    return "arial.ttf"

class CertificateGeneratorService:
    def sanitize_filename(self, name: str) -> str:
        """Replace spaces with underscores and remove unsafe filesystem characters."""
        # Replace spaces with underscores
        s = name.strip().replace(" ", "_")
        # Remove unsafe chars
        s = FILENAME_SAFE_REGEX.sub("", s)
        # Collapse multiple underscores
        s = re.sub(r'_+', '_', s)
        return s.strip("._") or "certificate"

    def build_filename(
        self,
        naming_pattern: str,
        row_data: Dict[str, Any],
        mappings: List[ProjectFieldMapping],
        output_format: str,
        row_index: int
    ) -> str:
        """
        Builds a safe, personalized filename based on the pattern, e.g. {{name}}_Certificate_{{year}}.pdf.
        """
        pattern = (naming_pattern or "").strip() or "{{name}}_Certificate"
        
        # Build comprehensive placeholder to value map
        value_map = {}
        for m in (mappings or []):
            ph = m.placeholder or ""
            clean_ph = ph.strip("{}").strip().lower()
            val = ""
            if m.sheet_column and m.sheet_column in row_data:
                val = str(row_data[m.sheet_column]).strip()
            
            if val:
                value_map[ph] = val
                value_map[ph.lower()] = val
                value_map[clean_ph] = val
                value_map[clean_ph.replace(" ", "_")] = val
                value_map[clean_ph.replace("_", " ")] = val
                value_map[re.sub(r'[\s_\-]+', '', clean_ph)] = val

        # Also map all row data columns directly (case-insensitive and format-tolerant)
        for k, v in row_data.items():
            if not k.startswith("_"):
                val_str = str(v).strip()
                k_clean = str(k).strip()
                k_lower = k_clean.lower()
                value_map[k_clean] = val_str
                value_map[k_lower] = val_str
                value_map[k_lower.replace(" ", "_")] = val_str
                value_map[k_lower.replace("_", " ")] = val_str
                value_map[re.sub(r'[\s_\-]+', '', k_lower)] = val_str

        # Substitute placeholders in pattern (supporting spaces, e.g. {{Student Name}}, {{College Name}})
        def replacer(match):
            raw_key = match.group(1).strip()
            key_clean = raw_key.strip("{}").strip()
            key_lower = key_clean.lower()

            candidates = [
                key_clean,
                key_lower,
                key_lower.replace(" ", "_"),
                key_lower.replace("_", " "),
                re.sub(r'[\s_\-]+', '', key_lower)
            ]
            for cand in candidates:
                if cand in value_map and value_map[cand]:
                    return value_map[cand]

            # If key refers to name / participant, attempt finding participant name in row_data
            if any(term in key_lower for term in ("name", "participant", "student", "candidate")):
                for col_name in ("Name", "name", "Full Name", "Participant Name", "Student Name", "Candidate Name", "Participant", "Student"):
                    if col_name in row_data and str(row_data[col_name]).strip():
                        return str(row_data[col_name]).strip()

            return ""

        result_name = re.sub(r'\{\{\s*([^{}]+?)\s*\}\}', replacer, pattern)
        
        # Clean up repeated separators or trailing/leading underscores/hyphens from missing placeholders
        result_name = re.sub(r'[_ \-]+', '_', result_name).strip('_-')
        sanitized = self.sanitize_filename(result_name)

        if not sanitized or sanitized.lower() in ("certificate", "cert"):
            participant = ""
            for col_name in ("Name", "name", "Full Name", "Participant Name", "Student Name", "Candidate Name", "Participant", "Student"):
                if col_name in row_data and str(row_data[col_name]).strip():
                    participant = str(row_data[col_name]).strip()
                    break
            if not participant:
                for k, v in row_data.items():
                    if not k.startswith("_") and str(v).strip():
                        participant = str(v).strip()
                        break
            if not participant:
                participant = f"Participant_{row_index}"

            if sanitized and sanitized.lower() in ("certificate", "cert"):
                sanitized = f"{self.sanitize_filename(participant)}_{sanitized}"
            else:
                sanitized = f"{self.sanitize_filename(participant)}_Certificate"

        ext = (output_format or "pdf").lower().lstrip(".")
        return f"{sanitized}.{ext}"

    def render_certificate(
        self,
        project: Project,
        mappings: List[ProjectFieldMapping],
        row_data: Dict[str, Any],
        output_format: str = "pdf"
    ) -> bytes:
        """
        Renders a single personalized certificate as bytes.
        Supports PDF, PNG, JPG.
        """
        template_path = settings.TEMPLATES_DIR / project.template_filename
        if not template_path.exists():
            raise FileNotFoundError(f"Template file '{project.template_filename}' not found.")

        # Determine if template is PDF or Image
        is_pdf_template = (project.template_file_type == "pdf")

        if is_pdf_template:
            return self._render_pdf_template(template_path, mappings, row_data, output_format, project)
        else:
            return self._render_image_template(template_path, mappings, row_data, output_format, project)

    def _render_pdf_template(
        self,
        template_path: Path,
        mappings: List[ProjectFieldMapping],
        row_data: Dict[str, Any],
        output_format: str,
        project: Project
    ) -> bytes:
        doc = fitz.open(template_path)
        page = doc[0]

        # First, search and remove literal {{placeholder}} text from the template page if present
        for m in mappings:
            ph = m.placeholder
            rects = page.search_for(ph)
            for r in rects:
                # Redact the placeholder with white/transparent fill so the text doesn't show
                page.add_redact_annot(r, fill=(1, 1, 1))
        page.apply_redactions()

        # Proportional scale in case PDF page size differs from project.template_width / height
        page_w = page.rect.width
        page_h = page.rect.height
        proj_w = float(getattr(project, 'template_width', 0) or page_w)
        proj_h = float(getattr(project, 'template_height', 0) or page_h)

        scale_x = page_w / proj_w if proj_w > 0 else 1.0
        scale_y = page_h / proj_h if proj_h > 0 else 1.0
        scale_font = (scale_x + scale_y) / 2.0

        # Now, insert the personalized replacement text for each mapping
        for idx, m in enumerate(mappings):
            val = ""
            if m.sheet_column:
                if m.sheet_column in row_data:
                    val = str(row_data[m.sheet_column] or "").strip()
                else:
                    col_clean = m.sheet_column.strip().lower()
                    for k, v in row_data.items():
                        if str(k).strip().lower() == col_clean:
                            val = str(v or "").strip()
                            break
            elif not m.sheet_column:
                # Static custom text element added by user
                val = m.placeholder.replace("{{", "").replace("}}", "").strip()
            if not val:
                continue

            # Normalize internal spaces so names don't have asymmetric padding
            val = " ".join(val.split())

            # Apply text transformation
            if getattr(m, 'text_case', None) == "uppercase":
                val = val.upper()
            elif getattr(m, 'text_case', None) == "lowercase":
                val = val.lower()
            elif getattr(m, 'text_case', None) == "capitalize":
                val = val.title()

            font_size = max(8.0, float(m.font_size or 24) * scale_font)
            color = hex_to_pdf_color(m.font_color or "#112D32")
            align_code = fitz.TEXT_ALIGN_CENTER
            if m.alignment == "left":
                align_code = fitz.TEXT_ALIGN_LEFT
            elif m.alignment == "right":
                align_code = fitz.TEXT_ALIGN_RIGHT

            # Scaled Coordinates
            x = float(m.x_pos) * scale_x
            y = float(m.y_pos) * scale_y

            font_family = getattr(m, 'font_family', '') or 'helvetica'
            font_weight = str(getattr(m, 'font_weight', 'normal'))
            is_italic = bool(getattr(m, 'is_italic', False))

            font_file = resolve_font_path(font_family, font_weight, is_italic)
            fontname = None
            if font_file and os.path.exists(font_file):
                try:
                    fontname = f"cfont_{idx}"
                    page.insert_font(fontname=fontname, fontfile=font_file)
                except Exception:
                    fontname = None

            if not fontname:
                font_family_lower = font_family.lower()
                is_bold_flag = font_weight.lower() in ["bold", "700", "800", "900", "semibold"]
                if any(s in font_family_lower for s in ["times", "serif", "playfair", "cinzel", "georgia", "garamond", "lora", "merriweather", "script", "vibes", "brush", "parisienne", "italianno", "bodoni", "prata", "marcellus", "dancing", "allura", "tangerine", "sacramento", "abril"]):
                    if is_bold_flag and is_italic:
                        fontname = "tibi"
                    elif is_bold_flag:
                        fontname = "tibo"
                    elif is_italic:
                        fontname = "tiit"
                    else:
                        fontname = "times"
                elif any(s in font_family_lower for s in ["courier", "mono", "space"]):
                    if is_bold_flag and is_italic:
                        fontname = "cobi"
                    elif is_bold_flag:
                        fontname = "cobo"
                    elif is_italic:
                        fontname = "coit"
                    else:
                        fontname = "couri"
                else:
                    if is_bold_flag and is_italic:
                        fontname = "hebi"
                    elif is_bold_flag:
                        fontname = "hebo"
                    elif is_italic:
                        fontname = "heit"
                    else:
                        fontname = "helv"

            # Ample vertical box height centered at y so PyMuPDF never wraps or fails
            box_h = max(font_size * 2.2, 50.0)
            y0 = y - (font_size * 0.75)
            y1 = y0 + box_h

            if m.alignment == "left":
                rect = fitz.Rect(x, y0, page_w - 20, y1)
            elif m.alignment == "right":
                rect = fitz.Rect(20, y0, x, y1)
            else: # center
                span = min(x - 10, page_w - x - 10)
                if span < 100:
                    span = max(page_w * 0.45, 200.0)
                rect = fitz.Rect(x - span, y0, x + span, y1)

            # Insert formatted text into box
            page.insert_textbox(
                rect,
                val,
                fontsize=font_size,
                fontname=fontname,
                color=color,
                align=align_code
            )

        output_fmt = output_format.lower()
        if output_fmt == "pdf":
            out_bytes = doc.tobytes()
            doc.close()
            return out_bytes
        else:
            # Convert to PNG or JPG
            zoom = 2.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=(output_fmt == "png"))
            img_bytes = pix.tobytes(output_fmt)
            doc.close()
            return img_bytes

    def _render_image_template(
        self,
        template_path: Path,
        mappings: List[ProjectFieldMapping],
        row_data: Dict[str, Any],
        output_format: str,
        project: Project
    ) -> bytes:
        with Image.open(template_path) as base_img:
            # Always work in RGBA for pristine font antialiasing and alpha blending
            img = base_img.convert("RGBA")
            draw = ImageDraw.Draw(img)

            img_w, img_h = img.size
            proj_w = float(getattr(project, 'template_width', 0) or img_w)
            proj_h = float(getattr(project, 'template_height', 0) or img_h)

            scale_x = img_w / proj_w if proj_w > 0 else 1.0
            scale_y = img_h / proj_h if proj_h > 0 else 1.0
            scale_font = (scale_x + scale_y) / 2.0

            for m in mappings:
                val = ""
                if m.sheet_column:
                    if m.sheet_column in row_data:
                        val = str(row_data[m.sheet_column] or "").strip()
                    else:
                        col_clean = m.sheet_column.strip().lower()
                        for k, v in row_data.items():
                            if str(k).strip().lower() == col_clean:
                                val = str(v or "").strip()
                                break
                elif not m.sheet_column:
                    # Static custom text element added by user
                    val = m.placeholder.replace("{{", "").replace("}}", "").strip()

                if not val:
                    continue

                # Normalize internal spaces so names don't have asymmetric padding
                val = " ".join(val.split())

                if getattr(m, 'text_case', None) == "uppercase":
                    val = val.upper()
                elif getattr(m, 'text_case', None) == "lowercase":
                    val = val.lower()
                elif getattr(m, 'text_case', None) == "capitalize":
                    val = val.title()

                font_size = max(8, int(float(m.font_size or 24) * scale_font))
                rgb = hex_to_rgb(getattr(m, 'font_color', None) or "#112D32")
                opacity = float(getattr(m, 'opacity', 1.0) if getattr(m, 'opacity', 1.0) is not None else 1.0)
                alpha = int(max(0.0, min(1.0, opacity)) * 255)
                fill_color = (rgb[0], rgb[1], rgb[2], alpha)

                # Resolve font accurately
                font_family = getattr(m, 'font_family', 'Helvetica')
                font_weight = str(getattr(m, 'font_weight', 'normal'))
                is_italic = bool(getattr(m, 'is_italic', False))
                is_bold = str(font_weight).lower() in ["bold", "700", "800", "900", "semibold"]

                font_path = resolve_font_path(font_family, font_weight, is_italic)
                font = None
                try:
                    font = ImageFont.truetype(font_path, font_size)
                except Exception:
                    try:
                        font = ImageFont.truetype("arial.ttf", font_size)
                    except Exception:
                        font = ImageFont.load_default()

                # If bold is requested, check if the loaded font file has genuine bold outlines.
                # If not (e.g. bundled font copies that share regular outlines), apply crisp faux bold stroke.
                stem = Path(font_path).stem.lower() if font_path else ""
                is_genuinely_bold = stem in GENUINE_BOLD_FONTS
                if is_bold:
                    if is_genuinely_bold:
                        stroke_w = 0
                        stroke_f = None
                    else:
                        stroke_w = max(1, round(font_size * 0.032))
                        stroke_f = fill_color
                else:
                    stroke_w = 0
                    stroke_f = None

                x = float(m.x_pos) * scale_x
                y = float(m.y_pos) * scale_y
                alignment = (getattr(m, 'alignment', 'center') or "center").lower()

                # Pillow text anchoring:
                # Use font-metrics baseline anchoring so dynamic names with or without descenders
                # (e.g. 'y', 'p', 'g' vs 'A', 'M') sit on the EXACT identical baseline and do not jump!
                try:
                    ascent, descent = font.getmetrics()
                    y_render = y + (ascent - descent) / 2.0
                    pil_anchor = "ms" if alignment == "center" else ("ls" if alignment == "left" else "rs")
                except Exception:
                    y_render = y
                    pil_anchor = "mm" if alignment == "center" else ("lm" if alignment == "left" else "rm")

                # Text effect shadows if configured
                text_effect = getattr(m, 'text_effect', 'none')
                if text_effect == "drop":
                    draw.text((x + 2 * scale_x, y_render + 2 * scale_y), val, fill=(0, 0, 0, int(alpha * 0.45)), font=font, anchor=pil_anchor)
                elif text_effect == "soft":
                    draw.text((x + 1 * scale_x, y_render + 1 * scale_y), val, fill=(0, 0, 0, int(alpha * 0.3)), font=font, anchor=pil_anchor)

                draw.text(
                    (x, y_render),
                    val,
                    fill=fill_color,
                    font=font,
                    anchor=pil_anchor,
                    stroke_width=stroke_w,
                    stroke_fill=stroke_f
                )

            buf = io.BytesIO()
            fmt = output_format.lower()
            if fmt == "pdf":
                img_rgb = Image.new("RGB", img.size, (255, 255, 255))
                img_rgb.paste(img, mask=img.split()[3])
                img_rgb.save(buf, format="PDF", resolution=150.0)
            elif fmt in ["jpg", "jpeg"]:
                img_rgb = Image.new("RGB", img.size, (255, 255, 255))
                img_rgb.paste(img, mask=img.split()[3])
                img_rgb.save(buf, format="JPEG", quality=95)
            else:
                img.save(buf, format="PNG")

            return buf.getvalue()

    def generate_preview_base64(
        self,
        project: Project,
        mappings: List[ProjectFieldMapping],
        row_data: Dict[str, Any]
    ) -> str:
        """Renders preview as base64 PNG data URI for instant responsive UI preview."""
        cert_bytes = self.render_certificate(
            project=project,
            mappings=mappings,
            row_data=row_data,
            output_format="png"
        )
        b64 = base64.b64encode(cert_bytes).decode("utf-8")
        return f"data:image/png;base64,{b64}"

certificate_generator_service = CertificateGeneratorService()
