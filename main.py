import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(db_url, pool_pre_ping=True)

app = FastAPI(title="Autonomous Business OS", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ApprovalRequest(BaseModel):
    task_id: int
    decision: str  # APPROVED or REJECTED

@app.get("/health")
def health_check():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
        return {"status": "HEALTHY", "database": "CONNECTED", "mode": "AUTONOMOUS_ENTERPRISE"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database Disconnected: {str(e)}")

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

@app.post("/api/approve-task")
def approve_task(req: ApprovalRequest):
    try:
        with engine.begin() as conn:
            row = conn.execute(text("SELECT * FROM pending_approvals WHERE id = :id"), {"id": req.task_id}).mappings().first()
            if not row:
                raise HTTPException(status_code=404, detail="Task not found")

            conn.execute(text("UPDATE pending_approvals SET status = :decision WHERE id = :id"), {"decision": req.decision.upper(), "id": req.task_id})

            if req.decision.upper() == "APPROVED":
                conn.execute(text("""
                    INSERT INTO books (title, niche, tier, price, price_val, market_price, badge, visits, orders, revenue, content_preview, file, seo_status, status)
                    VALUES (:title, :niche, 'Autonomous Tier', '₹499 ($6)', 499, '₹1999 ($24)', 'AI SCALED ASSET', 0, 0, 0, :content, '', 'Active 24x7 SEO', 'ACTIVE')
                """), {
                    "title": row["title"],
                    "niche": row["niche"],
                    "content": row["proposed_content"]
                })

            conn.execute(text("""
                INSERT INTO system_logs (module, status, message)
                VALUES ('APPROVAL_ENGINE', 'SUCCESS', :msg)
            """), {"msg": f"Task #{req.task_id} marked as {req.decision.upper()}."})

        return {"status": "SUCCESS", "message": f"Task #{req.task_id} {req.decision.upper()} successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Autonomous Business OS - Live Dashboard</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b0f19; color: #f3f4f6; margin: 0; padding: 24px; }
            .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1f2937; padding-bottom: 16px; margin-bottom: 24px; }
            .badge { background: #10b98122; color: #10b981; border: 1px solid #10b981; padding: 4px 12px; border-radius: 9999px; font-weight: 600; font-size: 13px; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }
            .card { background: #111827; border: 1px solid #1f2937; border-radius: 10px; padding: 18px; }
            .card-title { font-size: 13px; color: #9ca3af; text-transform: uppercase; font-weight: 600; margin-bottom: 6px; }
            .card-value { font-size: 24px; font-weight: bold; color: #fff; }
            .section { background: #111827; border: 1px solid #1f2937; border-radius: 10px; padding: 20px; margin-bottom: 24px; }
            .btn-approve { background: #10b981; color: #fff; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-weight: 600; }
            .btn-reject { background: #ef4444; color: #fff; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-weight: 600; margin-left: 8px; }
            table { width: 100%; border-collapse: collapse; margin-top: 12px; }
            th, td { text-align: left; padding: 10px; border-bottom: 1px solid #1f2937; font-size: 14px; }
            th { color: #9ca3af; }
        </style>
    </head>
    <body>
        <div class="header">
            <div>
                <h1 style="margin: 0; font-size: 22px;">Autonomous Business OS</h1>
                <p style="margin: 4px 0 0 0; color: #9ca3af; font-size: 14px;">PostgreSQL Enterprise Control Center</p>
            </div>
            <div class="badge">● LIVE POSTGRESQL CLOUD</div>
        </div>

        <div class="grid" id="metrics-grid">
            <div class="card"><div class="card-title">Active Products</div><div class="card-value" id="m-prod">--</div></div>
            <div class="card"><div class="card-title">Total Visits</div><div class="card-value" id="m-visits">--</div></div>
            <div class="card"><div class="card-title">Total Orders</div><div class="card-value" id="m-orders">--</div></div>
            <div class="card"><div class="card-title">Pending Approvals</div><div class="card-value" id="m-pending" style="color: #f59e0b;">--</div></div>
        </div>

        <div class="section">
            <h2 style="font-size: 16px; margin-top: 0;">⚡ Human-In-The-Loop Approval Queue</h2>
            <div id="pending-container"><p style="color: #6b7280;">Loading pending tasks...</p></div>
        </div>

        <div class="section">
            <h2 style="font-size: 16px; margin-top: 0;">📚 Active Enterprise Catalog</h2>
            <table>
                <thead>
                    <tr><th>ID</th><th>Title</th><th>Niche</th><th>Price</th><th>Visits</th></tr>
                </thead>
                <tbody id="books-tbody"></tbody>
            </table>
        </div>

        <script>
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
                        pBox.innerHTML = '<p style="color: #10b981;">✓ All queued autonomous actions are approved and running.</p>';
                    } else {
                        pBox.innerHTML = data.pending_approvals.map(p => `
                            <div style="background: #1f2937; padding: 14px; border-radius: 8px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <div style="font-weight: 600;">${p.title}</div>
                                    <div style="font-size: 13px; color: #9ca3af;">Niche: ${p.niche} | Type: ${p.task_type}</div>
                                </div>
                                <div>
                                    <button class="btn-approve" onclick="handleDecision(${p.id}, 'APPROVED')">Approve & Publish</button>
                                    <button class="btn-reject" onclick="handleDecision(${p.id}, 'REJECTED')">Reject</button>
                                </div>
                            </div>
                        `).join('');
                    }

                    const tBody = document.getElementById('books-tbody');
                    tBody.innerHTML = data.products.map(b => `
                        <tr>
                            <td>#${b.id}</td>
                            <td><b>${b.title}</b></td>
                            <td>${b.niche || '--'}</td>
                            <td>${b.price || '--'}</td>
                            <td>${b.visits}</td>
                        </tr>
                    `).join('');
                } catch (e) {
                    console.error("Fetch failed", e);
                }
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