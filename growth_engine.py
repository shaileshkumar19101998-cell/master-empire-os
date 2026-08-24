import os
import hashlib
import json
import re
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import create_engine, text

import ai_engine

def get_db_engine():
    db_url = os.getenv("DATABASE_URL", "sqlite:///./autonomous_local.db")
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    if "sqlite" in db_url:
        return create_engine(db_url, connect_args={"check_same_thread": False})
    return create_engine(db_url, pool_pre_ping=True)

# ==================== 1. REVENUE ANALYTICS ENGINE ====================

def calculate_revenue_metrics(engine=None) -> Dict[str, Any]:
    """Deterministic server-side analytics using Decimal / integer minor units."""
    if engine is None:
        engine = get_db_engine()

    with engine.connect() as conn:
        # 1. Orders aggregation
        order_rows = conn.execute(
            text("SELECT count(*) as total_orders, sum(CASE WHEN status = 'PAID' THEN 1 ELSE 0 END) as paid_orders FROM orders")
        ).mappings().first()
        total_orders = int(order_rows["total_orders"] or 0)
        paid_orders = int(order_rows["paid_orders"] or 0)

        # 2. Revenue Ledger aggregation
        ledger_rows = conn.execute(
            text("SELECT sum(gross_amount) as gross, sum(gateway_fee) as fee, sum(net_revenue) as net FROM revenue_ledger")
        ).mappings().first()
        
        gross_rev = Decimal(str(ledger_rows["gross"] or "0.00"))
        gateway_fees = Decimal(str(ledger_rows["fee"] or "0.00"))
        net_rev = Decimal(str(ledger_rows["net"] or "0.00"))

        # 3. Average Order Value (AOV)
        if paid_orders > 0:
            aov = (gross_rev / Decimal(str(paid_orders))).quantize(Decimal("0.01"))
        else:
            aov = Decimal("0.00")

        # 4. Product-wise Performance
        product_stats = []
        p_rows = conn.execute(text("""
            SELECT p.id, p.slug, p.title, p.base_price_inr,
                   count(o.id) as order_count,
                   sum(CASE WHEN o.status = 'PAID' THEN o.net_amount ELSE 0 END) as total_collected
            FROM products p
            LEFT JOIN orders o ON p.id = o.product_id
            GROUP BY p.id, p.slug, p.title, p.base_price_inr
        """)).mappings().all()

        for pr in p_rows:
            product_stats.append({
                "product_id": pr["id"],
                "slug": pr["slug"],
                "title": pr["title"],
                "price_inr": int(pr["base_price_inr"] or 0),
                "orders": int(pr["order_count"] or 0),
                "revenue_inr": str(Decimal(str(pr["total_collected"] or "0.00")).quantize(Decimal("0.01")))
            })

    return {
        "total_orders": total_orders,
        "paid_orders": paid_orders,
        "gross_revenue": str(gross_rev.quantize(Decimal("0.01"))),
        "gateway_fees": str(gateway_fees.quantize(Decimal("0.01"))),
        "net_revenue": str(net_rev.quantize(Decimal("0.01"))),
        "average_order_value": str(aov),
        "product_breakdown": product_stats,
        "conversion_rate": f"{(paid_orders / total_orders * 100):.2f}%" if total_orders > 0 else "0.00%"
    }

# ==================== 2. MARKET OPPORTUNITY SCORING ====================

def calculate_opportunity_score(
    demand_index: int,           # 0 - 100
    competition_index: int,      # 0 - 100 (Lower competition = higher score)
    commercial_intent_index: int,# 0 - 100
    content_gap_index: int       # 0 - 100
) -> Dict[str, Any]:
    """Deterministic opportunity score calculation (0–100 scale)."""
    # Clamp inputs between 0 and 100
    d = max(0, min(100, demand_index))
    c = max(0, min(100, competition_index))
    ci = max(0, min(100, commercial_intent_index))
    cg = max(0, min(100, content_gap_index))

    # Deterministic formula: 35% Demand + 25% Low Competition + 25% Commercial Intent + 15% Content Gap
    comp_advantage = 100 - c
    raw_score = (d * Decimal("0.35")) + (comp_advantage * Decimal("0.25")) + (ci * Decimal("0.25")) + (cg * Decimal("0.15"))
    final_score = int(round(raw_score))

    grade = "A+" if final_score >= 85 else ("A" if final_score >= 70 else ("B" if final_score >= 50 else "C"))

    return {
        "opportunity_score": final_score,
        "grade": grade,
        "metrics": {
            "demand": d,
            "competition": c,
            "commercial_intent": ci,
            "content_gap": cg
        },
        "verdict": "HIGH_POTENTIAL" if final_score >= 70 else "MODERATE_POTENTIAL"
    }

# ==================== 3. AI GROWTH RECOMMENDATIONS & COST CONTROL ====================

def check_ai_research_limits(topic: str, engine=None) -> Dict[str, Any]:
    """Ensure max 5 daily research jobs and block duplicate topic evaluations."""
    if engine is None:
        engine = get_db_engine()

    clean_topic = ai_engine.sanitize_input(topic).lower()
    topic_hash = hashlib.sha256(clean_topic.encode("utf-8")).hexdigest()[:16]
    max_daily = int(os.getenv("MAX_DAILY_AI_RESEARCH_JOBS", "5"))

    with engine.connect() as conn:
        # Check daily usage from system_logs
        since_t = datetime.utcnow() - timedelta(days=1)
        daily_count = conn.execute(text("""
            SELECT count(*) FROM system_logs 
            WHERE module = 'AI_RESEARCH' AND status = 'EXECUTED' AND created_at >= :t
        """), {"t": since_t}).scalar() or 0

        if daily_count >= max_daily:
            return {"allowed": False, "reason": "RATE_LIMIT_REACHED", "daily_count": daily_count}

        # Check duplicate topic research
        duplicate = conn.execute(text("""
            SELECT id FROM system_logs 
            WHERE module = 'AI_RESEARCH' AND message LIKE :thash
        """), {"thash": f"%[hash:{topic_hash}]%"}).first()

        if duplicate:
            return {"allowed": False, "reason": "DUPLICATE_TOPIC", "topic_hash": topic_hash}

    return {"allowed": True, "topic_hash": topic_hash}

def generate_growth_recommendations(topic: str, target_niche: str, engine=None) -> Dict[str, Any]:
    """Structured growth recommendation generation with Level 2 Autonomy enforcement."""
    if engine is None:
        engine = get_db_engine()

    clean_topic = ai_engine.sanitize_input(topic)
    clean_niche = ai_engine.sanitize_input(target_niche)

    limit_check = check_ai_research_limits(clean_topic, engine)
    if not limit_check["allowed"]:
        return {
            "status": "BLOCKED",
            "reason": limit_check["reason"],
            "recommendation": None
        }

    # Autonomy Guard (Default Level 2)
    autonomy_level = int(os.getenv("AUTONOMY_LEVEL", "2"))

    # Generate Structured Blueprint
    rec_payload = {
        "topic": clean_topic,
        "niche": clean_niche,
        "suggested_title": f"Complete Guide to {clean_topic}",
        "suggested_tier": "Tier 1",
        "seo_keywords": [clean_topic.lower(), f"{clean_niche.lower()} automation", "enterprise systems"],
        "content_angle": "Technical implementation & architectural blueprints",
        "action_required": "STAGE_PENDING_APPROVAL"
    }

    topic_hash = limit_check["topic_hash"]
    
    # Audit log
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO system_logs (module, status, message)
            VALUES ('AI_RESEARCH', 'EXECUTED', :msg)
        """), {"msg": f"Researched topic: {clean_topic} [hash:{topic_hash}]"})

        # Level 2 Autonomy Guard: Recommendations must be staged, financial actions never autonomous
        if autonomy_level == 2:
            conn.execute(text("""
                INSERT INTO pending_approvals (book_id, status)
                VALUES (0, 'RECOMMENDATION_PENDING')
            """))

    return {
        "status": "SUCCESS",
        "autonomy_level": autonomy_level,
        "staged_for_approval": autonomy_level == 2,
        "data": rec_payload
    }