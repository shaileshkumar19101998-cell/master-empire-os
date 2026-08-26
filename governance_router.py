from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
import sqlite3, json, datetime
from pydantic import BaseModel
from typing import Optional
from pipeline_orchestrator import execute_full_pipeline_cycle, log_pipeline_step

router = APIRouter()

def get_db():
    conn = sqlite3.connect("autonomous_local.db")
    conn.row_factory = sqlite3.Row
    return conn

class GovernanceDecisionRequest(BaseModel):
    opportunity_id: str
    decision: str
    reason: Optional[str] = "Manual owner review"
    auth_token: Optional[str] = "MASTER_EMPIRE_SECRET_2026"

@router.get("/api/v1/opportunities/top5")
def get_top5_opportunities():
    conn = get_db()
    cur = conn.cursor()
    rows = cur.execute("SELECT * FROM market_opportunities WHERE status NOT IN ('REJECTED') ORDER BY opportunity_score DESC LIMIT 5").fetchall()
    conn.close()
    return {"status": "success", "count": len(rows), "top5": [dict(r) for r in rows]}

@router.post("/api/v1/governance/decide")
def apply_governance_decision(req: GovernanceDecisionRequest):
    conn = get_db()
    cur = conn.cursor()
    opp = cur.execute("SELECT * FROM market_opportunities WHERE id = ?", (req.opportunity_id,)).fetchone()
    if not opp:
        conn.close()
        raise HTTPException(status_code=404, detail="Opportunity not found")
    current_status = opp["status"]
    decision = req.decision.upper()
    target_status = "APPROVED" if decision == "APPROVE" else ("REJECTED" if decision == "REJECT" else "SAVED_FOR_LATER")
    now = datetime.datetime.utcnow().isoformat()
    cur.execute("UPDATE market_opportunities SET status = ?, updated_at = ? WHERE id = ?", (target_status, now, req.opportunity_id))
    cur.execute("CREATE TABLE IF NOT EXISTS governance_audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, opportunity_id TEXT, previous_status TEXT, new_status TEXT, reason TEXT, decided_at TEXT)")
    cur.execute("INSERT INTO governance_audit_log (opportunity_id, previous_status, new_status, reason, decided_at) VALUES (?, ?, ?, ?, ?)", (req.opportunity_id, current_status, target_status, req.reason, now))
    conn.commit()
    conn.close()
    pipeline_result = None
    if target_status == "APPROVED":
        pipeline_result = execute_full_pipeline_cycle()
        log_pipeline_step("GOVERNANCE_AUTO_TRIGGER", "COMPLETED", opp_id=req.opportunity_id, payload={"decision": "APPROVED", "cycle": pipeline_result})
    return {"status": "success", "opportunity_id": req.opportunity_id, "previous_status": current_status, "new_status": target_status, "pipeline_triggered": target_status == "APPROVED", "pipeline_result": pipeline_result}

@router.get("/admin/dashboard", response_class=HTMLResponse)
def get_control_center_dashboard():
    conn = get_db()
    cur = conn.cursor()
    rows = cur.execute("SELECT * FROM market_opportunities WHERE status NOT IN ('REJECTED') ORDER BY opportunity_score DESC LIMIT 5").fetchall()
    prods_count = len(cur.execute("SELECT id FROM products WHERE status IN ('ACTIVE', 'PUBLISHED')").fetchall())
    conn.close()
    cards = ""
    for o in rows:
        cards += f"<div style='padding:16px; background:#1e293b; margin-bottom:12px; border-radius:8px;'><h3><b>{o['title']}</b> - Score: {o['opportunity_score']}</h3><p>Niche: {o['niche']} | Country: {o['country']}</p><p>{o['problem_statement']}</p></div>"
    return f"<!doctype html><html><body style='background:#0f172a; color:white; padding:20px; font-family:sans-serif;'><h1>WHAT SHOULD WE PUBLISH TODAY?</h1><p>Active Products: {prods_count} | Target Jurisdictions: 197</p>{cards}</body></html>"
