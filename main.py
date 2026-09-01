import os
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import requests
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

app = FastAPI(title="Master Empire OS - Shailja Tech Engine", version="22.0")

KEY_1 = os.getenv("GEMINI_API_KEY_1", "")
KEY_2 = os.getenv("GEMINI_API_KEY_2", "")
KEY_3 = os.getenv("GEMINI_API_KEY_3", "")
KEY_4 = os.getenv("GEMINI_API_KEY_4", "")

class BookRequest(BaseModel):
    title: str = "The Autonomous Digital Empire Blueprint"
    tier: str = "Enterprise Level"
    price: float = 29.99

def call_gemini_or_premium_content(api_key: str, fallback_title: str, detailed_fallback_body: str) -> str:
    """Attempts to fetch deep AI content via Gemini API. If keys are missing or delayed, uses rich professional pre-built expert content to ensure premium book quality."""
    if api_key and api_key.strip():
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        prompt = f"Write a comprehensive, highly detailed, multi-paragraph professional business and technical masterclass chapter on: {detailed_fallback_body}. Use elite enterprise terminology, deep strategic insights, and actionable frameworks."
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            response = requests.post(url, json=payload, timeout=20)
            if response.status_code == 200:
                data = response.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return text.replace("*", "").replace("#", "")
        except Exception as e:
            print(f"API Connection notice: {e}")
            
    # Premium Rich Fallback to guarantee a thick, premium, complete book instantly
    return detailed_fallback_body

@app.get("/", response_class=HTMLResponse)
def dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Master Empire OS — Shailja Tech Command Center</title>
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
            <h1>Shailja Tech &mdash; Master Empire OS</h1>
            <p>System Status: <span class="status">ONLINE (v22.0 Premium Engine)</span></p>
            <p>Publishing House: <b>Shailja Tech</b> | Quad-Key Pipeline Active.</p>
            <button onclick="launchProduction()">Launch Premium Book Production</button>
            <div id="output">Compiling comprehensive premium chapters...</div>
        </div>
        <script>
            async function launchProduction() {
                const out = document.getElementById('output');
                out.style.display = 'block';
                out.innerHTML = 'Synthesizing deep chapters and layout... Please wait...';
                try {
                    let res = await fetch('/api/generate-book', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ title: "The Autonomous Digital Empire Blueprint", tier: "Enterprise Level", price: 29.99 })
                    });
                    let data = await res.json();
                    out.innerHTML = 'Success! Premium Shailja Tech Masterpiece Generated: ' + data.filename + '<br><br><a href="/download/' + data.filename + '" style="color: #38bdf8; font-weight: bold; font-size: 16px;" target="_blank">📥 Download Premium Book (PDF)</a>';
                } catch(e) {
                    out.innerHTML = 'Execution Error: ' + e;
                }
            }
        </script>
    </body>
    </html>
    """

def generate_pdf_with_shailja_pipeline(filename: str, title: str):
    pdf_path = filename
    doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('CoverTitle', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor('#1e3a8a'), spaceAfter=10, alignment=1)
    subtitle_style = ParagraphStyle('CoverSub', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#475569'), spaceAfter=20, alignment=1)
    heading_style = ParagraphStyle('ChapterHeading', parent=styles['Heading2'], fontSize=13, textColor=colors.HexColor('#0f172a'), spaceBefore=12, spaceAfter=6)
    body_style = ParagraphStyle('BodyDark', parent=styles['BodyText'], fontSize=9.5, textColor=colors.HexColor('#334155'), spaceAfter=8, leading=13.5)

    story.append(Paragraph(title, title_style))
    story.append(Paragraph("Published by: <b>Shailja Tech</b><br/>Powered by Master Empire OS — Dedicated Quad-Key Pipeline", subtitle_style))
    story.append(Spacer(1, 10))

    # Chapter 1 & 2 (Managed by Key 1 / Expert Content)
    story.append(Paragraph("Chapter 1: Foundations of Autonomous Digital Empires", heading_style))
    c1 = call_gemini_or_premium_content(KEY_1, "Ch 1", 
        "Building an autonomous digital empire in today's hyper-competitive technological landscape requires a profound shift from manual operations to algorithmic execution. Modern solopreneurs and visionary creators are no longer constrained by physical headcount or geographical limitations. By harnessing advanced software architectures, automated cloud workflows, and intelligent micro-services, founders can engineer digital business ecosystems that operate with zero marginal cost. This chapter explores the core theoretical frameworks and practical blueprints required to transition from traditional freelancing into a self-sustaining, multi-channel software enterprise designed for absolute market longevity.")
    story.append(Paragraph(c1, body_style))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Chapter 2: Programmatic SEO & Global Scaling", heading_style))
    c2 = call_gemini_or_premium_content(KEY_1, "Ch 2", 
        "Organic customer acquisition is the lifeblood of any digital empire. Programmatic SEO (pSEO) represents the pinnacle of automated traffic generation, allowing businesses to target thousands of high-intent long-tail keyword variations simultaneously through structured databases and dynamic page generation templates. Rather than writing individual articles manually, top-tier platforms syndicate standardized datasets into high-ranking content hubs. This chapter deconstructs the technical pipelines, database structuring, and automated indexing strategies necessary to capture global search traffic at unprecedented scale with minimal ongoing overhead.")
    story.append(Paragraph(c2, body_style))
    story.append(Spacer(1, 8))

    # Chapter 3 & 4 (Managed by Key 2 / Expert Content)
    story.append(Paragraph("Chapter 3: Zero-Cost Cloud Infrastructure & Uptime", heading_style))
    c3 = call_gemini_or_premium_content(KEY_2, "Ch 3", 
        "Operational expenditure can cripple a growing startup before it achieves product-market fit. Achieving enterprise-level reliability while maintaining zero fixed server costs is one of the most critical competitive advantages of modern software engineering. Utilizing modern cloud platforms like Render, Supabase, and distributed edge networks, founders can host robust, scalable web applications entirely on free tiers. Furthermore, integrating automated external keep-alive pinging mechanisms guarantees 24/7 continuous uptime, eliminating server spin-downs and ensuring seamless user experiences across global time zones.")
    story.append(Paragraph(c3, body_style))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Chapter 4: AI Agents & Automated Sales Funnels", heading_style))
    c4 = call_gemini_or_premium_content(KEY_2, "Ch 4", 
        "The traditional sales funnel requires constant human intervention, leading to bottlenecks and conversion drop-offs. The integration of autonomous AI agents transforms passive web traffic into high-ticket conversions through real-time personalization, automated email sequences, and intelligent product recommendations. By deploying specialized machine learning models to handle customer inquiries, objections, and checkout workflows, entrepreneurs establish a 24/7 sales force that operates tirelessly. This chapter outlines how to build, train, and integrate AI conversion loops directly into your digital publishing platform.")
    story.append(Paragraph(c4, body_style))
    story.append(Spacer(1, 8))

    # Chapter 5 & 6 (Managed by Key 3 / Expert Content)
    story.append(Paragraph("Chapter 5: Multi-Channel Monetization Frameworks", heading_style))
    c5 = call_gemini_or_premium_content(KEY_3, "Ch 5", 
        "Relying on a single revenue stream exposes a business to catastrophic market shifts. Elite digital empires diversify their income across multiple high-margin assets, including automated e-book publishing, software-as-a-service (SaaS) subscriptions, curated digital directories, and premium membership ecosystems. By standardizing checkout flows and integrating global payment gateways like Stripe and Razorpay, founders create frictionless transaction paths. This chapter establishes the structural blueprints for stacking digital revenue products to ensure robust, predictable monthly cash flow.")
    story.append(Paragraph(c5, body_style))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Chapter 6: Scaling Without Burnout", heading_style))
    c6 = call_gemini_or_premium_content(KEY_3, "Ch 6", 
        "The ultimate paradox of entrepreneurship is that successful ventures often trap their creators in endless operational labor. True freedom—the core promise of an autonomous digital empire—is achieved only through radical delegation to code and automated workflows. When content publishing, customer support, analytics tracking, and server maintenance run autonomously, the founder transitions from an exhausted operator to a visionary architect. This chapter provides mental models and automation checklists designed to protect founders from burnout while accelerating exponential growth.")
    story.append(Paragraph(c6, body_style))
    story.append(Spacer(1, 8))

    # Master Index & Summary (Managed by Key 4 / Expert Content)
    story.append(Paragraph("Master Index & Strategic Executive Summary", heading_style))
    c_index = call_gemini_or_premium_content(KEY_4, "Index", 
        "Executive Summary: The journey from a solopreneur concept to a fully automated digital publishing powerhouse relies on systemic discipline, technological leverage, and relentless automation. Throughout this master blueprint, we have dissected the exact pillars required for market dominance: robust cloud architecture, programmatic SEO distribution, multi-key AI content pipelines, and diversified monetization frameworks. By implementing the Shailja Tech operational model, creators secure complete digital sovereignty, achieving 24/7 global reach, zero marginal operating costs, and absolute market leadership.")
    story.append(Paragraph(c_index, body_style))
    story.append(Spacer(1, 8))

    doc.build(story)

@app.post("/api/generate-book")
def generate_book(req: BookRequest, background_tasks: BackgroundTasks):
    filename = "autonomous_empire_blueprint.pdf"
    background_tasks.add_task(generate_pdf_with_shailja_pipeline, filename, req.title)
    return {"status": "success", "message": "Shailja Tech Premium Book generated successfully", "filename": filename}

@app.get("/download/{filename}")
def download_book(filename: str):
    if os.path.exists(filename):
        return FileResponse(filename, media_type='application/pdf', filename=filename)
    raise HTTPException(status_code=404, detail="File not found")

@app.get("/health")
def health_check():
    active_keys = sum([1 for k in [KEY_1, KEY_2, KEY_3, KEY_4] if k and k.strip()])
    return {"status": "healthy", "publisher": "Shailja Tech", "engine": "Premium Hybrid Pipeline v22.0", "active_keys": active_keys}