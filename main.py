import os
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = FastAPI(title="Master Empire OS", version="16.0")

# Quad-Key Gemini API Pool from Environment Variables
GEMINI_KEYS = [
    os.getenv("GEMINI_API_KEY_1", ""),
    os.getenv("GEMINI_API_KEY_2", ""),
    os.getenv("GEMINI_API_KEY_3", ""),
    os.getenv("GEMINI_API_KEY_4", "")
]

class BookRequest(BaseModel):
    title: str = "The Autonomous Digital Empire Blueprint"
    tier: str = "Enterprise Level"
    price: float = 29.99

@app.get("/", response_class=HTMLResponse)
def dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Master Empire OS — Command Center</title>
        <style>
            body { font-family: Arial, sans-serif; background: #0b0f19; color: #ffffff; padding: 40px; }
            .card { background: #1f2937; padding: 30px; border-radius: 12px; max-width: 600px; margin: auto; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
            h1 { color: #38bdf8; font-size: 24px; }
            .status { color: #22c55e; font-weight: bold; }
            button { background: #38bdf8; color: #000; border: none; padding: 12px 20px; font-size: 16px; font-weight: bold; border-radius: 6px; cursor: pointer; margin-top: 20px; width: 100%; }
            button:hover { background: #0ea5e9; }
            #output { margin-top: 20px; background: #111827; padding: 15px; border-radius: 6px; font-family: monospace; display: none; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>Master Empire OS &mdash; Live Engine</h1>
            <p>System Status: <span class="status">ONLINE (v16.0)</span></p>
            <p>Autonomous AI Book & Sales Engine is active.</p>
            <button onclick="launchProduction()">Launch Background Book Production</button>
            <div id="output">Initializing production cycle...</div>
        </div>
        <script>
            async function launchProduction() {
                const out = document.getElementById('output');
                out.style.display = 'block';
                out.innerHTML = 'Triggering background generation...';
                try {
                    let res = await fetch('/api/generate-book', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ title: "The Autonomous Digital Empire Blueprint", tier: "Enterprise Level", price: 29.99 })
                    });
                    let data = await res.json();
                    out.innerHTML = 'Success! Book Generated: ' + data.filename + '<br><a href="/download/' + data.filename + '" style="color: #38bdf8;" target="_blank">Download Generated Book PDF</a>';
                } catch(e) {
                    out.innerHTML = 'Error during execution: ' + e;
                }
            }
        </script>
    </body>
    </html>
    """

def generate_pdf_background(filename: str, title: str):
    pdf_path = filename
    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter
    
    c.setFont("Helvetica-Bold", 20)
    c.drawString(54, height - 72, title)
    
    c.setFont("Helvetica", 12)
    c.drawString(54, height - 120, "Published by: Selza Media & Studio")
    c.drawString(54, height - 140, "Powered by Master Empire OS Autonomous Engine")
    
    c.drawString(54, height - 190, "Chapter 1: The Vision of Autonomous Digital Empires")
    c.drawString(54, height - 210, "Top-tier tech frameworks demand 24/7 uptime, zero operational cost,")
    c.drawString(54, height - 230, "and absolute automated execution across global distribution channels.")
    
    c.save()

@app.post("/api/generate-book")
def generate_book(req: BookRequest, background_tasks: BackgroundTasks):
    filename = "autonomous_empire_blueprint.pdf"
    background_tasks.add_task(generate_pdf_background, filename, req.title)
    return {"status": "success", "message": "Book generation triggered in background", "filename": filename}

@app.get("/download/{filename}")
def download_book(filename: str):
    if os.path.exists(filename):
        return FileResponse(filename, media_type='application/pdf', filename=filename)
    raise HTTPException(status_code=404, detail="File not found")

@app.get("/health")
def health_check():
    return {"status": "healthy", "engine": "running", "active_keys": len([k for k in GEMINI_KEYS if k])}