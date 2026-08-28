import hashlib
from typing import Dict, Any, List, Optional

class OpportunityEngine:
    FORMULA_VERSION = "SERP_V1_DETERMINISTIC"

    @staticmethod
    def calculate_serp_opportunity_score(market_signals: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not market_signals or market_signals.get("source_type") != "LIVE_EXTERNAL_SIGNAL":
            return None

        evidence_str = market_signals.get("evidence_source", "")
        organic_count = 0
        paa_count = 0
        related_count = 0

        try:
            if "Organic:" in evidence_str:
                parts = evidence_str.split("Organic:")[1].split(",")
                organic_count = int(parts[0].strip())
            if "PAA:" in evidence_str:
                parts = evidence_str.split("PAA:")[1].split(",")
                paa_count = int(parts[0].strip())
            if "Related:" in evidence_str:
                parts = evidence_str.split("Related:")[1].replace(")", "").strip()
                related_count = int(parts)
        except Exception:
            pass

        is_commercial = market_signals.get("search_intent") == "commercial"

        paa_score = min(paa_count * 6.0, 30.0)
        related_score = min(related_count * 3.75, 30.0)
        organic_score = min(organic_count * 2.0, 20.0)
        intent_score = 20.0 if is_commercial else 10.0

        raw_total = paa_score + related_score + organic_score + intent_score
        live_serp_score = round(min(raw_total, 100.0), 2)

        provenance = {
            "score_type": "LIVE_SERP_OPPORTUNITY_SCORE",
            "score_semantics": "Opportunity characteristics derived from SERP coverage, PAA depth, and related breadth. NOT verified search volume or revenue guarantee.",
            "formula_version": OpportunityEngine.FORMULA_VERSION,
            "raw_inputs": {
                "organic_count": organic_count,
                "paa_count": paa_count,
                "related_count": related_count,
                "is_commercial": is_commercial
            },
            "sub_scores": {
                "paa_score": paa_score,
                "related_score": related_score,
                "organic_score": organic_score,
                "intent_score": intent_score
            },
            "live_serp_opportunity_score": live_serp_score
        }
        return provenance

    @staticmethod
    def rank_live_opportunities(signals_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        ranked = []
        for sig in signals_list:
            if sig.get("source_type") == "LIVE_EXTERNAL_SIGNAL":
                prov = OpportunityEngine.calculate_serp_opportunity_score(sig)
                if prov:
                    kw = sig.get("keyword", "unknown")
                    tie_breaker = hashlib.sha256(kw.encode("utf-8")).hexdigest()[:6]
                    ranked.append({
                        "opportunity_id": f"live-opp-{tie_breaker}",
                        "title": f"{kw.title()} Strategy & Execution Manual",
                        "keyword": kw,
                        "country_code": sig.get("country_code"),
                        "language_code": sig.get("language_code"),
                        "source_type": "LIVE_EXTERNAL_SIGNAL",
                        "live_serp_opportunity_score": prov["live_serp_opportunity_score"],
                        "score_provenance": prov,
                        "market_signals": sig,
                        "governance_status": "PROPOSED_IDEA",
                        "search_volume_monthly": None,
                        "cpc_value_usd": None,
                        "competition_density": None
                    })

        ranked.sort(key=lambda x: (-x["live_serp_opportunity_score"], x["opportunity_id"]))
        return ranked[:5]

engine = OpportunityEngine()