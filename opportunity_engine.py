import hashlib
import json
from typing import List, Dict, Any

WEIGHT_DEMAND = 0.30
WEIGHT_VELOCITY = 0.20
WEIGHT_MONETIZATION = 0.25
WEIGHT_SEO_GAP = 0.15
WEIGHT_COMPETITION = 0.10

SEED_OPPORTUNITIES = [
    {
        "niche": "Cloud & DevOps Architecture",
        "country": "USA",
        "title": "Zero-Downtime Multi-Region Kubernetes & Infrastructure Handbook",
        "target_audience": "Senior DevOps Engineers, Cloud Architects, Technical Leads",
        "problem_statement": "Deploying cross-region resilient clusters with state replication without incurring catastrophic multi-cloud egress costs.",
        "demand_score": 92.0,
        "velocity_score": 88.0,
        "monetization_score": 95.0,
        "seo_gap_score": 82.0,
        "competition_score": 45.0,
        "suggested_price": 29.0,
        "suggested_format": "PDF + Interactive Checklists",
        "risk_level": "LOW",
        "recommended_action": "PRIORITIZE_FOR_HUMAN_REVIEW"
    },
    {
        "niche": "AI Application Engineering",
        "country": "India",
        "title": "Autonomous RAG Systems with Local Vector Databases Architecture Guide",
        "target_audience": "Full-Stack AI Developers, Enterprise Tech Leads in Tier-1 Tech Hubs",
        "problem_statement": "Preventing retrieval hallucination and high LLM API latency in production enterprise search setups.",
        "demand_score": 96.0,
        "velocity_score": 94.0,
        "monetization_score": 89.0,
        "seo_gap_score": 91.0,
        "competition_score": 38.0,
        "suggested_price": 499.0,
        "suggested_format": "E-Book + Code Repositories",
        "risk_level": "LOW",
        "recommended_action": "PRIORITIZE_FOR_HUMAN_REVIEW"
    },
    {
        "niche": "Personal Finance & Solopreneurship",
        "country": "UK",
        "title": "UK Solopreneur & Micro-SaaS VAT / Corporation Tax Optimization Playbook",
        "target_audience": "Freelancers, Agency Owners, Digital Nomads in the UK",
        "problem_statement": "Navigating modern digital sales tax, Cross-border VAT exemptions, and allowable business deductions legally.",
        "demand_score": 84.0,
        "velocity_score": 79.0,
        "monetization_score": 92.0,
        "seo_gap_score": 78.0,
        "competition_score": 42.0,
        "suggested_price": 24.0,
        "suggested_format": "PDF + Spreadsheet Templates",
        "risk_level": "MEDIUM",
        "recommended_action": "QUEUE_FOR_RESEARCH"
    },
    {
        "niche": "Cybersecurity Compliance",
        "country": "Europe",
        "title": "GDPR & EU AI Act Compliance Blueprint for Early-Stage Startups",
        "target_audience": "Startup Founders, Data Protection Officers, CTOs operating in EU",
        "problem_statement": "Rapidly implementing compliant user data consent, telemetry retention, and model auditing without slowing feature velocity.",
        "demand_score": 89.0,
        "velocity_score": 92.0,
        "monetization_score": 94.0,
        "seo_gap_score": 85.0,
        "competition_score": 35.0,
        "suggested_price": 39.0,
        "suggested_format": "Handbook + Audit Matrices",
        "risk_level": "LOW",
        "recommended_action": "PRIORITIZE_FOR_HUMAN_REVIEW"
    },
    {
        "niche": "Health & Bio-Optimization",
        "country": "Australia",
        "title": "Circadian Synchronization & Evidence-Based Sleep Architecture Manual",
        "target_audience": "Shift Workers, High-Stress Executives, Endurance Athletes",
        "problem_statement": "Managing deep sleep fragmentation and recovery metrics in high-stress work patterns.",
        "demand_score": 81.0,
        "velocity_score": 83.0,
        "monetization_score": 80.0,
        "seo_gap_score": 75.0,
        "competition_score": 52.0,
        "suggested_price": 19.0,
        "suggested_format": "Illustrated PDF + Habit Trackers",
        "risk_level": "LOW",
        "recommended_action": "QUEUE_FOR_RESEARCH"
    }
]

def generate_deterministic_id(niche: str, country: str, title: str) -> str:
    raw_key = f"{niche.strip().lower()}:{country.strip().lower()}:{title.strip().lower()}"
    return f"opp_{hashlib.sha256(raw_key.encode('utf-8')).hexdigest()[:12]}"

def validate_and_clamp_score(score: float) -> float:
    try:
        val = float(score)
        return max(0.0, min(100.0, val))
    except (ValueError, TypeError):
        return 0.0

def calculate_opportunity_score(
    demand: float,
    velocity: float,
    monetization: float,
    seo_gap: float,
    competition: float
) -> float:
    d = validate_and_clamp_score(demand)
    v = validate_and_clamp_score(velocity)
    m = validate_and_clamp_score(monetization)
    sg = validate_and_clamp_score(seo_gap)
    c = validate_and_clamp_score(competition)

    raw_score = (
        (d * WEIGHT_DEMAND) +
        (v * WEIGHT_VELOCITY) +
        (m * WEIGHT_MONETIZATION) +
        (sg * WEIGHT_SEO_GAP) -
        (c * WEIGHT_COMPETITION)
    )
    return round(max(0.0, min(100.0, raw_score)), 2)

def generate_market_opportunities() -> List[Dict[str, Any]]:
    opportunities = []
    for item in SEED_OPPORTUNITIES:
        opp_id = generate_deterministic_id(item["niche"], item["country"], item["title"])
        score = calculate_opportunity_score(
            demand=item["demand_score"],
            velocity=item["velocity_score"],
            monetization=item["monetization_score"],
            seo_gap=item["seo_gap_score"],
            competition=item["competition_score"]
        )

        evidence = {
            "source_type": "HEURISTIC_SEED",
            "confidence": "BASELINE",
            "signals": ["Google Trends Regional Heuristic", "Search Query Seed Analysis", "Community Problem Frequency"],
            "velocity_score": item["velocity_score"],
            "seo_gap_score": item["seo_gap_score"]
        }

        opportunities.append({
            "id": opp_id,
            "niche": item["niche"],
            "country": item["country"],
            "title": item["title"],
            "target_audience": item["target_audience"],
            "problem_statement": item["problem_statement"],
            "demand_score": item["demand_score"],
            "competition_score": item["competition_score"],
            "monetization_score": item["monetization_score"],
            "opportunity_score": score,
            "suggested_price": item["suggested_price"],
            "suggested_format": item["suggested_format"],
            "status": "DISCOVERED",
            "evidence_data": json.dumps(evidence),
            "risk_level": item["risk_level"],
            "recommended_action": item["recommended_action"]
        })

    opportunities.sort(key=lambda x: (x["opportunity_score"], x["id"]), reverse=True)
    return opportunities