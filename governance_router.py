import time
import sqlite3
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

import product_synthesis_engine
import qa_engine

router = APIRouter(prefix="/governance", tags=["governance"])
DB_PATH = "autonomous_local.db"

class GovernanceDecisionRequest(BaseModel):
    opportunity_id: str
    decision: str  # "APPROVE", "REJECT"
    operator: Optional[str] = "ADMIN_OPERATOR"
    opportunity_payload: Optional[Dict[str, Any]] = None

@router.post("/decision")
def record_governance_decision(req: GovernanceDecisionRequest):
    if req.decision not in ["APPROVE", "REJECT"]:
        raise HTTPException(status_code=400, detail="Decision must be APPROVE or REJECT")

    now = time.time()
    action = f"DECISION_{req.decision}"
    prev_state = "PROPOSED_IDEA"
    new_state = "APPROVED" if req.decision == "APPROVE" else "REJECTED"
    reason = f"Governance decision by {req.operator}"

    # Insert into governance_audit_log matching exact schema
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO governance_audit_log 
        (opportunity_id, action, actor, previous_state, new_state, timestamp, previous_status, new_status, reason, decided_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (req.opportunity_id, action, req.operator, prev_state, new_state, now, prev_state, new_state, reason, now))
    conn.commit()
    conn.close()

    if req.decision == "APPROVE" and req.opportunity_payload:
        blueprint = product_synthesis_engine.synthesis_engine.generate_blueprint(req.opportunity_payload)
        artifact = product_synthesis_engine.synthesis_engine.synthesize_product(blueprint)
        qa_result = qa_engine.qa_engine.evaluate_product(artifact)
        return {
            "status": "success",
            "opportunity_id": req.opportunity_id,
            "governance_decision": "APPROVED",
            "synthesis_job_id": artifact["product_job_id"],
            "qa_result": qa_result,
            "final_status": qa_result["governance_status"]  # READY_FOR_CATALOG
        }

    return {
        "status": "success",
        "opportunity_id": req.opportunity_id,
        "governance_decision": req.decision,
        "final_status": new_state
    }

@router.post("/synthesize-gate")
def attempt_synthesis_gate(req: Dict[str, Any]):
    gov_status = req.get("governance_status")
    if gov_status != "APPROVED":
        raise HTTPException(
            status_code=403, 
            detail=f"Governance Violation: Cannot synthesize opportunity in state '{gov_status}'. Explicit human APPROVAL required."
        )
    
    blueprint = product_synthesis_engine.synthesis_engine.generate_blueprint(req)
    artifact = product_synthesis_engine.synthesis_engine.synthesize_product(blueprint)
    qa_result = qa_engine.qa_engine.evaluate_product(artifact)
    return {"status": "success", "artifact": artifact, "qa_result": qa_result}