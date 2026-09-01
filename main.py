import os
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import requests
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

app = FastAPI(title="Master Empire OS - Dedicated Quad-Key Pipeline", version="20.0")

# Dedicated Keys mapping for specific tasks
KEY_1 = os.getenv("GEMINI_API_KEY_1", "") # Chapters 1 & 2
KEY_2 = os.getenv("GEMINI_API_KEY_2", "") # Chapters 3 & 4
KEY_3 = os.getenv("GEMINI_API_KEY_3", "") # Chapters 5 & 6
KEY_4 = os.getenv("GEMINI_API_KEY_4", "") # Indexing & Summary

class BookRequest(BaseModel):
    title: str = "The Autonomous Digital Empire Blueprint"
    tier: str = "Enterprise Level"
    price: float = 29.99

def call_specific_gemini(api_key: str, prompt: str, fallback_text: str) -> str:
    """Calls a specific Gemini API key dedicated to a specific section."""
    if not api_key or not api_key.strip():
        return f"Fallback Content: {fallback_text}"
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].replace("*", "")
    except Exception as e:
        print(f"Dedicated Key API error: {e}")
    
    return f"Fallback Content: {fallback_text}"

@app.get("/", response_class=HTMLResponse)
def dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Master Empire OS — Dedicated Quad-Key Pipeline</title>
        <style>
            body { font-family: 'Segoe UI', Arial, sans-serif; background: #0b0f19; color: #ffffff; padding: 40px; }
            .card { background: #1f2937; padding: 35px; border-radius: 14px; max-width: 650px; margin: auto; box-shadow: 0 10px 30px rgba(0,0,0,0.6); border: 1px solid #374151; }
            h1 { color: #38bdf8; font-size: 26px; margin-bottom: 5px; }
            .status { color: #22c55e; font-weight: bold; }
            button { background: #38bdf8; color: #000; border: none; padding: 14px 22px; font-size: 16px; font-weight: bold; border-radius: 8px; cursor: pointer; margin-top: 20px; width: 100%; transition: 0.2s; }
            button:hover { background: #0ea5e9; }
            #output { margin-top: 20px; background: #111827; padding: 18px; border-radius: 8px; font-family: monospace; display: none; border-left: 4px solid #38bdf8; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>Master Empire OS &mdash; Pipeline Studio</h1>
            <p>System Status: <span class="status">ONLINE (v20.0 Dedicated 4-Key Pipeline)</span></p>
            <p>Key 1-2 (Ch 1-4), Key 3 (Ch 5-6), Key 4 (Index & Summary) active.</p>
            <button onclick="launchProduction()">Launch Dedicated AI Pipeline Production</button>
            <div id="output">Executing distributed multi-key pipeline...</div>
        </div>
        <script>
            async function launchProduction() {
                const out = document.getElementById('output');
                out.style.display = 'block';
                out.innerHTML = 'Distributing tasks across 4 dedicated Gemini keys... Please wait...';
                try {
                    let res = await fetch('/api/generate-book', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ title: "The Autonomous Digital Empire Blueprint", tier: "Enterprise Level", price: 29.99 })
                    });
                    let data = await res.json();
                    out.innerHTML = 'Success! Multi-Key Pipeline Masterpiece Generated: ' + data.filename + '<br><br><a href="/download/' + data.filename + '" style="color: #38bdf8; font-weight: bold; font-size: 16px;" target="_blank">📥 Download Distributed AI Book (PDF)</a>';
                } catch(e) {
                    out.innerHTML = 'Execution Error: ' + e;
                }
            }
        </script>
    </body>
    </html>
    """

def generate_pdf_with_pipeline(filename: str, title: str):
    pdf_path = filename
    doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('CoverTitle', parent=styles['Heading1'], fontSize=22, textColor=colors.HexColor('#1e3a8a'), spaceAfter=15, alignment=1)
    subtitle_style = ParagraphStyle('CoverSub', parent=styles['Normal'], fontSize=11, textColor=colors.HexColor('#475569'), spaceAfter=25, alignment=1)
    heading_style = ParagraphStyle('ChapterHeading', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#0f172a'), spaceBefore=15, spaceAfter=8)
    body_style = ParagraphStyle('BodyDark', parent=styles['BodyText'], fontSize=10, textColor=colors.HexColor('#334155'), spaceAfter=10, leading=14)

    story.append(Paragraph(title, title_style))
    story.append(Paragraph("Published by: Selza Media & Studio<br/>Powered by Master Empire OS — Dedicated 4-Key Pipeline", subtitle_style))
    story.append(Spacer(1, 15))

    # Task Division across the 4 Keys
    # Key 1 handles Chapters 1 & 2
    story.append(Paragraph("Chapter 1: Foundations of Autonomous Digital Empires", heading_style))
    c1 = call_specific_gemini(KEY_1, "Write a detailed 3-paragraph professional guide on building automated digital empires with zero marginal cost.", "Foundations rely on solid software architectures.")
    story.append(Paragraph(c1, body_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Chapter 2: Programmatic SEO & Global Scaling", heading_style))
    c2 = call_specific_gemini(KEY_1, "Write a detailed 3-paragraph technical guide on executing programmatic SEO and automated content distribution.", "Programmatic SEO drives organic traffic at scale.")
    story.append(Paragraph(c2, body_style))
    story.append(Spacer(1, 10))

    # Key 2 handles Chapters 3 & 4
    story.append(Paragraph("Chapter 3: Zero-Cost Cloud Infrastructure & Uptime", heading_style))
    c3 = call_specific_gemini(KEY_2, "Write a detailed 3-paragraph guide on deploying apps on free cloud platforms and maintaining 24/7 server uptime.", "Cloud architectures ensure 24/7 availability.")
    story.append(Paragraph(c3, body_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Chapter 4: AI Agents & Automated Sales Funnels", heading_style))
    c4 = call_specific_gemini(KEY_2, "Write a detailed 3-paragraph business guide on deploying AI agents for automated sales and customer conversion.", "AI agents automate customer interaction seamlessly.")
    story.append(Paragraph(c4, body_style))
    story.append(Spacer(1, 10))

    # Key 3 handles Chapters 5 & 6
    story.append(Paragraph("Chapter 5: Multi-Channel Monetization Frameworks", heading_style))
    c5 = call_specific_gemini(KEY_3, "Write a detailed 3-paragraph guide on diversifying revenue streams through digital products and memberships.", "Diversification secures robust enterprise revenue.")
    story.append(Paragraph(c5, body_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Chapter 6: Scaling Without Burnout", heading_style))
    c6 = call_specific_gemini(KEY_3, "Write a detailed 3-paragraph management guide on automating business operations completely to prevent solopreneur burnout.", "Automation protects founders from burnout.")
    story.append(Paragraph(c6, body_style))
    story.append(Spacer(1, 10))

    # Key 4 handles Indexing, Table of Contents & Master Summary
    story.append(Paragraph("Master Index & Strategic Summary", heading_style))
    c_index = call_specific_gemini(KEY_4, "Write a comprehensive master index and executive conclusion summarizing the entire autonomous digital empire blueprint.", "Summary: Complete automation yields absolute market dominance.")
    story.append(Paragraph(c_index, body_style))
    story.append(Spacer(1, 10))

    doc.build(story)

@app.post("/api/generate-book")
def generate_book(req: BookRequest, background_tasks: BackgroundTasks):
    filename = "autonomous_empire_blueprint.pdf"
    background_tasks.add_task(generate_pdf_with_pipeline, filename, req.title)
    return {"status": "success", "message": "Dedicated Multi-Key Pipeline triggered", "filename": filename}

@app.get("/download/{filename}")
def download_book(filename: str):
    if os.path.exists(filename):
        return FileResponse(filename, media_type='application/pdf', filename=filename)
    raise HTTPException(status_code=404, detail="File not found")

@app.get("/health")
def health_check():
    active_keys = sum([1 for k in [KEY_1, KEY_2, KEY_3, KEY_4] if k and k.strip()])
    return {"status": "healthy", "engine": "Dedicated Pipeline v20.0", "active_pipeline_keys": active_keys}