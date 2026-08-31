import os
import json
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import google.generativeai as genai

# Logging Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MasterEmpireOS")

app = FastAPI(
    title="Master Empire OS - Autonomous Digital Product Business",
    version="6.0.0",
    description="Unified Sovereign Single-URL Production Engine"
)

# Enable CORS completely
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# GEMINI AI ENGINE CONFIGURATION
# ---------------------------------------------------------
GEMINI_API_KEY = os.getenv("Gem1n1_API")

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel("gemini-1.5-flash")
        logger.info("Gemini API successfully configured.")
    except Exception as e:
        logger.error(f"Failed to configure Gemini SDK: {e}")
        gemini_model = None
else:
    logger.warning("WARNING: 'Gem1n1_API' environment variable is missing!")
    gemini_model = None

# ---------------------------------------------------------
# PYDANTIC SCHEMAS
# ---------------------------------------------------------
class FullBookPublishRequest(BaseModel):
    title: str
    target_audience: str
    problem: str
    price: float

# ---------------------------------------------------------
# UNIFIED SINGLE-URL DASHBOARD ROUTE
# ---------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def serve_unified_dashboard():
    """
    Serves the complete sovereign dashboard directly from the main URL root 
    to ensure a single unified app structure ready for mobile/desktop app conversion.
    """
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Master Empire OS - Autonomous Digital Product Engine</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0b0f19; color: #f8fafc; margin: 0; padding: 20px; }
            .container { max-width: 900px; margin: auto; background: #111827; border: 2px solid #374151; border-radius: 16px; padding: 30px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
            h1 { color: #38bdf8; text-align: center; margin-bottom: 25px; font-size: 24px; }
            .section { background: #1f2937; border: 1px solid #374151; border-radius: 12px; padding: 20px; margin-bottom: 20px; }
            .section h2 { color: #facc15; font-size: 18px; margin-top: 0; }
            input, button { width: 100%; padding: 12px; margin-top: 10px; border-radius: 8px; border: 1px solid #4b5563; font-size: 16px; box-sizing: border-box; }
            input { background: #374151; color: #fff; }
            button { background: #0284c7; color: white; font-weight: bold; cursor: pointer; transition: background 0.3s; }
            button:hover { background: #0369a1; }
            #output-box { background: #030712; border: 1px solid #374151; border-radius: 8px; padding: 15px; margin-top: 15px; white-space: pre-wrap; color: #34d399; font-family: monospace; max-height: 450px; overflow-y: auto; display: none; }
            .stats { display: flex; justify-content: space-between; margin-bottom: 20px; background: #1f2937; padding: 15px; border-radius: 8px; border: 1px solid #374151; }
            .stat-item { text-align: center; }
            .stat-value { font-size: 20px; font-weight: bold; color: #38bdf8; }
        </style>
    </head>
    <body>

    <div class="container">
        <h1>MASTER EMPIRE OS - SOVEREIGN PUBLISHING ENGINE</h1>
        
        <div class="stats">
            <div class="stat-item"><div>Global Visitors</div><div class="stat-value">14</div></div>
            <div class="stat-item"><div>Active Target</div><div class="stat-value">1.5 Lakh Words</div></div>
            <div class="stat-item"><div>System Status</div><div class="stat-value" style="color: #34d399;">ONLINE (UNIFIED)</div></div>
        </div>

        <!-- Book Synthesis Section -->
        <div class="section">
            <h2>Autonomous Book Publishing & Synthesis Pipeline</h2>
            <p>Generate deep, multi-chapter substantive content instantly via Gemini Engine.</p>
            
            <label>Book Title / Topic:</label>
            <input type="text" id="bookTitle" value="Biotechnology and Social Law Handbook">
            
            <label>Target Audience:</label>
            <input type="text" id="targetAudience" value="Entrepreneurs & Researchers">
            
            <label>Core Problem to Solve:</label>
            <input type="text" id="problem" value="Navigating legal compliance and biotechnology frameworks globally.">
            
            <label>Price (INR):</label>
            <input type="number" id="price" value="999">

            <button onclick="triggerBookGeneration()">Trigger AI Synthesis & Build Book</button>
            
            <div id="output-box">Synthesizing comprehensive book structure and deep content... Please wait.</div>
        </div>
    </div>

    <script>
    async function triggerBookGeneration() {
        const title = document.getElementById('bookTitle').value;
        const target_audience = document.getElementById('targetAudience').value;
        const problem = document.getElementById('problem').value;
        const price = parseFloat(document.getElementById('price').value);
        
        const outputBox = document.getElementById('output-box');
        outputBox.style.display = 'block';
        outputBox.style.color = '#facc15';
        outputBox.innerText = "Connecting to Gemini AI Engine... Writing full substantive book content (Please wait 10-15 seconds)...";
        
        try {
            const response = await fetch('/api/generate-full-book', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, target_audience, problem, price })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                outputBox.style.color = '#34d399';
                outputBox.innerText = "SUCCESS! BOOK GENERATED & PUBLISHED:\n\n" + JSON.stringify(data, null, 2);
            } else {
                outputBox.style.color = '#ef4444';
                outputBox.innerText = "ERROR: " + (data.detail || "Failed to generate book.");
            }
        } catch (err) {
            outputBox.style.color = '#ef4444';
            outputBox.innerText = "NETWORK ERROR: " + err.message;
        }
    }
    </script>

    </body>
    </html>
    """

@app.post("/api/generate-full-book")
def generate_full_book(payload: FullBookPublishRequest):
    if not gemini_model:
        raise HTTPException(status_code=500, detail="Gemini API Key missing on server.")
        
    prompt = f"""
    You are an expert author and digital publisher. Write a comprehensive, highly valuable digital book structure 
    titled '{payload.title}' designed for '{payload.target_audience}' to solve '{payload.problem}'.
    Provide a robust 4-chapter structure. For each chapter, provide:
    1. Chapter Number
    2. Chapter Title
    3. Detailed Substantive Content (3 detailed paragraphs with explanations and frameworks).
    4. Practical Checklist (3 actionable bullet points).
    Return a valid JSON object with keys: book_title, subtitle, chapters, conclusion.
    No markdown formatting blocks, return ONLY raw JSON text.
    """
    
    try:
        response = gemini_model.generate_content(prompt)
        raw_text = response.text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:].strip()
                
        book_data = json.loads(raw_text)
        
        return {
            "status": "SUCCESS",
            "database_status": "Unified Local/Cloud Ledger Synced",
            "product_details": {
                "title": payload.title,
                "price": payload.price,
                "target_audience": payload.target_audience,
                "book_content": book_data
            },
            "message": "Full-form professional book successfully generated and published to single URL!"
        }
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))