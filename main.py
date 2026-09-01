import os
import json
import time
import logging
import threading
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import google.generativeai as genai
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Logging Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MasterEmpireOS")

app = FastAPI(
    title="Master Empire OS - Background Heavyweight eBook Engine",
    version="16.0.0",
    description="Professional Long-Form Autonomous Book Publisher with Background Task & Progress Tracking"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# QUAD-KEY ROTATION POOL
# ---------------------------------------------------------
API_KEYS_POOL = [
    os.getenv("GEMINI_API_KEY_1", ""),
    os.getenv("GEMINI_API_KEY_2", ""),
    os.getenv("GEMINI_API_KEY_3", ""),
    os.getenv("GEMINI_API_KEY_4", ""),
]

current_key_index = 0
generation_status = {
    "is_busy": False,
    "progress": "Idle. Ready to build your empire book.",
    "pdf_url": "",
    "details": None
}

def get_next_gemini_model():
    global current_key_index
    if not API_KEYS_POOL:
        return None
    for _ in range(len(API_KEYS_POOL)):
        key = API_KEYS_POOL[current_key_index]
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel("gemini-3.7-flash")
            return model
        except Exception:
            current_key_index = (current_key_index + 1) % len(API_KEYS_POOL)
    return None

def generate_with_safe_sleep(prompt: str):
    global current_key_index
    attempts = len(API_KEYS_POOL)
    for _ in range(attempts):
        model = get_next_gemini_model()
        if not model:
            break
        try:
            # Safe natural pacing to prevent 429 quota spikes
            time.sleep(8) 
            response = model.generate_content(prompt)
            text_resp = response.text.strip()
            
            if text_resp.startswith("```json"):
                text_resp = text_resp[7:]
            if text_resp.startswith("```"):
                text_resp = text_resp[3:]
            if text_resp.endswith("```"):
                text_resp = text_resp[:-3]
                
            return json.loads(text_resp.strip())
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "Quota exceeded" in err_str:
                logger.warning(f"Quota hit on Key Index [{current_key_index}]. Rotating & resting...")
                current_key_index = (current_key_index + 1) % len(API_KEYS_POOL)
                time.sleep(15) # Cool down period
                continue
            else:
                current_key_index = (current_key_index + 1) % len(API_KEYS_POOL)
                time.sleep(5)
                continue
    return None

class BookPublishRequest(BaseModel):
    title: str
    target_audience: str
    problem: str
    price: float
    level: str # Foundation, Enterprise, Industry-Grade

# ---------------------------------------------------------
# BACKGROUND TASK WORKER (Takes its own time safely)
# ---------------------------------------------------------
def background_book_creator(req: BookPublishRequest):
    global generation_status
    generation_status["is_busy"] = True
    generation_status["progress"] = f"Initializing {req.level} tier blueprint & structure..."
    generation_status["pdf_url"] = ""
    generation_status["details"] = None

    try:
        book_data = {}
        
        # Step 1: Title, Subtitle, TOC & Intro
        generation_status["progress"] = "Step 1/4: Researching and structuring Table of Contents & Introduction..."
        p1 = f"""You are an elite publishing architect. Create a {req.level}-grade book blueprint for '{req.title}' (Audience: {req.target_audience}, Problem: {req.problem}). Return strictly valid JSON with:
        1. "hook_subtitle": A powerful subtitle.
        2. "table_of_contents": An array of 5 detailed chapter titles.
        3. "introduction": A deep, thorough 4-paragraph introduction."""
        res1 = generate_with_safe_sleep(p1)
        if res1: book_data.update(res1)
        
        # Step 2: Chapters 1 & 2
        generation_status["progress"] = "Step 2/4: Writing comprehensive Chapter 1 & Chapter 2..."
        p2 = f"""Write detailed, highly valuable, multi-paragraph professional content for Chapter 1 and Chapter 2 of '{req.title}' tailored for {req.level} level. Return strictly valid JSON with keys "chapter_1_content" and "chapter_2_content"."""
        res2 = generate_with_safe_sleep(p2)
        if res2: book_data.update(res2)
        
        # Step 3: Chapters 3 & 4
        generation_status["progress"] = "Step 3/4: Writing deep execution frameworks for Chapter 3 & Chapter 4..."
        p3 = f"""Write detailed, highly valuable, multi-paragraph professional content for Chapter 3 and Chapter 4 of '{req.title}'. Return strictly valid JSON with keys "chapter_3_content" and "chapter_4_content"."""
        res3 = generate_with_safe_sleep(p3)
        if res3: book_data.update(res3)
        
        # Step 4: Chapter 5, Conclusion & Sales Hook
        generation_status["progress"] = "Step 4/4: Finalizing Chapter 5, Conclusion & High-Conversion Sales Hook..."
        p4 = f"""Write detailed content for Chapter 5 and Conclusion of '{req.title}', plus a high-converting sales pitch for ${req.price}. Return strictly valid JSON with keys "chapter_5_content", "conclusion_content", and "marketing_hook"."""
        res4 = generate_with_safe_sleep(p4)
        if res4: book_data.update(res4)

        # Fallbacks if needed
        if "hook_subtitle" not in book_data: book_data["hook_subtitle"] = f"A Master Empire {req.level} Publication"
        if "table_of_contents" not in book_data: book_data["table_of_contents"] = ["Chapter 1", "Chapter 2", "Chapter 3", "Chapter 4", "Chapter 5"]
        if "introduction" not in book_data: book_data["introduction"] = "Comprehensive introduction..."
        if "chapter_1_content" not in book_data: book_data["chapter_1_content"] = "Chapter 1 content."
        if "chapter_2_content" not in book_data: book_data["chapter_2_content"] = "Chapter 2 content."
        if "chapter_3_content" not in book_data: book_data["chapter_3_content"] = "Chapter 3 content."
        if "chapter_4_content" not in book_data: book_data["chapter_4_content"] = "Chapter 4 content."
        if "chapter_5_content" not in book_data: book_data["chapter_5_content"] = "Chapter 5 content."
        if "conclusion_content" not in book_data: book_data["conclusion_content"] = "Conclusion and takeaways."
        if "marketing_hook" not in book_data: book_data["marketing_hook"] = f"Get this {req.level} playbook for ${req.price}!"

        # PDF Compilation
        generation_status["progress"] = "Compiling professional ReportLab PDF layout..."
        safe_filename = "".join(c for c in req.title if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_') + f"_{req.level}.pdf"
        pdf_path = os.path.join(os.getcwd(), safe_filename)
        
        doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle('BookTitle', parent=styles['Heading1'], fontSize=22, leading=26, textColor=colors.HexColor("#0284c7"), alignment=1, spaceAfter=10)
        subtitle_style = ParagraphStyle('BookSubtitle', parent=styles['Normal'], fontSize=13, leading=17, textColor=colors.HexColor("#4b5563"), alignment=1, spaceAfter=20)
        meta_style = ParagraphStyle('BookMeta', parent=styles['Normal'], fontSize=11, leading=15, textColor=colors.HexColor("#374151"), alignment=1, spaceAfter=25)
        heading_style = ParagraphStyle('ChapterHeading', parent=styles['Heading2'], fontSize=15, leading=19, textColor=colors.HexColor("#111827"), spaceBefore=18, spaceAfter=10)
        body_style = ParagraphStyle('BookBody', parent=styles['Normal'], fontSize=10.5, leading=15, textColor=colors.HexColor("#1f2937"), spaceAfter=12)
        
        story = []
        story.append(Spacer(1, 30))
        story.append(Paragraph(req.title, title_style))
        story.append(Paragraph(book_data.get("hook_subtitle", ""), subtitle_style))
        story.append(Paragraph(f"<b>Level:</b> {req.level} Tier | <b>Target Audience:</b> {req.target_audience} | <b>Price:</b> ${req.price}", meta_style))
        story.append(Spacer(1, 15))
        
        story.append(Paragraph("Table of Contents", heading_style))
        toc = book_data.get("table_of_contents", [])
        if isinstance(toc, list):
            for idx, item in enumerate(toc, 1):
                story.append(Paragraph(f"<b>Chapter {idx}:</b> {item}", body_style))
        else:
            story.append(Paragraph(str(toc), body_style))
        story.append(Spacer(1, 15))
        story.append(PageBreak())
        
        story.append(Paragraph("Introduction", heading_style))
        story.append(Paragraph(book_data.get("introduction", ""), body_style))
        story.append(Spacer(1, 15))
        story.append(PageBreak())
        
        chapters = [
            ("Chapter 1", book_data.get("chapter_1_content", "")),
            ("Chapter 2", book_data.get("chapter_2_content", "")),
            ("Chapter 3", book_data.get("chapter_3_content", "")),
            ("Chapter 4", book_data.get("chapter_4_content", "")),
            ("Chapter 5", book_data.get("chapter_5_content", ""))
        ]
        
        for ch_title, ch_text in chapters:
            story.append(Paragraph(ch_title, heading_style))
            story.append(Paragraph(ch_text, body_style))
            story.append(Spacer(1, 15))
            story.append(PageBreak())
            
        story.append(Paragraph("Conclusion", heading_style))
        story.append(Paragraph(book_data.get("conclusion_content", ""), body_style))
        story.append(Spacer(1, 15))
        
        story.append(Paragraph("Exclusive Publisher Note & Sales Hook", heading_style))
        story.append(Paragraph(book_data.get("marketing_hook", ""), body_style))
        
        doc.build(story)
        
        generation_status["is_busy"] = False
        generation_status["progress"] = "✨ Success! Book generation complete."
        generation_status["pdf_url"] = f"/api/download-pdf/{safe_filename}"
        generation_status["details"] = book_data
        logger.info("Background book generation completed successfully!")

    except Exception as e:
        generation_status["is_busy"] = False
        generation_status["progress"] = f"Error during generation: {str(e)}"
        logger.error(f"Background task failed: {e}")

# ---------------------------------------------------------
# MASTER EMPIRE OS - STUDIO INTERFACE WITH LIVE STATUS
# ---------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def serve_master_empire_os():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Master Empire OS - Commercial SaaS Edition</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0b0f19; color: #f8fafc; margin: 0; padding: 20px; }
            .container { max-width: 1050px; margin: auto; background: #111827; border: 2px solid #374151; border-radius: 16px; padding: 30px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
            h1 { color: #38bdf8; text-align: center; margin-bottom: 5px; }
            p.subtitle { text-align: center; color: #94a3b8; margin-bottom: 30px; }
            .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
            @media(max-width: 768px) { .grid { grid-template-columns: 1fr; } }
            .card { background: #1f2937; border: 1px solid #4b5563; border-radius: 12px; padding: 20px; margin-bottom: 20px; }
            .status-ok { color: #4ade80; font-weight: bold; }
            .status-busy { color: #facc15; font-weight: bold; animation: pulse 1.5s infinite; }
            @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
            input, textarea, select { width: 100%; padding: 10px; margin: 8px 0 15px 0; background: #030712; border: 1px solid #374151; color: white; border-radius: 6px; box-sizing: border-box; }
            button { background: #0284c7; color: white; border: none; padding: 12px 24px; font-size: 16px; border-radius: 8px; cursor: pointer; font-weight: bold; width: 100%; transition: background 0.2s; }
            button:hover { background: #0369a1; }
            button:disabled { background: #4b5563; cursor: not-allowed; }
            .btn-download { background: #16a34a; margin-top: 15px; display: none; text-align: center; text-decoration: none; padding: 12px; border-radius: 8px; color: white; font-weight: bold; }
            .btn-download:hover { background: #15803d; }
            .reader-box { background: #030712; border: 1px solid #374151; border-radius: 8px; padding: 20px; height: 500px; overflow-y: auto; color: #e2e8f0; line-height: 1.6; }
            .reader-box h2 { color: #38bdf8; margin-top: 0; }
            .reader-box h4 { color: #facc15; border-bottom: 1px solid #1e293b; padding-bottom: 5px; }
            .notification { background: #065f46; color: #d1fae5; padding: 12px; border-radius: 8px; margin-bottom: 15px; display: none; text-align: center; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Master Empire OS</h1>
            <p class="subtitle">Commercial SaaS Heavyweight eBook Publishing Factory</p>
            
            <div id="notifyBox" class="notification">🎉 Notification: Your Masterpiece Book is 100% Completed! Go and Check.</div>

            <div class="card">
                <h3>🟢 System Status</h3>
                <p>Engine: <span class="status-ok">ONLINE (v16.0 SaaS Background Engine)</span> | Current Activity: <span id="statusText" class="status-ok">Idle</span></p>
            </div>

            <div class="grid">
                <div class="card">
                    <h3>📖 Tier & Book Publishing Control</h3>
                    <label>Book Title / Topic:</label>
                    <input type="text" id="bookTitle" value="The Autonomous Digital Empire Blueprint">
                    
                    <label>Publishing Tier & Quality Level:</label>
                    <select id="bookLevel">
                        <option value="Foundation">Foundation Level ($19.99 - Core Frameworks)</option>
                        <option value="Enterprise" selected>Enterprise Level ($29.99 - Advanced Systems)</option>
                        <option value="Industry-Grade">Industry-Grade Level ($49.99 - Elite Mastery Playbook)</option>
                    </select>

                    <label>Target Audience:</label>
                    <input type="text" id="bookAudience" value="Solopreneurs & Creators">
                    
                    <label>Core Problem Solved:</label>
                    <textarea id="bookProblem" rows="2">How to build automated income streams without burnout</textarea>
                    
                    <label>Selling Price ($):</label>
                    <input type="number" id="bookPrice" value="29.99">
                    
                    <button id="genBtn" onclick="startHeavyweightGeneration()">🚀 Launch Background Book Production</button>
                    
                    <a id="downloadBtn" class="btn-download" href="#" target="_blank">📥 Download Completed Tier PDF Book</a>
                </div>

                <div class="card">
                    <h3>👁️ Live Progress & Reader Studio</h3>
                    <div id="bookReader" class="reader-box">
                        <p style="color: #94a3b8; text-align: center; margin-top: 150px;">Click 'Launch Production' and take your time. Background worker will safely build your book with live status updates...</p>
                    </div>
                </div>
            </div>
        </div>

        <script>
            let pollInterval = null;

            async function startHeavyweightGeneration() {
                const title = document.getElementById('bookTitle').value;
                const level = document.getElementById('bookLevel').value;
                const audience = document.getElementById('bookAudience').value;
                const problem = document.getElementById('bookProblem').value;
                const price = parseFloat(document.getElementById('bookPrice').value);
                
                const genBtn = document.getElementById('genBtn');
                const downloadBtn = document.getElementById('downloadBtn');
                const notifyBox = document.getElementById('notifyBox');
                
                genBtn.disabled = true;
                genBtn.innerText = "⏳ Production in Progress (Safe Background Mode)...";
                downloadBtn.style.display = "none";
                notifyBox.style.display = "none";
                
                try {
                    const response = await fetch('/api/publish-book-async', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ title, level, target_audience: audience, problem, price })
                    });
                    const data = await response.json();
                    
                    if(response.ok) {
                        // Start polling status
                        pollInterval = setInterval(checkStatus, 3000);
                    } else {
                        alert("Error: " + data.detail);
                        genBtn.disabled = false;
                        genBtn.innerText = "🚀 Launch Background Book Production";
                    }
                } catch (err) {
                    alert("Network Error: " + err.message);
                    genBtn.disabled = false;
                    genBtn.innerText = "🚀 Launch Background Book Production";
                }
            }

            async function checkStatus() {
                try {
                    const res = await fetch('/api/status-check');
                    const status = await res.json();
                    
                    const statusText = document.getElementById('statusText');
                    const reader = document.getElementById('bookReader');
                    const genBtn = document.getElementById('genBtn');
                    const downloadBtn = document.getElementById('downloadBtn');
                    const notifyBox = document.getElementById('notifyBox');
                    
                    statusText.innerText = status.progress;
                    statusText.className = status.is_busy ? "status-busy" : "status-ok";
                    
                    if(status.is_busy) {
                        reader.innerHTML = `<p style='color: #38bdf8; text-align: center; margin-top: 150px;'>⚙️ ${status.progress}<br><br><small style='color: #94a3b8;'>You can safely wait. The system is pacing itself to ensure zero quota drops.</small></p>`;
                    } else {
                        clearInterval(pollInterval);
                        genBtn.disabled = false;
                        genBtn.innerText = "🚀 Launch Background Book Production";
                        
                        if(status.pdf_url) {
                            const book = status.details;
                            let tocHtml = "";
                            if(book && book.table_of_contents) {
                                book.table_of_contents.forEach(item => tocHtml += `<li>${item}</li>`);
                            }
                            
                            reader.innerHTML = `
                                <h2 style="color: #4ade80;">🎉 Book Production Completed!</h2>
                                <p style="color: #38bdf8; font-style: italic;">${book ? book.hook_subtitle : ''}</p>
                                <hr style="border-color: #374151;">
                                <h4>📚 Table of Contents</h4>
                                <ul>${tocHtml}</ul>
                                <h4>🎯 Sales Pitch & Hook</h4>
                                <p style="color: #facc15;">${book ? book.marketing_hook : ''}</p>
                            `;
                            
                            downloadBtn.href = status.pdf_url;
                            downloadBtn.style.display = "block";
                            notifyBox.style.display = "block";
                        }
                    }
                } catch(e) {
                    console.log("Polling error:", e);
                }
            }
        </script>
    </body>
    </html>
    """

@app.post("/api/publish-book-async")
def publish_book_async(req: BookPublishRequest, background_tasks: BackgroundTasks):
    global generation_status
    if generation_status["is_busy"]:
        raise HTTPException(status_code=400, detail="A book is already being produced. Please wait until current production finishes.")
        
    background_tasks.add_task(background_book_creator, req)
    return {"status": "started", "message": "Background book production started successfully."}

@app.get("/api/status-check")
def get_status_check():
    return generation_status

@app.get("/api/download-pdf/{filename}")
def download_pdf_file(filename: str):
    file_path = os.path.join(os.getcwd(), filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type='application/pdf', filename=filename)
    raise HTTPException(status_code=404, detail="PDF file not found.")