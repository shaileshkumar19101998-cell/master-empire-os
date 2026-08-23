import os
import random
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from worker import run_research_task_with_retry

load_dotenv()
db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(db_url, pool_pre_ping=True)

app = FastAPI(title="Autonomous Business OS", version="2.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ApprovalRequest(BaseModel):
    task_id: int
    decision: str

class GenerateIdeaRequest(BaseModel):
    custom_niche: str = ""

@app.get("/api/analytics")
def get_analytics():
    try:
        with engine.connect() as conn:
            books_res = conn.execute(text("SELECT * FROM books ORDER BY id DESC;")).mappings().all()
            pending_res = conn.execute(text("SELECT * FROM pending_approvals WHERE status = 'PENDING' ORDER BY id DESC;")).mappings().all()
            logs_res = conn.execute(text("SELECT * FROM system_logs ORDER BY id DESC LIMIT 10;")).mappings().all()

            total_visits = sum(b.get("visits", 0) for b in books_res)
            total_orders = sum(b.get("orders", 0) for b in books_res)
            total_rev = sum(b.get("revenue", 0) for b in books_res)

        return {
            "metrics": {
                "total_products": len(books_res),
                "total_visits": total_visits,
                "total_orders": total_orders,
                "total_revenue": f"₹{total_rev:,}",
                "pending_approvals_count": len(pending_res)
            },
            "products": [dict(b) for b in books_res],
            "pending_approvals": [dict(p) for p in pending_res],
            "system_logs": [dict(l) for l in logs_res]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/think-idea")
def think_new_idea(req: GenerateIdeaRequest):
    tiers = ["Foundation Tier", "Standard Tier", "Industry Mastery Tier"]
    niches = ["AI Workflow Automation", "Autonomous E-Commerce", "B2B Lead Generation", "SaaS Growth Engine"]
    target = req.custom_niche.strip() if req.custom_niche.strip() else f"{random.choice(niches)} - {random.choice(tiers)}"
    success = run_research_task_with_retry(target)
    if success:
        return {"status": "SUCCESS"}
    raise HTTPException(status_code=500, detail="Research failed")

@app.post("/api/approve-task")
def approve_task(req: ApprovalRequest):
    try:
        with engine.begin() as conn:
            row = conn.execute(text("SELECT * FROM pending_approvals WHERE id = :id"), {"id": req.task_id}).mappings().first()
            if not row:
                raise HTTPException(status_code=404, detail="Task not found")

            conn.execute(text("UPDATE pending_approvals SET status = :decision WHERE id = :id"), {"decision": req.decision.upper(), "id": req.task_id})

            if req.decision.upper() == "APPROVED":
                title_lower = (row["title"] + row["niche"]).lower()
                tier_val = "Normal Standard"
                if "foundation" in title_lower:
                    tier_val = "Foundation Level"
                elif "industry" in title_lower or "mastery" in title_lower or "advanced" in title_lower:
                    tier_val = "Industry Level"

                conn.execute(text("""
                    INSERT INTO books (title, niche, tier, price, price_val, market_price, badge, visits, orders, revenue, content_preview, file, seo_status, status)
                    VALUES (:title, :niche, :tier, '₹499 ($6)', 499, '₹1999 ($24)', 'AI ASSET', 0, 0, 0, :content, '', 'Active 24x7 SEO', 'ACTIVE')
                """), {
                    "title": row["title"],
                    "niche": row["niche"],
                    "tier": tier_val,
                    "content": row["proposed_content"]
                })
        return {"status": "SUCCESS"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Autonomous Business OS</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b0f19; color: #f3f4f6; margin: 0; padding: 24px; }
            .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1f2937; padding-bottom: 16px; margin-bottom: 24px; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }
            .card { background: #111827; border: 1px solid #1f2937; border-radius: 10px; padding: 18px; }
            .card-title { font-size: 13px; color: #9ca3af; text-transform: uppercase; font-weight: 600; margin-bottom: 6px; }
            .card-value { font-size: 24px; font-weight: bold; color: #fff; }
            .section { background: #111827; border: 1px solid #1f2937; border-radius: 10px; padding: 20px; margin-bottom: 24px; }
            
            .btn-think { background: #6366f1; color: #fff; border: none; padding: 9px 18px; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 14px; }
            .btn-think:hover { background: #4f46e5; }
            
            /* Tier Folders */
            .folder-nav { display: flex; gap: 10px; margin-bottom: 16px; border-bottom: 1px solid #1f2937; padding-bottom: 12px; }
            .folder-btn { background: #1f2937; color: #9ca3af; border: 1px solid #374151; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 13px; }
            .folder-btn.active { background: #2563eb; color: #fff; border-color: #3b82f6; }
            
            .btn-approve { background: #10b981; color: #fff; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-weight: 600; margin-right: 6px; }
            .btn-reject { background: #ef4444; color: #fff; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-weight: 600; }
            table { width: 100%; border-collapse: collapse; margin-top: 10px; }
            th, td { text-align: left; padding: 10px; border-bottom: 1px solid #1f2937; font-size: 14px; }
            th { color: #9ca3af; }
            .tag { padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
            .tag-found { background: #3b82f622; color: #3b82f6; border: 1px solid #3b82f6; }
            .tag-norm { background: #f59e0b22; color: #f59e0b; border: 1px solid #f59e0b; }
            .tag-ind { background: #8b5cf622; color: #8b5cf6; border: 1px solid #8b5cf6; }
        </style>
    </head>
    <body>
        <div class="header">
            <div>
                <h1 style="margin: 0; font-size: 22px;">Autonomous Business OS</h1>
                <p style="margin: 4px 0 0 0; color: #9ca3af; font-size: 14px;">PostgreSQL Enterprise Control Center</p>
            </div>
            <div>
                <button class="btn-think" onclick="triggerThinkIdea()">⚡ Think / Generate AI Idea</button>
            </div>
        </div>

        <div class="grid">
            <div class="card"><div class="card-title">Active Products</div><div class="card-value" id="m-prod">--</div></div>
            <div class="card"><div class="card-title">Total Visits</div><div class="card-value" id="m-visits">--</div></div>
            <div class="card"><div class="card-title">Total Orders</div><div class="card-value" id="m-orders">--</div></div>
            <div class="card"><div class="card-title">Pending Approvals</div><div class="card-value" id="m-pending" style="color: #f59e0b;">--</div></div>
        </div>

        <div class="section">
            <h2 style="font-size: 16px; margin-top: 0;">⚡ Human-In-The-Loop Approval Queue</h2>
            <div id="pending-container"><p style="color: #6b7280;">Loading...</p></div>
        </div>

        <div class="section">
            <h2 style="font-size: 16px; margin-top: 0; margin-bottom: 12px;">📁 Product Books by Level</h2>
            
            <div class="folder-nav">
                <button class="folder-btn active" onclick="setFolder('ALL', this)">📂 All Books (<span id="cnt-all">0</span>)</button>
                <button class="folder-btn" onclick="setFolder('Foundation', this)">📘 Foundation Level (<span id="cnt-found">0</span>)</button>
                <button class="folder-btn" onclick="setFolder('Normal', this)">📗 Normal Standard (<span id="cnt-norm">0</span>)</button>
                <button class="folder-btn" onclick="setFolder('Industry', this)">📕 Industry Level (<span id="cnt-ind">0</span>)</button>
            </div>

            <table>
                <thead>
                    <tr><th>ID</th><th>Book Title</th><th>Niche</th><th>Tier Level</th><th>Price</th></tr>
                </thead>
                <tbody id="books-tbody"></tbody>
            </table>
        </div>

        <script>
            let allBooks = [];
            let activeFolder = 'ALL';

            async function loadData() {
                try {
                    const res = await fetch('/api/analytics');
                    const data = await res.json();
                    document.getElementById('m-prod').innerText = data.metrics.total_products;
                    document.getElementById('m-visits').innerText = data.metrics.total_visits;
                    document.getElementById('m-orders').innerText = data.metrics.total_orders;
                    document.getElementById('m-pending').innerText = data.metrics.pending_approvals_count;

                    const pBox = document.getElementById('pending-container');
                    if (data.pending_approvals.length === 0) {
                        pBox.innerHTML = '<p style="color: #10b981; margin:0;">✓ Approval queue is clear. Click <b>⚡ Think / Generate AI Idea</b> above to generate new book drafts.</p>';
                    } else {
                        pBox.innerHTML = data.pending_approvals.map(p => `
                            <div style="background: #1f2937; padding: 14px; border-radius: 8px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <div style="font-weight: 600; font-size: 15px;">${p.title}</div>
                                    <div style="font-size: 13px; color: #9ca3af; margin-top: 4px;">Niche: <b>${p.niche}</b></div>
                                </div>
                                <div>
                                    <button class="btn-approve" onclick="handleDecision(${p.id}, 'APPROVED')">✓ Approve</button>
                                    <button class="btn-reject" onclick="handleDecision(${p.id}, 'REJECTED')">✕ Reject</button>
                                </div>
                            </div>
                        `).join('');
                    }

                    allBooks = data.products;
                    updateFolderCounts();
                    renderTable();
                } catch (e) {
                    console.error(e);
                }
            }

            function updateFolderCounts() {
                document.getElementById('cnt-all').innerText = allBooks.length;
                document.getElementById('cnt-found').innerText = allBooks.filter(b => (b.tier || b.title).toLowerCase().includes('foundation')).length;
                document.getElementById('cnt-ind').innerText = allBooks.filter(b => (b.tier || b.title).toLowerCase().includes('industry') || (b.tier || b.title).toLowerCase().includes('mastery')).length;
                document.getElementById('cnt-norm').innerText = allBooks.length - (parseInt(document.getElementById('cnt-found').innerText) + parseInt(document.getElementById('cnt-ind').innerText));
            }

            function setFolder(folder, btn) {
                activeFolder = folder;
                document.querySelectorAll('.folder-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                renderTable();
            }

            function renderTable() {
                const tBody = document.getElementById('books-tbody');
                const filtered = allBooks.filter(b => {
                    const textContent = ((b.tier || '') + ' ' + (b.title || '')).toLowerCase();
                    if (activeFolder === 'Foundation') return textContent.includes('foundation');
                    if (activeFolder === 'Industry') return textContent.includes('industry') || textContent.includes('mastery');
                    if (activeFolder === 'Normal') return !textContent.includes('foundation') && !textContent.includes('industry') && !textContent.includes('mastery');
                    return true;
                });

                tBody.innerHTML = filtered.map(b => {
                    const textContent = ((b.tier || '') + ' ' + (b.title || '')).toLowerCase();
                    let tTag = '<span class="tag tag-norm">Normal Standard</span>';
                    if (textContent.includes('foundation')) tTag = '<span class="tag tag-found">Foundation Level</span>';
                    if (textContent.includes('industry') || textContent.includes('mastery')) tTag = '<span class="tag tag-ind">Industry Level</span>';

                    return `
                        <tr>
                            <td>#${b.id}</td>
                            <td><b>${b.title}</b></td>
                            <td>${b.niche || '--'}</td>
                            <td>${tTag}</td>
                            <td>${b.price || '₹499'}</td>
                        </tr>
                    `;
                }).join('');
            }

            async function triggerThinkIdea() {
                const niche = prompt("Enter specific niche (or leave blank for AI Auto-Discovery):", "");
                if (niche === null) return;
                alert("Agent activated. Generating new draft...");
                await fetch('/api/think-idea', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ custom_niche: niche })
                });
                loadData();
            }

            async function handleDecision(taskId, decision) {
                await fetch('/api/approve-task', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ task_id: taskId, decision: decision })
                });
                loadData();
            }

            loadData();
        </script>
    </body>
    </html>
    """