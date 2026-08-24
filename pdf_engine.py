import os
import hashlib
from typing import List, Dict, Any
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak

PDF_STORAGE_DIR = os.path.join(os.getcwd(), "static", "pdfs")
os.makedirs(PDF_STORAGE_DIR, exist_ok=True)

class NumberedCanvas:
    """Helper for dynamic page numbering and header/footers."""
    pass

def compile_complete_book_pdf(
    book_title: str,
    target_niche: str,
    chapters: List[Dict[str, Any]],
    output_path: str
) -> str:
    """Headless PDF compilation in local storage with cover, TOC, chapters, and appendix."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Title'],
        fontSize=28,
        leading=34,
        textColor=colors.HexColor('#0f172a'),
        alignment=1,
        spaceAfter=20
    )
    niche_style = ParagraphStyle(
        'CoverNiche',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#2563eb'),
        alignment=1,
        spaceAfter=40
    )
    heading_style = ParagraphStyle(
        'ChapHeading',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#1e293b'),
        spaceBefore=20,
        spaceAfter=12
    )
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontSize=10,
        leading=15,
        textColor=colors.HexColor('#334155'),
        spaceAfter=10
    )
    
    story = []
    
    # Cover Page
    story.append(Spacer(1, 150))
    story.append(Paragraph(book_title, title_style))
    story.append(Paragraph(f"Category: {target_niche.upper()} • Enterprise Blueprint Edition", niche_style))
    story.append(Spacer(1, 150))
    story.append(Paragraph("Autonomous Publishing OS • Cryptographically Verified Asset", body_style))
    story.append(PageBreak())
    
    # Table of Contents
    story.append(Paragraph("Table of Contents", heading_style))
    story.append(Spacer(1, 10))
    for chap in chapters:
        story.append(Paragraph(f"Chapter {chap['chapter_num']}: {chap['title']}", body_style))
    story.append(PageBreak())
    
    # Chapters
    for chap in chapters:
        story.append(Paragraph(f"Chapter {chap['chapter_num']}: {chap['title']}", heading_style))
        for line in chap['content'].split('\n\n'):
            if line.strip():
                story.append(Paragraph(line.replace('\n', '<br/>'), body_style))
        story.append(PageBreak())
        
    # Appendix & Legal Disclaimer
    story.append(Paragraph("Appendix & Legal Disclaimer", heading_style))
    story.append(Paragraph(
        "This digital technical asset is generated and distributed under autonomous enterprise protocols. "
        "All rights reserved. Unauthorized reproduction, distribution, or reverse-engineering is prohibited.",
        body_style
    ))
    
    doc.build(story)
    
    # Validate PDF signature
    with open(output_path, "rb") as f:
        sig = f.read(5)
        if not sig.startswith(b"%PDF-"):
            raise ValueError("Generated file failed valid %PDF byte signature check.")
            
    # Compute SHA-256
    hasher = hashlib.sha256()
    with open(output_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
            
    return hasher.hexdigest()