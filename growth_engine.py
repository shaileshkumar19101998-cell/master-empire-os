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

# ==================== 1. REVENUE & BUSINESS TELEMETRY ====================

def calculate_revenue_metrics(engine=None) -> Dict[str, Any]:
    """Deterministic server-side analytics using Decimal / integer minor units."""
    if engine is None:
        engine = get_db_engine()

    with engine.connect() as conn:
        order_rows = conn.execute(
            text("SELECT count(*) as total_orders, sum(CASE WHEN status = 'PAID' THEN 1 ELSE 0 END) as paid_orders FROM orders")
        ).mappings().first()
        total_orders = int(order_rows["total_orders"] or 0)
        paid_orders = int(order_rows["paid_orders"] or 0)

        ledger_rows = conn.execute(
            text("SELECT sum(gross_amount) as gross, sum(gateway_fee) as fee, sum(net_revenue) as net FROM revenue_ledger")
        ).mappings().first()
        
        gross_rev = Decimal(str(ledger_rows["gross"] or "0.00"))
        gateway_fees = Decimal(str(ledger_rows["fee"] or "0.00"))
        net_rev = Decimal(str(ledger_rows["net"] or "0.00"))

        aov = (gross_rev / Decimal(str(paid_orders))).quantize(Decimal("0.01")) if paid_orders > 0 else Decimal("0.00")

        # Product-wise Breakdown
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

        # Customer Intelligence
        cust_rows = conn.execute(text("""
            SELECT count(DISTINCT customer_id) as total_customers,
                   sum(CASE WHEN order_count > 1 THEN 1 ELSE 0 END) as repeat_customers
            FROM (SELECT customer_id, count(id) as order_count FROM orders GROUP BY customer_id)
        """)).mappings().first()
        total_cust = int(cust_rows["total_customers"] or 0) if cust_rows else 0
        repeat_cust = int(cust_rows["repeat_customers"] or 0) if cust_rows else 0
        new_cust = max(0, total_cust - repeat_cust)

        health_score = 98 if paid_orders > 0 and gross_rev > 0 else 85
        conv_rate = f"{(paid_orders / total_orders * 100):.1f}%" if total_orders > 0 else "0.0%"

    return {
        "total_orders": total_orders,
        "paid_orders": paid_orders,
        "gross_revenue": str(gross_rev.quantize(Decimal("0.01"))),
        "gateway_fees": str(gateway_fees.quantize(Decimal("0.01"))),
        "net_revenue": str(net_rev.quantize(Decimal("0.01"))),
        "average_order_value": str(aov),
        "conversion_rate": conv_rate,
        "product_breakdown": product_stats,
        "customer_intel": {
            "total_customers": total_cust,
            "new_customers": new_cust,
            "repeat_customers": repeat_cust,
            "repeat_ratio": f"{(repeat_cust / total_cust * 100):.1f}%" if total_cust > 0 else "0.0%"
        },
        "health_score": health_score
    }

# ==================== 2. PIPELINE & TELEMETRY AGGREGATION ====================

def get_command_center_telemetry(engine=None) -> Dict[str, Any]:
    """Single batched query aggregator for the Ultra-Premium Command Center."""
    if engine is None:
        engine = get_db_engine()

    metrics = calculate_revenue_metrics(engine)

    with engine.connect() as conn:
        pending_items = conn.execute(text("""
            SELECT pa.id, pa.book_id, pa.status, pa.created_at, b.title, b.target_niche, b.slug
            FROM pending_approvals pa
            LEFT JOIN books b ON pa.book_id = b.id
            WHERE pa.status = 'PENDING'
            ORDER BY pa.id DESC LIMIT 10
        """)).mappings().all()

        pipeline_rows = conn.execute(text("""
            SELECT status, count(*) as count FROM books GROUP BY status
        """)).mappings().all()
        pipeline_counts = {r["status"]: r["count"] for r in pipeline_rows}

        recent_txs = conn.execute(text("""
            SELECT o.id, o.customer_id, o.net_amount, o.status, o.created_at, p.title
            FROM orders o
            LEFT JOIN products p ON o.product_id = p.id
            ORDER BY o.created_at DESC LIMIT 6
        """)).mappings().all()

        audit_logs = conn.execute(text("""
            SELECT module, status, message, created_at FROM system_logs ORDER BY id DESC LIMIT 8
        """)).mappings().all()

    return {
        "metrics": metrics,
        "pending_approvals": [dict(r) for r in pending_items],
        "pipeline": {
            "DRAFT": pipeline_counts.get("DRAFT", 0),
            "PROCESSING": pipeline_counts.get("PROCESSING", 0),
            "COMPLETED": pipeline_counts.get("COMPLETED", 0),
            "PUBLISHED": pipeline_counts.get("PUBLISHED", 0),
            "FAILED": pipeline_counts.get("FAILED", 0)
        },
        "recent_transactions": [dict(r) for r in recent_txs],
        "audit_logs": [dict(r) for r in audit_logs]
    }

# ==================== 3. ADMINISTRATIVE APPROVAL / REJECTION ====================

def approve_pending_job(approval_id: int, engine=None) -> Dict[str, Any]:
    if engine is None:
        engine = get_db_engine()

    with engine.begin() as conn:
        approval = conn.execute(
            text("SELECT * FROM pending_approvals WHERE id = :id"),
            {"id": approval_id}
        ).mappings().first()

        if not approval:
            raise ValueError("Target approval record not found.")
        if approval["status"] != "PENDING":
            raise ValueError(f"Record already processed with status {approval['status']}.")

        book = conn.execute(
            text("SELECT * FROM books WHERE id = :bid"),
            {"bid": approval["book_id"]}
        ).mappings().first()

        if not book:
            raise ValueError("Associated book metadata not found.")

        conn.execute(text("""
            INSERT INTO products (slug, title, tier_level, target_niche, base_price_inr, base_price_usd, pdf_file_path, status)
            VALUES (:s, :t, 'Tier 1', :n, 999, 12, :r2_key, 'ACTIVE')
        """), {
            "s": book["slug"], "t": book["title"], "n": book["target_niche"], "r2_key": book["pdf_file_path"]
        })

        conn.execute(text("UPDATE books SET status = 'PUBLISHED' WHERE id = :bid"), {"bid": book["id"]})
        conn.execute(text("UPDATE pending_approvals SET status = 'APPROVED' WHERE id = :id"), {"id": approval_id})

        conn.execute(text("""
            INSERT INTO system_logs (module, status, message)
            VALUES ('APPROVAL_ENGINE', 'APPROVED', :msg)
        """), {"msg": f"Admin approved book {book['slug']} (ID: {book['id']}) for production catalog."})

    return {"status": "SUCCESS", "message": f"Book {book['slug']} approved and published to live catalog."}

def reject_pending_job(approval_id: int, reason: str = "Admin Rejected", engine=None) -> Dict[str, Any]:
    if engine is None:
        engine = get_db_engine()

    with engine.begin() as conn:
        approval = conn.execute(
            text("SELECT * FROM pending_approvals WHERE id = :id"),
            {"id": approval_id}
        ).mappings().first()

        if not approval:
            raise ValueError("Target approval record not found.")
        if approval["status"] != "PENDING":
            raise ValueError(f"Record already processed with status {approval['status']}.")

        conn.execute(text("UPDATE pending_approvals SET status = 'REJECTED' WHERE id = :id"), {"id": approval_id})
        conn.execute(text("UPDATE books SET status = 'FAILED', error_message = :err WHERE id = :bid"),
                     {"err": reason[:250], "bid": approval["book_id"]})

        conn.execute(text("""
            INSERT INTO system_logs (module, status, message)
            VALUES ('APPROVAL_ENGINE', 'REJECTED', :msg)
        """), {"msg": f"Admin rejected approval item ID: {approval_id}. Reason: {reason}"})

    return {"status": "SUCCESS", "message": f"Approval item ID {approval_id} rejected."}

# ==================== 4. MARKET OPPORTUNITY & RESEARCH SCORING ====================

def calculate_opportunity_score(
    demand_index: int,
    competition_index: int,
    commercial_intent_index: int,
    content_gap_index: int
) -> Dict[str, Any]:
    d = max(0, min(100, demand_index))
    c = max(0, min(100, competition_index))
    ci = max(0, min(100, commercial_intent_index))
    cg = max(0, min(100, content_gap_index))

    comp_advantage = 100 - c
    raw_score = (d * Decimal("0.35")) + (comp_advantage * Decimal("0.25")) + (ci * Decimal("0.25")) + (cg * Decimal("0.15"))
    final_score = int(round(raw_score))

    grade = "A+" if final_score >= 85 else ("A" if final_score >= 70 else ("B" if final_score >= 50 else "C"))
    return {
        "opportunity_score": final_score,
        "grade": grade,
        "metrics": {"demand": d, "competition": c, "commercial_intent": ci, "content_gap": cg},
        "verdict": "HIGH_POTENTIAL" if final_score >= 70 else "MODERATE_POTENTIAL"
    }

def check_ai_research_limits(topic: str, engine=None) -> Dict[str, Any]:
    if engine is None:
        engine = get_db_engine()

    clean_topic = ai_engine.sanitize_input(topic).lower()
    topic_hash = hashlib.sha256(clean_topic.encode("utf-8")).hexdigest()[:16]
    max_daily = int(os.getenv("MAX_DAILY_AI_RESEARCH_JOBS", "5"))

    with engine.connect() as conn:
        since_t = datetime.utcnow() - timedelta(days=1)
        daily_count = conn.execute(text("""
            SELECT count(*) FROM system_logs 
            WHERE module = 'AI_RESEARCH' AND status = 'EXECUTED' AND created_at >= :t
        """), {"t": since_t}).scalar() or 0

        if daily_count >= max_daily:
            return {"allowed": False, "reason": "RATE_LIMIT_REACHED", "daily_count": daily_count}

        duplicate = conn.execute(text("""
            SELECT id FROM system_logs 
            WHERE module = 'AI_RESEARCH' AND message LIKE :thash
        """), {"thash": f"%[hash:{topic_hash}]%"}).first()

        if duplicate:
            return {"allowed": False, "reason": "DUPLICATE_TOPIC", "topic_hash": topic_hash}

    return {"allowed": True, "topic_hash": topic_hash}

def generate_growth_recommendations(topic: str, target_niche: str, engine=None) -> Dict[str, Any]:
    if engine is None:
        engine = get_db_engine()

    clean_topic = ai_engine.sanitize_input(topic)
    clean_niche = ai_engine.sanitize_input(target_niche)

    limit_check = check_ai_research_limits(clean_topic, engine)
    if not limit_check["allowed"]:
        return {"status": "BLOCKED", "reason": limit_check["reason"], "recommendation": None}

    autonomy_level = int(os.getenv("AUTONOMY_LEVEL", "2"))
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
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO system_logs (module, status, message)
            VALUES ('AI_RESEARCH', 'EXECUTED', :msg)
        """), {"msg": f"Researched topic: {clean_topic} [hash:{topic_hash}]"})

    return {
        "status": "SUCCESS",
        "autonomy_level": autonomy_level,
        "staged_for_approval": autonomy_level == 2,
        "data": rec_payload
    }