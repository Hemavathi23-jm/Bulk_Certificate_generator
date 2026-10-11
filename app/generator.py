import os
from pathlib import Path
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.pdfgen import canvas

def generate_pdf_certificate(
    output_path: Path,
    recipient_name: str,
    event_name: str,
    issuer_name: str,
    issue_date: str,
    certificate_title: str = "Certificate of Achievement",
    certificate_id: str = "",
    custom_attributes: dict = None
) -> Path:
    """
    Generates a professional, print-ready landscape PDF certificate using ReportLab.
    """
    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    width, height = landscape(A4)  # ~ 841.89 x 595.27 pt
    c = canvas.Canvas(str(output_path), pagesize=(width, height))

    # Color Palette
    navy_dark = colors.HexColor("#0D2137")
    gold_primary = colors.HexColor("#C59B27")
    gold_light = colors.HexColor("#E5C365")
    slate_gray = colors.HexColor("#4A5568")
    cream_bg = colors.HexColor("#FCFBF7")

    # 1. Subtle warm background
    c.setFillColor(cream_bg)
    c.rect(0, 0, width, height, fill=True, stroke=False)

    # 2. Outer decorative border
    c.setStrokeColor(navy_dark)
    c.setLineWidth(6)
    c.rect(24, 24, width - 48, height - 48, fill=False, stroke=True)

    # 3. Inner golden accent border
    c.setStrokeColor(gold_primary)
    c.setLineWidth(2)
    c.rect(32, 32, width - 64, height - 64, fill=False, stroke=True)

    # 4. Corner Accents (Triangles / Corner brackets)
    corner_size = 28
    corners = [
        (34, 34, 34 + corner_size, 34, 34, 34 + corner_size),  # Bottom-Left
        (width - 34, 34, width - 34 - corner_size, 34, width - 34, 34 + corner_size),  # Bottom-Right
        (34, height - 34, 34 + corner_size, height - 34, 34, height - 34 - corner_size),  # Top-Left
        (width - 34, height - 34, width - 34 - corner_size, height - 34, width - 34, height - 34 - corner_size),  # Top-Right
    ]
    c.setFillColor(gold_light)
    c.setStrokeColor(gold_primary)
    for x1, y1, x2, y2, x3, y3 in corners:
        p = c.beginPath()
        p.moveTo(x1, y1)
        p.lineTo(x2, y2)
        p.lineTo(x3, y3)
        p.close()
        c.drawPath(p, fill=True, stroke=True)

    # 5. Organization / Issuer Top Label
    c.setFont("Helvetica-Bold", 13)
    c.setFillColor(gold_primary)
    c.drawCentredString(width / 2, height - 75, issuer_name.upper())

    # Thin decorative line under Issuer
    c.setStrokeColor(gold_primary)
    c.setLineWidth(1)
    c.line(width / 2 - 120, height - 85, width / 2 + 120, height - 85)

    # 6. Main Certificate Title
    c.setFont("Helvetica-Bold", 32)
    c.setFillColor(navy_dark)
    c.drawCentredString(width / 2, height - 130, certificate_title.upper())

    # 7. Subtitle Presentation Text
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(gold_primary)
    c.drawCentredString(width / 2, height - 165, "THIS IS PROUDLY PRESENTED TO")

    # 8. Recipient Name (Featured prominently)
    c.setFont("Helvetica-Bold", 30)
    c.setFillColor(navy_dark)
    c.drawCentredString(width / 2, height - 220, recipient_name)

    # Underline accent for recipient name
    name_width = c.stringWidth(recipient_name, "Helvetica-Bold", 30)
    underline_w = max(name_width + 40, 260)
    c.setStrokeColor(gold_primary)
    c.setLineWidth(1.5)
    c.line(width / 2 - (underline_w / 2), height - 232, width / 2 + (underline_w / 2), height - 232)

    # 9. Description / Event Details
    c.setFont("Helvetica", 13)
    c.setFillColor(slate_gray)
    c.drawCentredString(width / 2, height - 270, "for outstanding participation and successfully completing")

    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(navy_dark)
    c.drawCentredString(width / 2, height - 305, f'"{event_name}"')

    # Optional custom attribute line (e.g. Grade, Track, Score)
    if custom_attributes:
        attr_strings = [f"{k.replace('_', ' ').title()}: {v}" for k, v in custom_attributes.items() if v]
        if attr_strings:
            c.setFont("Helvetica-Oblique", 11)
            c.setFillColor(slate_gray)
            c.drawCentredString(width / 2, height - 335, " • ".join(attr_strings))

    # 10. Center Decorative Seal / Badge
    seal_x = width / 2
    seal_y = 125
    c.setStrokeColor(gold_primary)
    c.setFillColor(gold_light)
    c.circle(seal_x, seal_y, 35, fill=True, stroke=True)

    c.setStrokeColor(navy_dark)
    c.setLineWidth(1)
    c.circle(seal_x, seal_y, 30, fill=False, stroke=True)

    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(navy_dark)
    c.drawCentredString(seal_x, seal_y + 8, "VERIFIED")
    c.drawCentredString(seal_x, seal_y - 4, "EXCELLENCE")
    c.setFont("Helvetica", 7)
    c.drawCentredString(seal_x, seal_y - 14, "★ ★ ★")

    # 11. Left Column: Date of Issue
    left_x = 160
    c.setStrokeColor(slate_gray)
    c.setLineWidth(1)
    c.line(left_x - 70, 115, left_x + 70, 115)

    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(navy_dark)
    c.drawCentredString(left_x, 125, issue_date)
    c.setFont("Helvetica", 9)
    c.setFillColor(slate_gray)
    c.drawCentredString(left_x, 100, "Date of Issuance")

    # 12. Right Column: Signature
    right_x = width - 160
    c.setStrokeColor(slate_gray)
    c.setLineWidth(1)
    c.line(right_x - 70, 115, right_x + 70, 115)

    # Stylized signature text
    c.setFont("Times-BoldItalic", 16)
    c.setFillColor(navy_dark)
    c.drawCentredString(right_x, 125, issuer_name)
    c.setFont("Helvetica", 9)
    c.setFillColor(slate_gray)
    c.drawCentredString(right_x, 100, "Authorized Signatory")

    # 13. Bottom Verification ID
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#94A3B8"))
    c.drawCentredString(width / 2, 45, f"Certificate ID: {certificate_id}  |  Official Digitally Generated Credential")

    c.showPage()
    c.save()
    return output_path
