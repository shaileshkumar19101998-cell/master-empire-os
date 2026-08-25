import json
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.engine import Engine

from opportunity_engine import generate_market_opportunities
from seo_engine import generate_seo_metadata
from idea_governance import validate_state_transition

phase3_router = APIRouter(prefix="/api/phase3", tags=["Phase 3: Opportunities & Governance"])

def init_phase3_tables(engine: Engine):
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS market_opportunities (
                id VARCHAR(64) PRIMARY KEY,
                niche VARCHAR(120),
                country VARCHAR(50),
                title VARCHAR(255),
                target_audience TEXT,
                problem_statement TEXT,
                demand_score NUMERIC,
                competition_score NUMERIC,
                monetization_score NUMERIC,
                opportunity_score NUMERIC,
                suggested_price NUMERIC,
                suggested_format VARCHAR(50),
                status VARCHAR(50) DEFAULT 'DISCOVERED',
                evidence_data TEXT,
                risk_level VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS seo_records (
                id SERIAL PRIMARY KEY,
                opportunity_id VARCHAR(64) REFERENCES market_opportunities(id),
                primary_keyword VARCHAR(255),
                secondary_keywords TEXT,
                long_tail_keywords TEXT,
                search_intent VARCHAR(50),
                meta_title VARCHAR(255),
                meta_description TEXT,
                slug VARCHAR(255),
                structured_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS governance_audit_log (
                id SERIAL PRIMARY KEY,
                opportunity_id VARCHAR(64),
                action VARCHAR(64),
                actor VARCHAR(64),
                previous_state VARCHAR(50),
                new_state VARCHAR(50),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))

class TransitionStateRequest(BaseModel):
    opportunity_id: str
    target_state: str
    actor: str = "SYSTEM"

def setup_phase3_routes(engine: Engine) -> APIRouter:
    init_phase3_tables(engine)

    @phase3_router.post("/opportunities/discover")
    def run_discovery():
        opps = generate_market_opportunities()
        with engine.begin() as conn:
            for opp in opps:
                conn.execute(text("""
                    INSERT INTO market_opportunities (
                        id, niche, country, title, target_audience, problem_statement,
                        demand_score, competition_score, monetization_score, opportunity_score,
                        suggested_price, suggested_format, status, evidence_data, risk_level, updated_at
                    ) VALUES (
                        :id, :niche, :country, :title, :target_audience, :problem_statement,
                        :demand_score, :competition_score, :monetization_score, :opportunity_score,
                        :suggested_price, :suggested_format, :status, :evidence_data, :risk_level, CURRENT_TIMESTAMP
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        demand_score = EXCLUDED.demand_score,
                        competition_score = EXCLUDED.competition_score,
                        monetization_score = EXCLUDED.monetization_score,
                        opportunity_score = EXCLUDED.opportunity_score,
                        evidence_data = EXCLUDED.evidence_data,
                        updated_at = CURRENT_TIMESTAMP;
                """), opp)

                seo = generate_seo_metadata(opp)
                existing_seo = conn.execute(
                    text("SELECT id FROM seo_records WHERE opportunity_id = :oid"),
                    {"oid": opp["id"]}
                ).mappings().first()

                if not existing_seo:
                    conn.execute(text("""
                        INSERT INTO seo_records (
                            opportunity_id, primary_keyword, secondary_keywords, long_tail_keywords,
                            search_intent, meta_title, meta_description, slug, structured_data
                        ) VALUES (
                            :oid, :pk, :sk, :ltk, :si, :mt, :md, :slug, :sd
                        )
                    """), {
                        "oid": opp["id"],
                        "pk": seo["primary_keyword"],
                        "sk": seo["secondary_keywords"],
                        "ltk": seo["long_tail_keywords"],
                        "si": seo["search_intent"],
                        "mt": seo["meta_title"],
                        "md": seo["meta_description"],
                        "slug": seo["slug"],
                        "sd": json.dumps(seo["structured_data"])
                    })

        return {
            "status": "SUCCESS",
            "source_type": "HEURISTIC_SEED",
            "confidence": "BASELINE",
            "discovered_count": len(opps)
        }

    @phase3_router.get("/opportunities/top5")
    def get_top5_opportunities():
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT 
                    m.id, m.niche, m.country, m.title, m.target_audience, m.problem_statement,
                    m.demand_score, m.competition_score, m.monetization_score, m.opportunity_score,
                    m.suggested_price, m.suggested_format, m.status, m.risk_level, m.evidence_data,
                    s.primary_keyword, s.slug, s.meta_title, s.meta_description, s.structured_data
                FROM market_opportunities m
                LEFT JOIN seo_records s ON m.id = s.opportunity_id
                ORDER BY m.opportunity_score DESC, m.updated_at DESC, m.id ASC
                LIMIT 5
            """)).mappings().all()

        if not rows:
            return {
                "status": "SUCCESS",
                "message": "No opportunities discovered yet. Run POST /api/phase3/opportunities/discover first.",
                "data_source": "HEURISTIC_SEED",
                "confidence": "BASELINE",
                "top_5": []
            }

        parsed_rows = []
        for r in rows:
            d = dict(r)
            if d.get("evidence_data"):
                try:
                    d["evidence_data"] = json.loads(d["evidence_data"])
                except Exception:
                    pass
            if d.get("structured_data"):
                try:
                    d["structured_data"] = json.loads(d["structured_data"])
                except Exception:
                    pass
            parsed_rows.append(d)

        return {
            "status": "SUCCESS",
            "data_source": "HEURISTIC_SEED",
            "confidence": "BASELINE",
            "top_5": parsed_rows
        }

    @phase3_router.post("/governance/transition")
    def transition_opportunity_state(
        req: TransitionStateRequest,
        x_governance_key: Optional[str] = Header(default="")
    ):
        with engine.connect() as conn:
            opp = conn.execute(
                text("SELECT id, status FROM market_opportunities WHERE id = :id"),
                {"id": req.opportunity_id}
            ).mappings().first()

        if not opp:
            raise HTTPException(status_code=404, detail="Opportunity not found.")

        current_state = opp["status"]
        validation = validate_state_transition(
            current_state=current_state,
            target_state=req.target_state,
            autonomy_level=2,
            actor=req.actor,
            governance_key=x_governance_key or ""
        )

        if not validation["allowed"]:
            raise HTTPException(status_code=validation["error_code"], detail=validation["message"])

        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE market_opportunities 
                SET status = :nstate, updated_at = CURRENT_TIMESTAMP 
                WHERE id = :id
            """), {"nstate": req.target_state, "id": req.opportunity_id})

            conn.execute(text("""
                INSERT INTO governance_audit_log (opportunity_id, action, actor, previous_state, new_state)
                VALUES (:oid, 'STATE_TRANSITION', :actor, :pstate, :nstate)
            """), {
                "oid": req.opportunity_id,
                "actor": req.actor,
                "pstate": current_state,
                "nstate": req.target_state
            })

        return {
            "status": "SUCCESS",
            "opportunity_id": req.opportunity_id,
            "previous_state": current_state,
            "new_state": req.target_state,
            "authorized_by": req.actor
        }

    return phase3_router