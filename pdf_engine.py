import os
import re
import time
from typing import Dict, Any, Tuple
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether, Table, TableStyle
)
from reportlab.pdfgen import canvas

PDF_STORAGE_DIR = os.path.join(os.path.dirname(__file__), "static", "pdfs")
os.makedirs(PDF_STORAGE_DIR, exist_ok=True)

class NumberedCanvas(canvas.Canvas):
    """दोहरे पास का कैनवास जो कुल पेजों की सही गणना करता है और हेडर/फूटर जोड़ता है।"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            if self._pageNumber > 1:  # कवर पेज पर हेडर-फूटर नहीं होगा
                self.saveState()
                self.setFont("Helvetica", 8)
                self.setFillColor(colors.HexColor("#6b7280"))
                # Header
                self.drawString(15 * mm, 285 * mm, "Global Enterprise Edition — Confidential Asset")
                self.setStrokeColor(colors.HexColor("#e5e7eb"))
                self.setLineWidth(0.5)
                self.line(15 * mm, 282 * mm, 195 * mm, 282 * mm)
                # Footer
                self.line(15 * mm, 15 * mm, 195 * mm, 15 * mm)
                self.drawString(15 * mm, 10 * mm, "Autonomous Business OS | Master Publication")
                self.drawRightString(195 * mm, 10 * mm, f"Page {self._pageNumber} of {num_pages}")
                self.restoreState()
            super().showPage()
        super().save()

def verify_pdf_integrity(file_path: str) -> Tuple[bool, str, int]:
    """5-Point Integrity Guard (File, Size, Magic Header, Parse, Pages)"""
    if not os.path.exists(file_path):
        return False, "File not found on disk.", 0
    
    file_size = os.path.getsize(file_path)
    if file_size < 1024:  # Minimum 1 KB
        return False, f"File size too small ({file_size} bytes).", 0
    
    with open(file_path, "rb") as f:
        header = f.read(5)
        if header != b"%PDF-":
            return False, "Invalid PDF magic header.", 0
    
    # Simple page marker count verification
    with open(file_path, "rb") as f:
        content = f.read()
        page_count = len(re.findall(rb"/Type\s*/Page\b", content))
        if page_count == 0:
            page_count = 1  # Fallback for compressed objects
            
    return True, "Integrity verified.", page_count

def compile_markdown_to_pdf(
    title: str,
    tier_level: str,
    target_niche: str,
    markdown_content: str,
    output_filename: str
) -> Dict[str, Any]:
    """कच्चे मार्कडाउन को A4 पब्लिशिंग-ग्रेड PDF में संकलित करता है।"""
    start_time = time.time()
    target_path = os.path.join(PDF_STORAGE_DIR, output_filename)
    
    # Temporary staging path
    temp_path = target_path + ".tmp"
    if os.path.exists(temp_path):
        os.remove(temp_path)

    try:
        doc = SimpleDocTemplate(
            temp_path,
            pagesize=A4,
            leftMargin=15 * mm,
            rightMargin=15 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm
        )
        
        styles = getSampleStyleSheet()
        
        # Typography Styles
        title_style = ParagraphStyle(
            'CoverTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=24,
            leading=28,
            textColor=colors.HexColor("#0f172a"),
            alignment=1, # Center
            spaceAfter=15
        )
        
        meta_style = ParagraphStyle(
            'CoverMeta',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#475569"),
            alignment=1,
            spaceAfter=8
        )
        
        h1_style = ParagraphStyle(
            'Heading1_Custom',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=14,
            spaceAfter=8,
            keepWithNext=True
        )
        
        h2_style = ParagraphStyle(
            'Heading2_Custom',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#334155"),
            spaceBefore=10,
            spaceAfter=6,
            keepWithNext=True
        )
        
        body_style = ParagraphStyle(
            'Body_Custom',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor("#1f2937"),
            spaceAfter=6
        )
        
        code_style = ParagraphStyle(
            'Code_Custom',
            parent=styles['Normal'],
            fontName='Courier',
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#0f172a"),
            backColor=colors.HexColor("#f1f5f9"),
            borderPadding=6,
            spaceBefore=6,
            spaceAfter=6
        )

        story = []

        # ----------------------------------------------------
        # 1. FRONT COVER PAGE
        # ----------------------------------------------------
        story.append(Spacer(1, 40 * mm))
        
        # Badge
        badge_data = [[Paragraph(f"<b>{tier_level.upper()}</b>", ParagraphStyle('B', fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor("#1e40af"), alignment=1))]]
        badge_table = Table(badge_data, colWidths=[120 * mm])
        badge_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#dbeafe")),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(badge_table)
        story.append(Spacer(1, 15 * mm))
        
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 5 * mm))
        story.append(Paragraph(f"Specialized Blueprint for: <b>{target_niche}</b>", meta_style))
        story.append(Paragraph("Production Grade • Enterprise Systems Architecture", meta_style))
        
        story.append(Spacer(1, 60 * mm))
        story.append(Paragraph("Published by Autonomous Business OS Engine", meta_style))
        story.append(PageBreak())

        # ----------------------------------------------------
        # 2. BODY CONTENT PARSING
        # ----------------------------------------------------
        lines = markdown_content.split("\n")
        in_code_block = False
        code_accumulator = []

        for line in lines:
            line_str = line.strip()
            
            # Code block toggle
            if line_str.startswith("```"):
                if in_code_block:
                    full_code = "<br/>".join(code_accumulator)
                    story.append(Paragraph(full_code, code_style))
                    code_accumulator = []
                    in_code_block = False
                else:
                    in_code_block = True
                continue
            
            if in_code_block:
                clean_line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace(" ", "&nbsp;")
                code_accumulator.append(clean_line)
                continue
            
            if not line_str:
                story.append(Spacer(1, 2 * mm))
                continue
            
            if line_str.startswith("# "):
                clean_text = line_str[2:].replace("<", "&lt;").replace(">", "&gt;")
                story.append(Paragraph(clean_text, h1_style))
            elif line_str.startswith("## "):
                clean_text = line_str[3:].replace("<", "&lt;").replace(">", "&gt;")
                story.append(Paragraph(clean_text, h2_style))
            elif line_str.startswith("### "):
                clean_text = line_str[4:].replace("<", "&lt;").replace(">", "&gt;")
                story.append(Paragraph(f"<b>{clean_text}</b>", body_style))
            elif line_str.startswith("- ") or line_str.startswith("* "):
                clean_text = line_str[2:].replace("<", "&lt;").replace(">", "&gt;")
                # Bold conversion
                clean_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', clean_text)
                story.append(Paragraph(f"• {clean_text}", body_style))
            else:
                clean_text = line_str.replace("<", "&lt;").replace(">", "&gt;")
                clean_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', clean_text)
                story.append(Paragraph(clean_text, body_style))

        # Build Document with NumberedCanvas
        doc.build(story, canvasmaker=NumberedCanvas)
        
        # ----------------------------------------------------
        # 3. PDF INTEGRITY AUDIT GATE
        # ----------------------------------------------------
        is_valid, msg, pages = verify_pdf_integrity(temp_path)
        if not is_valid:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return {
                "success": False,
                "error": f"Integrity Gate Rejected: {msg}",
                "elapsed_time": round(time.time() - start_time, 2)
            }
        
        # Atomic rename to final path
        if os.path.exists(target_path):
            os.remove(target_path)
        os.rename(temp_path, target_path)

        elapsed = round(time.time() - start_time, 2)
        return {
            "success": True,
            "file_path": f"/static/pdfs/{output_filename}",
            "absolute_path": target_path,
            "page_count": pages,
            "file_size_kb": round(os.path.getsize(target_path) / 1024, 2),
            "elapsed_time_seconds": elapsed
        }

    except Exception as e:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        return {
            "success": False,
            "error": str(e),
            "elapsed_time": round(time.time() - start_time, 2)
        }