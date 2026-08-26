from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
import sqlite3, datetime
from pydantic import BaseModel
from typing import Optional
from pipeline_orchestrator import execute_full_pipeline_cycle

router = APIRouter()

def get_db():
    conn = sqlite3.connect("autonomous_local.db")
    conn.row_factory = sqlite3.Row
    return conn

class GovernanceDecisionRequest(BaseModel):
    opportunity_id: str
    decision: str
    reason: Optional[str] = "Manual review"

@router.get("/api/v1/opportunities/top5")
def get_top5_opportunities():
    conn = get_db()
    cur = conn.cursor()
    rows = cur.execute("SELECT * FROM market_opportunities WHERE status NOT IN ('REJECTED') ORDER BY opportunity_score DESC LIMIT 5").fetchall()
    conn.close()
    top5 = []
    for r in rows:
        d = dict(r)
        if not d.get("source_type"):
            d["source_type"] = "SEEDED / INTERNAL"
            d["confidence_score"] = 100.0
            d["provider_status"] = "INTERNAL_INITIALIZED"
            d["evidence_freshness"] = "2026-BASELINE"
        top5.append(d)
    return {"status": "success", "count": len(top5), "top5": top5}

@router.get("/api/v1/opportunities/{opp_id}/dossier")
def get_opportunity_dossier(opp_id: str):
    conn = get_db()
    cur = conn.cursor()
    opp = cur.execute("SELECT * FROM market_opportunities WHERE id = ?", (opp_id,)).fetchone()
    conn.close()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    d = dict(opp)
    if not d.get("source_type"):
        d["source_type"] = "SEEDED / INTERNAL"
        d["confidence_score"] = 100.0
        d["evidence_freshness"] = "2026-BASELINE"
    return {"status": "success", "dossier": d}

@router.post("/api/v1/governance/decide")
def apply_governance_decision(req: GovernanceDecisionRequest):
    conn = get_db()
    cur = conn.cursor()
    opp = cur.execute("SELECT * FROM market_opportunities WHERE id = ?", (req.opportunity_id,)).fetchone()
    if not opp:
        conn.close()
        raise HTTPException(status_code=404, detail="Opportunity not found")
    tgt = "APPROVED" if req.decision.upper() == "APPROVE" else ("REJECTED" if req.decision.upper() == "REJECT" else "SAVED_FOR_LATER")
    now = datetime.datetime.utcnow().isoformat()
    cur.execute("UPDATE market_opportunities SET status = ?, updated_at = ? WHERE id = ?", (tgt, now, req.opportunity_id))
    cur.execute("CREATE TABLE IF NOT EXISTS governance_audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, opportunity_id TEXT, previous_status TEXT, new_status TEXT, reason TEXT, decided_at TEXT)")
    cur.execute("INSERT INTO governance_audit_log (opportunity_id, previous_status, new_status, reason, decided_at) VALUES (?, ?, ?, ?, ?)", (req.opportunity_id, opp["status"], tgt, req.reason, now))
    conn.commit()
    conn.close()
    pipeline_result = execute_full_pipeline_cycle(req.opportunity_id) if tgt == "APPROVED" else None
    return {"status": "success", "opportunity_id": req.opportunity_id, "new_status": tgt, "pipeline_triggered": tgt == "APPROVED", "pipeline_result": pipeline_result}

@router.get("/admin/dashboard", response_class=HTMLResponse)
def get_control_center_dashboard():
    conn = get_db()
    cur = conn.cursor()
    rows = cur.execute("SELECT * FROM market_opportunities WHERE status NOT IN ('REJECTED') ORDER BY opportunity_score DESC LIMIT 5").fetchall()
    pc = len(cur.execute("SELECT id FROM products WHERE status IN ('ACTIVE', 'PUBLISHED')").fetchall())
    conn.close()
    cards = ""
    for o in rows:
        src = o["source_type"] or "SEEDED / INTERNAL"
        conf = o["confidence_score"] if o["confidence_score"] is not None else 100
        cards += f"<div style='padding:16px; background:#1e293b; margin-bottom:12px; border-radius:8px;'><h3><b>{o['title']}</b> - Score: {o['opportunity_score']} <span style='font-size:12px; color:#38bdf8; background:#0f172a; padding:2px 8px; border-radius:4px;'>[{src} | Conf: {conf}%]</span></h3><p>Niche: {o['niche']} | Country: {o['country']}</p><div id='dossier-{o['id']}' style='display:none; background:#0f172a; padding:10px; margin:10px 0; border-radius:4px; font-size:13px; color:#94a3b8;'><p><b>Problem:</b> {o['problem_statement']}</p><p><b>Target:</b> {o['target_audience']} | <b>Freshness:</b> {o['evidence_freshness'] or 'N/A'}</p></div><div><button onclick=\"document.getElementById('dossier-{o['id']}').style.display='block'\" style='background:#3b82f6; color:white; border:none; padding:6px 12px; cursor:pointer; margin-right:8px; border-radius:4px;'>VIEW DOSSIER</button><button onclick=\"fetch('/api/v1/governance/decide', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{opportunity_id: '{o['id']}', decision: 'APPROVE'}})}}).then(r=>r.json()).then(d=>alert('Approved & Triggered Pipeline!'))\" style='background:#10b981; color:white; border:none; padding:6px 12px; cursor:pointer; margin-right:8px; border-radius:4px;'>APPROVE</button><button style='background:#ef4444; color:white; border:none; padding:6px 12px; cursor:pointer; margin-right:8px; border-radius:4px;'>REJECT</button><button style='background:#f59e0b; color:white; border:none; padding:6px 12px; cursor:pointer; border-radius:4px;'>SAVE</button></div></div>"
    return f"<!doctype html><html><body style='background:#0f172a; color:white; padding:20px; font-family:sans-serif;'><h1>GLOBAL OPPORTUNITY CONTROL CENTER</h1><p>Active Products: {pc} | Target Jurisdictions: 197</p>{cards}</body></html>"
