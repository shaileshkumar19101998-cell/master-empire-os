import uuid
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
import market_intelligence_provider

router = APIRouter(prefix="/api/v1/opportunities", tags=["opportunities"])

class DiscoverRequest(BaseModel):
    niche: str
    country_code: Optional[str] = "US"
    language_code: Optional[str] = "en"

SEEDED_TOP5 = [
    {
        "opportunity_id": "seed-001",
        "title": "Autonomous Remote Consulting OS",
        "niche": "remote consulting",
        "source_type": "INTERNAL_DEVELOPMENT_FIXTURE",
        "opportunity_score": 97,
        "is_seeded": True
    },
    {
        "opportunity_id": "seed-002",
        "title": "AI Career Blueprint 2026",
        "niche": "ai careers",
        "source_type": "INTERNAL_DEVELOPMENT_FIXTURE",
        "opportunity_score": 96,
        "is_seeded": True
    },
    {
        "opportunity_id": "seed-003",
        "title": "Zero-Debt Wealth Engine",
        "niche": "personal finance",
        "source_type": "INTERNAL_DEVELOPMENT_FIXTURE",
        "opportunity_score": 94,
        "is_seeded": True
    }
]

@router.post("/discover")
def discover_opportunity(req: DiscoverRequest):
    signals = market_intelligence_provider.registry.fetch_unified_signals(
        keyword=req.niche,
        country_code=req.country_code,
        language_code=req.language_code
    )
    
    if signals["source_type"] == "LIVE_EXTERNAL_SIGNAL":
        return {
            "status": "success",
            "opportunity_id": f"opp-{uuid.uuid4().hex[:8]}",
            "market_signals": signals,
            "live_score": signals.get("confidence_score"),
            "source_type": "LIVE_EXTERNAL_SIGNAL"
        }
    else:
        return {
            "status": "zero_state",
            "opportunity_id": None,
            "market_signals": signals,
            "live_score": None,
            "source_type": "EXTERNAL_DATA_UNAVAILABLE"
        }

@router.get("/top5")
def get_top5_opportunities():
    prov = market_intelligence_provider.registry.get_active_provider()
    status = prov.get_status()
    if status.get("auth_configured"):
        return {
            "status": "success",
            "source_type": "LIVE_EXTERNAL_SIGNAL",
            "top5": []
        }
    return {
        "status": "success",
        "source_type": "INTERNAL_DEVELOPMENT_FIXTURE",
        "note": "Live market intelligence connector not configured. Presenting development fixtures.",
        "top5": SEEDED_TOP5
    }