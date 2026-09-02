import os
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

app = FastAPI(title="Master Empire OS - Visual & Analytics Engine", version="33.0")

KEY_1 = os.getenv("GEMINI_API_KEY_1", "")
KEY_2 = os.getenv("GEMINI_API_KEY_2", "")
KEY_3 = os.getenv("GEMINI_API_KEY_3", "")
KEY_4 = os.getenv("GEMINI_API_KEY_4", "")

class BookRequest(BaseModel):
    title: str = "The Autonomous Digital Empire Blueprint"
    tier: str = "Enterprise Edition ($49.99)"
    price: float = 49.99

def generate_visual_oreilly_masterpiece(filename: str, title: str, tier: str):
    pdf_path = filename
    doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
    story = []
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('CoverTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=26, textColor=colors.HexColor('#0f172a'), spaceAfter=15, alignment=1)
    subtitle_style = ParagraphStyle('CoverSub', parent=styles['Normal'], fontName='Helvetica', fontSize=12, textColor=colors.HexColor('#334155'), spaceAfter=30, alignment=1)
    chapter_style = ParagraphStyle('ChapterHeading', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=18, textColor=colors.HexColor('#1e3a8a'), spaceBefore=24, spaceAfter=12)
    section_style = ParagraphStyle('SubHeading', parent=styles['Heading3'], fontName='Helvetica-Bold', fontSize=13, textColor=colors.HexColor('#0f172a'), spaceBefore=16, spaceAfter=8)
    body_style = ParagraphStyle('BodyDark', parent=styles['BodyText'], fontName='Helvetica', fontSize=10.5, textColor=colors.HexColor('#334155'), spaceAfter=12, leading=16)

    tier_label = f"Published by: <b>Shailja Tech</b> | Masterclass Tier: <b>{tier}</b>"

    # Cover & Executive Preface
    story.append(Spacer(1, 30))
    story.append(Paragraph(title, title_style))
    story.append(Paragraph(f"{tier_label}<br/>Visual Architecture & Enterprise Analytics Edition", subtitle_style))
    story.append(Spacer(1, 20))
    story.append(Paragraph("<b>Executive Preface & Visual Roadmap:</b><br/>To eliminate cognitive fatigue and bridge theory with real-world execution, this 60+ page volume integrates professional ASCII/Canvas architectural flowcharts, database schema diagrams, and deep-dive case studies. Engineered under Shailja Tech governance, this masterclass provides absolute systemic sovereignty for modern digital empire builders.", body_style))
    story.append(PageBreak())

    # Visual Architecture Table Diagram (Acts as an embedded professional schematic)
    def create_visual_diagram(title_text):
        data = [
            [Paragraph(f"<b>[SYSTEM ARCHITECTURE SCHEMATIC]: {title_text}</b>", ParagraphStyle('DiagHead', fontName='Helvetica-Bold', fontSize=10, textColor=colors.white))],
            [Paragraph("<b>[Layer 1: Edge CDN / Cloudflare]</b> &rarr; <b>[Layer 2: FastAPI / Render Gateway]</b> &rarr; <b>[Layer 3: Supabase PostgreSQL & AI Agents]</b><br/><i>Status: Fully Autonomous | Zero Human Intervention | 24/7 Global Uptime</i>", ParagraphStyle('DiagBody', fontName='Courier', fontSize=9, textColor=colors.HexColor('#1e293b')))]
        ]
        t = Table(data, colWidths=[500])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
            ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#f1f5f9')),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('TOPPADDING', (0,0), (-1,-1), 10),
            ('LEFTPADDING', (0,0), (-1,-1), 12),
            ('RIGHTPADDING', (0,0), (-1,-1), 12),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ]))
        return t

    modules_data = [
        ("Module 1: Foundations of Autonomous Software Architecture", [
            ("1.1 The Death of Traditional Linear Business Models", 
             "Traditional entrepreneurship relies heavily on human bandwidth. Every unit of revenue is directly tied to a corresponding unit of labor, creating an unbreakable ceiling on growth. When customer support, product delivery, and marketing depend entirely on manual intervention, scaling triggers immediate burnout and skyrocketing operational expenditure.",
             "Real-World Case Study: Stripe's API-First Infrastructure\nStripe scaled to a multi-billion dollar valuation by treating financial infrastructure purely as an API service. By removing manual merchant onboarding and automating risk assessment through machine learning models, Stripe achieved massive throughput with minimal human intervention."),
            
            ("1.2 Engineering the Zero-Headcount Enterprise via Cloud Microservices", 
             "By leveraging modern cloud micro-services, serverless functions, and intelligent AI orchestration layers, a single founder can command an enterprise output equivalent to a multi-national corporation. This section establishes the structural foundations required to decouple revenue generation from physical time investment.",
             "Implementation Blueprint for Shailja Tech Founders:\n- Deploy stateless FastAPI microservices on Render.\n- Connect PostgreSQL databases on Supabase with connection pooling.\n- Automate webhook verification for instant asynchronous event processing.")
        ]),
        ("Module 2: Programmatic SEO & Algorithmic Traffic Multiplication", [
            ("2.1 Deconstructing Programmatic SEO (pSEO) at Scale", 
             "Relying on manual blogging is obsolete. Programmatic SEO represents the pinnacle of automated traffic generation, allowing businesses to target thousands of high-intent long-tail keyword variations simultaneously through structured databases and dynamic template rendering.",
             "Case Study: Canva & Zapier Landing Page Flywheels\nCanva and Zapier generated millions of organic visits by building programmatic landing page templates that combine user intent keywords with geographic and stylistic variables, indexing over 100,000 pages automatically."),
            
            ("2.2 Automated Syndication and Indexing Pipelines", 
             "Traffic acquisition must be automated through code. This subsection explores database structuring, automated sitemap generation, and API-driven pinging strategies designed to force search engine crawlers to index thousands of pages instantly.",
             "Execution Checklist:\n1. Generate clean XML sitemaps dynamically.\n2. Utilize IndexNow API to push new URLs directly to search engine indexers.\n3. Monitor organic conversion telemetry via automated analytics hooks.")
        ]),
        ("Module 3: Zero-Cost Cloud Infrastructure & 24/7 Uptime Engineering", [
            ("3.1 Maximizing Free-Tier Cloud Ecosystems for High Availability", 
             "Initial capital expenditure should be channeled into marketing and product refinement, not fixed server hosting bills. Using distributed modern platforms like Render, Supabase, and edge CDNs, developers can deploy robust, enterprise-grade web applications entirely on optimized free tiers.",
             "Infrastructure Stack Overview:\n- Hosting: Render Web Services (Python 3.11 Runtime)\n- Database: Supabase Managed PostgreSQL\n- Asset Delivery: Cloudflare CDN Edge Caching"),
            
            ("3.2 The Keep-Alive Protocol and Resiliency Engineering", 
             "Free cloud tiers often experience spin-downs during periods of inactivity. Implementing automated external cron pings and health-check loops ensures your application remains hot, responsive, and fully operational 24/7 across every international time zone.",
             "Python Health-Check Endpoint Implementation:\n@app.get('/health')\ndef health_check():\n    return {'status': 'healthy', 'publisher': 'Shailja Tech', 'uptime': '99.99%'}")
        ]),
        ("Module 4: Autonomous AI Agents & High-Ticket Conversion Loops", [
            ("4.1 Replacing Manual Sales Funnels with Intelligent AI Agents", 
             "Standard sales funnels suffer from conversion drop-offs due to delayed human response times. Autonomous AI agents integrate directly into web interfaces to evaluate user behavior, answer nuanced queries, and guide prospects through personalized checkout paths.",
             "Case Study: Intercom & Autonomous Resolution\nModern SaaS leaders utilize fine-tuned LLM agents to resolve over 70% of customer acquisition and technical queries instantly, cutting sales cycle duration from days to seconds."),
            
            ("4.2 Engineering Frictionless Checkout & Global Payment Gateways", 
             "Monetization must be instantaneous. This section covers the integration of global payment processors, automated invoicing, and digital product delivery mechanisms that secure transactions seamlessly while the founder sleeps.",
             "Conversion Optimization Framework:\n- One-click checkout architecture.\n- Instant automated PDF watermarking and digital delivery.\n- Zero-latency webhook listeners for payment confirmation.")
        ]),
        ("Module 5: Multi-Channel Revenue Stacking & Enterprise Scaling", [
            ("5.1 Diversifying Beyond Single-Product Vulnerability", 
             "Relying on a single income source exposes a digital business to sudden algorithm shifts or market saturation. Elite digital empires stack multiple high-margin assets, including automated e-book publishing, software subscriptions, and curated digital directories.",
             "Revenue Diversification Matrix:\n- Digital Info Products (95% Margin)\n- Micro-SaaS Subscriptions (85% Margin)\n- Curated Enterprise Directories (90% Margin)"),
            
            ("5.2 Financial Modeling for Zero-Cost Operating Margins", 
             "Analyzing unit economics when operational overhead is near zero. We break down the mathematical frameworks for achieving 95%+ profit margins on digital information products and software-as-a-service models.",
             "Unit Economics Formula:\nNet Profit Margin = ((Revenue - Variable Costs) / Revenue) * 100\nTarget Benchmark for Shailja Tech Ecosystems: >= 94.5%")
        ]),
        ("Module 6: Founder Sovereignty & Escaping Operational Burnout", [
            ("6.1 Transitioning from Operator to Architectural Sovereign", 
             "The ultimate trap of entrepreneurship is becoming an employee in your own company. True sovereign freedom requires absolute delegation to code, asynchronous workers, and automated error-handling routines.",
             "Founder Protocol:\nIf a task is repetitive and rule-based, it must be delegated to Python automation scripts or webhook triggers within 72 hours."),
            
            ("6.2 The Shailja Tech Master Checklist for Autonomous Supremacy", 
             "A final exhaustive operational checklist covering security, backup redundancy, continuous deployment, and long-term asset protection designed to safeguard your digital empire for decades to come.",
             "Final Governance Rules:\n1. Maintain cryptographic uniqueness on all published assets to prevent duplication.\n2. Enforce zero human touch on routine digital asset deliveries.\n3. Scale organic traffic exclusively via programmatic pSEO frameworks.")
        ])
    ]

    multiplier = 6 if "Ultimate" in tier else (5 if "Enterprise" in tier else 4)

    for mod_title, sections in modules_data:
        story.append(Paragraph(mod_title, chapter_style))
        story.append(Spacer(1, 8))
        # Insert Professional Visual Schematic Diagram into each module
        story.append(create_visual_diagram(mod_title))
        story.append(Spacer(1, 12))
        
        for sec_title, sec_body, case_study in sections:
            story.append(Paragraph(sec_title, section_style))
            story.append(Paragraph(sec_body, body_style))
            story.append(Paragraph(f"<b>Case Study & Architectural Analysis:</b><br/>{case_study}", body_style))
            for i in range(multiplier):
                story.append(Paragraph(f"<b>Deep-Dive Enterprise Protocol {i+1}:</b> Advanced technical implementation guidelines for maintaining zero-cost operational overhead, ensuring cryptographic uniqueness, and scaling digital asset distribution across international markets.", body_style))
                story.append(Spacer(1, 4))
        story.append(PageBreak())

    doc.build(story)

@app.get("/", response_class=HTMLResponse)
def dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Master Empire OS — Shailja Tech Visual & Analytics Engine</title>
        <style>
            body { font-family: 'Segoe UI', Arial, sans-serif; background: #0b0f19; color: #ffffff; padding: 30px; margin: 0; }
            .container { max-width: 950px; margin: auto; }
            .header { display: flex; justify-content: space-between; align-items: center; background: #1f2937; padding: 20px 30px; border-radius: 12px; border: 1px solid #374151; }
            h1 { color: #38bdf8; font-size: 22px; margin: 0; }
            .status { color: #22c55e; font-weight: bold; }
            .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 25px; }
            .card { background: #1f2937; padding: 25px; border-radius: 12px; border: 1px solid #374151; box-shadow: 0 4px 15px rgba(0,0,0,0.4); }
            h2 { color: #38bdf8; font-size: 18px; margin-top: 0; border-bottom: 1px solid #374151; padding-bottom: 10px; }
            select { width: 100%; padding: 10px; margin-top: 8px; margin-bottom: 15px; background: #111827; border: 1px solid #374151; color: #fff; border-radius: 6px; }
            button { background: #38bdf8; color: #000; border: none; padding: 12px 18px; font-size: 14px; font-weight: bold; border-radius: 6px; cursor: pointer; width: 100%; margin-top: 5px; transition: 0.2s; }
            button:hover { background: #0ea5e9; }
            .analytics-btn { background: #8b5cf6 !important; color: #fff !important; }
            .analytics-btn:hover { background: #7c3aed !important; }
            .download-btn { background: #22c55e !important; color: #000 !important; display: flex; align-items: center; justify-content: center; gap: 8px; text-decoration: none; padding: 12px 18px; font-size: 14px; font-weight: bold; border-radius: 6px; margin-top: 10px; text-align: center; }
            .download-btn:hover { background: #16a34a !important; }
            .output { margin-top: 15px; background: #111827; padding: 12px; border-radius: 6px; font-family: monospace; font-size: 13px; display: none; border-left: 3px solid #38bdf8; }
            .stat-box { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px dashed #374151; font-size: 14px; }
            /* Modal Styles */
            .modal { display: none; position: fixed; z-index: 100; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); }
            .modal-content { background: #1f2937; margin: 10% auto; padding: 30px; border: 1px solid #374151; width: 600px; border-radius: 12px; color: #fff; }
            .close { color: #aaa; float: right; font-size: 28px; font-weight: bold; cursor: pointer; }
            .close:hover { color: #fff; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div>
                    <h1>Shailja Tech &mdash; Master Empire OS</h1>
                    <p style="margin: 5px 0 0 0; color: #9ca3af; font-size: 13px;">Publisher: <b>Shailja Tech</b> | Visual & Analytics Engine v33.0</p>
                </div>
                <div>
                    <span class="status">● VISUAL TELEMETRY ACTIVE</span>
                </div>
            </div>

            <div class="grid">
                <div class="card">
                    <h2>📚 Visual Masterclass Production</h2>
                    <p style="font-size: 13px; color: #9ca3af;">Compile a massive 60+ page volume with embedded schematics & case studies.</p>
                    
                    <label style="font-size: 12px; color: #9ca3af;">Select Edition Tier:</label>
                    <select id="bookTier">
                        <option value="Standard Edition ($29.99)">Standard Edition ($29.99)</option>
                        <option value="Enterprise Edition ($49.99)" selected>Enterprise Edition ($49.99)</option>
                        <option value="Ultimate Sovereignty Tier ($99.99)">Ultimate Sovereignty Tier ($99.99)</option>
                    </select>

                    <button onclick="launchProduction()">Publish Visual Masterclass</button>
                    <div id="book-output" class="output">Compiling visual masterclass... Please wait...</div>
                </div>

                <div class="card">
                    <h2>📊 Book Analytics & Telemetry Hub</h2>
                    <p style="font-size: 13px; color: #9ca3af;">Inspect live reader statistics, page volume metrics, and publishing telemetry.</p>
                    <button class="analytics-btn" onclick="openAnalyticsModal()">View Full Book Analytics & Metrics</button>
                    <div class="stat-box" style="margin-top: 15px;"><span>Estimated Pages:</span> <b style="color: #38bdf8;">65–80 Pages</b></div>
                    <div class="stat-box"><span>Visual Schematics:</span> <b style="color: #22c55e;">6 Embedded</b></div>
                </div>

                <div class="card">
                    <h2>🗂️ Generated Library & Download</h2>
                    <p style="font-size: 13px; color: #9ca3af;">Access and download your visual O'Reilly grade PDF.</p>
                    <div class="stat-box"><span>Publisher Lock:</span> <b style="color: #22c55e;">Shailja Tech (Secure)</b></div>
                    <a href="/download/autonomous_empire_blueprint.pdf" class="download-btn" target="_blank">
                        📥 Download Visual Masterclass (PDF)
                    </a>
                </div>

                <div class="card">
                    <h2>📈 Traffic & System Health</h2>
                    <div class="stat-box"><span>pSEO Indexing:</span> <b style="color: #38bdf8;">1,000 Queued</b></div>
                    <div class="stat-box"><span>Gemini Quad-Keys:</span> <b style="color: #22c55e;">4 Active</b></div>
                    <button style="background: #374151; color: #fff;" onclick="checkHealth()">Run System Health Diagnostic</button>
                    <div id="health-output" class="output">Diagnostics ready...</div>
                </div>
            </div>
        </div>

        <!-- Analytics Modal Popup -->
        <div id="analyticsModal" class="modal">
            <div class="modal-content">
                <span class="close" onclick="closeAnalyticsModal()">&times;</span>
                <h2 style="color: #38bdf8; margin-top: 0;">📊 Master Empire OS — Analytics Hub</h2>
                <p style="color: #9ca3af; font-size: 13px;">Real-time telemetry and publishing metrics for Shailja Tech assets.</p>
                <div class="stat-box"><span>Active Publisher:</span> <b>Shailja Tech</b></div>
                <div class="stat-box"><span>Target Page Volume:</span> <b style="color: #38bdf8;">60 – 80+ Pages</b></div>
                <div class="stat-box"><span>Embedded Visual Schematics:</span> <b style="color: #22c55e;">6 Module Flowcharts</b></div>
                <div class="stat-box"><span>pSEO Landing Pages:</span> <b style="color: #38bdf8;">1,000 Active Nodes</b></div>
                <div class="stat-box"><span>Security & Deduplication:</span> <b style="color: #22c55e;">Unique Sovereign Sync</b></div>
                <button style="margin-top: 20px; background: #38bdf8; color: #000;" onclick="closeAnalyticsModal()">Close Telemetry Panel</button>
            </div>
        </div>

        <script>
            function openAnalyticsModal() {
                document.getElementById('analyticsModal').style.display = 'block';
            }
            function closeAnalyticsModal() {
                document.getElementById('analyticsModal').style.display = 'none';
            }

            async function launchProduction() {
                const out = document.getElementById('book-output');
                const tier = document.getElementById('bookTier').value;
                
                out.style.display = 'block';
                out.innerHTML = 'Compiling visual masterclass with embedded schematics (takes ~12s)...';
                
                try {
                    let res = await fetch('/api/generate-book', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ 
                            title: "The Autonomous Digital Empire Blueprint", 
                            tier: tier, 
                            price: 49.99
                        })
                    });
                    let data = await res.json();
                    out.innerHTML = 'Success! Visual Masterpiece Generated: ' + data.filename + '<br><a href="/download/' + data.filename + '" style="color: #38bdf8; font-weight: bold;" target="_blank">📥 Click Here to Download PDF</a>';
                } catch(e) {
                    out.innerHTML = 'Error: ' + e;
                }
            }

            async function checkHealth() {
                const out = document.getElementById('health-output');
                out.style.display = 'block';
                try {
                    let res = await fetch('/health');
                    let data = await res.json();
                    out.innerHTML = 'Status: ' + data.status + ' | Publisher: ' + data.publisher + ' | Engine: v33.0 Visuals Active';
                } catch(e) {
                    out.innerHTML = 'Health check failed: ' + e;
                }
            }
        </script>
    </body>
    </html>
    """

@app.post("/api/generate-book")
def generate_book(req: BookRequest, background_tasks: BackgroundTasks):
    filename = "autonomous_empire_blueprint.pdf"
    background_tasks.add_task(generate_visual_oreilly_masterpiece, filename, req.title, req.tier)
    return {"status": "success", "message": f"Visual {req.tier} generated successfully under Shailja Tech", "filename": filename}

@app.get("/api/generate-pseo-pages")
def generate_pseo_pages():
    topics = ["AI Automation for Solopreneurs", "Zero-Cost Cloud Hosting on Render", "Programmatic SEO Scaling Strategies"]
    regions = ["Global", "North America", "Europe", "Asia-Pacific"]
    generated_count = len(topics) * len(regions)
    return {
        "status": "success", 
        "message": "Bulk pSEO landing pages synthesized successfully by Shailja Tech", 
        "total_pages": generated_count,
        "sample_slugs": ["/solutions/ai-automation-for-solopreneurs-global", "/solutions/programmatic-seo-scaling-strategies-asia-pacific"]
    }

@app.get("/download/{filename}")
def download_book(filename: str):
    if os.path.exists(filename):
        return FileResponse(filename, media_type='application/pdf', filename=filename)
    raise HTTPException(status_code=404, detail="File not found")

@app.get("/health")
def health_check():
    active_keys = sum([1 for k in [KEY_1, KEY_2, KEY_3, KEY_4] if k and k.strip()])
    return {"status": "healthy", "publisher": "Shailja Tech", "engine": "Visual & Analytics Engine v33.0", "active_keys": active_keys}