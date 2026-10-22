from pathlib import Path
from reportlab.lib.pagesizes import landscape, A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from PIL import Image, ImageDraw, ImageFont

def generate_sample_pdf_template(output_path: Path):
    """Generates an elegant, high-res sample certificate PDF with placeholders."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    w, h = landscape(A4) # 841.89 x 595.27
    c = canvas.Canvas(str(output_path), pagesize=(w, h))

    # Background clean cream / slate gradient-like feel
    c.setFillColor(colors.HexColor("#f8fafc"))
    c.rect(0, 0, w, h, fill=1, stroke=0)

    # Outer ornate borders
    c.setStrokeColor(colors.HexColor("#0f172a"))
    c.setLineWidth(3)
    c.rect(24, 24, w - 48, h - 48)

    c.setStrokeColor(colors.HexColor("#6366f1")) # Indigo
    c.setLineWidth(1.5)
    c.rect(32, 32, w - 64, h - 64)

    # Corner accents
    for x_corner, y_corner in [(32, 32), (w - 32, 32), (32, h - 32), (w - 32, h - 32)]:
        c.setFillColor(colors.HexColor("#4f46e5"))
        c.circle(x_corner, y_corner, 5, fill=1, stroke=0)

    # Header Ribbon / Subtitle
    c.setFillColor(colors.HexColor("#4338ca"))
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(w / 2.0, h - 90, "GLOBAL TECH ACADEMY & INNOVATION SUMMIT")

    # Main Certificate Title
    c.setFillColor(colors.HexColor("#0f172a"))
    c.setFont("Helvetica-Bold", 34)
    c.drawCentredString(w / 2.0, h - 135, "CERTIFICATE OF EXCELLENCE")

    # Presentation text
    c.setFillColor(colors.HexColor("#64748b"))
    c.setFont("Helvetica", 14)
    c.drawCentredString(w / 2.0, h - 175, "THIS IS PROUDLY PRESENTED TO")

    # Participant Name Placeholder
    c.setFillColor(colors.HexColor("#1e1b4b"))
    c.setFont("Helvetica-Bold", 30)
    c.drawCentredString(w / 2.0, h - 235, "{{name}}")

    # Divider bar
    c.setStrokeColor(colors.HexColor("#cbd5e1"))
    c.setLineWidth(1)
    c.line(w / 2.0 - 180, h - 255, w / 2.0 + 180, h - 255)

    # Reason / Competition
    c.setFillColor(colors.HexColor("#475569"))
    c.setFont("Helvetica", 14)
    c.drawCentredString(w / 2.0, h - 290, "For outstanding achievement and dedication in")

    c.setFillColor(colors.HexColor("#2563eb"))
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(w / 2.0, h - 325, "{{competition}}")

    # Position
    c.setFillColor(colors.HexColor("#0f172a"))
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(w / 2.0, h - 365, "Awarded the distinction of: {{position}}")

    # Signatures & Date
    # Left: Date
    c.setStrokeColor(colors.HexColor("#94a3b8"))
    c.line(100, 100, 260, 100)
    c.setFillColor(colors.HexColor("#1e293b"))
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(180, 115, "{{date}}")
    c.setFillColor(colors.HexColor("#64748b"))
    c.setFont("Helvetica", 11)
    c.drawCentredString(180, 85, "Issue Date")

    # Center: Year
    c.setFillColor(colors.HexColor("#64748b"))
    c.setFont("Helvetica", 11)
    c.drawCentredString(w / 2.0, 85, "Academic Year {{year}}")

    # Right: Signature
    c.setStrokeColor(colors.HexColor("#94a3b8"))
    c.line(w - 260, 100, w - 100, 100)
    c.setFillColor(colors.HexColor("#1e293b"))
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(w - 180, 115, "Dr. Alexander Wright")
    c.setFillColor(colors.HexColor("#64748b"))
    c.setFont("Helvetica", 11)
    c.drawCentredString(w - 180, 85, "Program Director")

    c.save()
    print(f"Generated sample PDF template at: {output_path}")

def generate_sample_png_template(output_path: Path):
    """Generates an image template (PNG)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    w, h = 1200, 850
    img = Image.new("RGB", (w, h), color="#fcfcfd")
    draw = ImageDraw.Draw(img)

    # Border
    draw.rectangle([25, 25, w - 25, h - 25], outline="#0f172a", width=4)
    draw.rectangle([35, 35, w - 35, h - 35], outline="#3b82f6", width=2)

    # Simple clean styling
    draw.text((w // 2 - 220, 100), "CERTIFICATE OF PARTICIPATION", fill="#0f172a")
    img.save(output_path, format="PNG")
    print(f"Generated sample PNG template at: {output_path}")

if __name__ == "__main__":
    base = Path(__file__).parent / "data" / "sample_templates"
    generate_sample_pdf_template(base / "elegant_award_certificate.pdf")
    generate_sample_png_template(base / "modern_minimal_certificate.png")
