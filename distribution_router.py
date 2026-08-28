from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import distribution_orchestrator
import distribution_connectors

router = APIRouter(prefix="/api/v1/distribution", tags=["distribution"])

OPERATOR_SECRET_KEY = os.getenv("OPERATOR_MASTER_SECRET", "LEAD_OPERATOR_AUTH_TOKEN_7788")

class ProposalStageRequest(BaseModel):
    product_id: str

class ProposalApproveRequest(BaseModel):
    proposal_id: str
    operator_identity: str

class DispatchRequest(BaseModel):
    proposal_id: str
    operator_identity: str
    dry_run: Optional[bool] = True

def verify_operator_auth(x_operator_secret: Optional[str]):
    if not x_operator_secret or x_operator_secret != OPERATOR_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized: Invalid or missing operator authorization credentials.")
    return True

@router.get("/connectors/status")
def get_connectors_status():
    statuses = [conn.validate_credentials() for conn in distribution_connectors.CONNECTOR_REGISTRY.values()]
    return {"status": "success", "connectors": statuses}

@router.post("/stage")
def stage_product_distribution(req: ProposalStageRequest, x_operator_secret: Optional[str] = Header(default=None, alias="x-operator-secret")):
    verify_operator_auth(x_operator_secret)
    try:
        proposals = distribution_orchestrator.orchestrator.stage_channel_proposals(req.product_id)
        return {"status": "success", "proposals_count": len(proposals), "proposals": proposals}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/approve")
def approve_distribution_proposal(req: ProposalApproveRequest, x_operator_secret: Optional[str] = Header(default=None, alias="x-operator-secret")):
    verify_operator_auth(x_operator_secret)
    try:
        res = distribution_orchestrator.orchestrator.approve_proposal(req.proposal_id, req.operator_identity)
        return {"status": "success", "approval": res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/dispatch")
def execute_distribution_dispatch(req: DispatchRequest, x_operator_secret: Optional[str] = Header(default=None, alias="x-operator-secret")):
    verify_operator_auth(x_operator_secret)
    try:
        res = distribution_orchestrator.orchestrator.execute_dispatch(req.proposal_id, req.operator_identity, dry_run=req.dry_run)
        return {"status": "success", "dispatch_result": res}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))