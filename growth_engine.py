import os
import hashlib
import json
import re
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import create_engine, text

def get_db_engine():
    db_url = os.getenv("DATABASE_URL", "sqlite:///./autonomous_local.db")
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    if "sqlite" in db_url:
        return create_engine(db_url, connect_args={"check_same_thread": False})
    return create_engine(db_url, pool_pre_ping=True)

def sanitize_text(val: str, max_length: int = 120) -> str:
    """Safe inline sanitization removing script injections and enforcing bounds."""
    if not val:
        return ""
    clean = re.sub(r"[^\w\s\-\.\,\:\?\/@]", "", str(val)).strip()
    return clean[:max_length]

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

# ==================== 2. PHASE 1.2: CONVERSION & ATTRIBUTION ENGINE ====================

def calculate_acquisition_metrics(engine=None) -> Dict[str, Any]:
    """Parse zero-migration attribution metadata from system_logs and orders."""
    if engine is None:
        engine = get_db_engine()

    sources_map = {}
    campaigns_map = {}
    total_attributed_orders = 0
    total_attributed_rev = Decimal("0.00")

    with engine.connect() as conn:
        attr_logs = conn.execute(text("""
            SELECT message, created_at FROM system_logs 
            WHERE module = 'ATTRIBUTION' AND status = 'CAPTURED'
            ORDER BY id DESC LIMIT 500
        """)).mappings().all()

        for l in attr_logs:
            try:
                data = json.loads(l["message"])
                src = data.get("utm_source") or "direct"
                cmp = data.get("utm_campaign") or "organic"
                amt = Decimal(str(data.get("net_amount", 0)))
                is_paid = data.get("status") == "PAID"

                # Aggregate Source
                if src not in sources_map:
                    sources_map[src] = {"orders": 0, "paid_orders": 0, "revenue": Decimal("0.00")}
                sources_map[src]["orders"] += 1
                if is_paid:
                    sources_map[src]["paid_orders"] += 1
                    sources_map[src]["revenue"] += amt

                # Aggregate Campaign
                if cmp not in campaigns_map:
                    campaigns_map[cmp] = {"orders": 0, "paid_orders": 0, "revenue": Decimal("0.00")}
                campaigns_map[cmp]["orders"] += 1
                if is_paid:
                    campaigns_map[cmp]["paid_orders"] += 1
                    campaigns_map[cmp]["revenue"] += amt

                total_attributed_orders += 1
                if is_paid:
                    total_attributed_rev += amt
            except Exception:
                continue

    # Format output for UI tables
    src_summary = [
        {"source": k, "orders": v["orders"], "paid_orders": v["paid_orders"], "revenue": str(v["revenue"].quantize(Decimal("0.01")))}
        for k, v in sources_map.items()
    ]
    cmp_summary = [
        {"campaign": k, "orders": v["orders"], "paid_orders": v["paid_orders"], "revenue": str(v["revenue"].quantize(Decimal("0.01")))}
        for k, v in campaigns_map.items()
    ]

    top_source = max(src_summary, key=lambda x: Decimal(x["revenue"]))["source"] if src_summary else "Direct / None"
    top_campaign = max(cmp_summary, key=lambda x: Decimal(x["revenue"]))["campaign"] if cmp_summary else "Organic / None"

    return {
        "sources": src_summary,
        "campaigns": cmp_summary,
        "top_source": top_source,
        "top_campaign": top_campaign,
        "total_attributed_orders": total_attributed_orders,
        "total_attributed_revenue": str(total_attributed_rev.quantize(Decimal("0.01")))
    }

# ==================== 3. PHASE 1.2: MARKETING CAMPAIGN GENERATOR ====================

def generate_marketing_campaign_kit(product_id: int, campaign_name: str = "launch", engine=None) -> Dict[str, Any]:
    """Generate structured multi-channel marketing kit staged for Level 2 human approval."""
    if engine is None:
        engine = get_db_engine()

    clean_campaign = sanitize_text(campaign_name, max_length=50).lower() or "launch"
    max_daily = int(os.getenv("MAX_DAILY_AI_RESEARCH_JOBS", "5"))

    with engine.connect() as conn:
        prod = conn.execute(
            text("SELECT * FROM products WHERE id = :pid AND status = 'ACTIVE'"),
            {"pid": product_id}
        ).mappings().first()

        if not prod:
            raise ValueError("Target product not found or not in ACTIVE catalog.")

        # Check daily quota usage
        since_t = datetime.utcnow() - timedelta(days=1)
        daily_count = conn.execute(text("""
            SELECT count(*) FROM system_logs 
            WHERE (module = 'AI_RESEARCH' OR module = 'MARKETING_AI') AND status = 'EXECUTED' AND created_at >= :t
        """), {"t": since_t}).scalar() or 0

        if daily_count >= max_daily:
            raise ValueError(f"Daily AI budget limit reached ({daily_count}/{max_daily}).")

        # Duplicate kit check
        dup_hash = hashlib.sha256(f"{prod['slug']}:{clean_campaign}".encode("utf-8")).hexdigest()[:16]
        dup = conn.execute(text("""
            SELECT id FROM system_logs 
            WHERE module = 'MARKETING_AI' AND message LIKE :dhash
        """), {"dhash": f"%[hash:{dup_hash}]%"}).first()

        if dup:
            raise ValueError(f"Marketing kit already exists for {prod['slug']} with campaign '{clean_campaign}'.")

    p_title = sanitize_text(prod['title'], max_length=150)
    p_niche = sanitize_text(prod['target_niche'], max_length=80)
    p_slug = sanitize_text(prod['slug'], max_length=80)

    # Structured marketing content kit
    marketing_kit = {
        "product_id": prod["id"],
        "slug": p_slug,
        "campaign": clean_campaign,
        "instagram": {
            "caption": f"🚀 Master {p_title} with our definitive enterprise guide! #tech #engineering #{p_niche.lower().replace(' ', '')}",
            "reel_hook": f"Stop making this 1 crucial mistake in {p_niche}.",
            "cta": f"Link in bio to get full blueprint for ₹{prod['base_price_inr']}."
        },
        "email": {
            "subject": f"Exclusive Blueprint: How to scale your {p_niche} stack",
            "body": f"Hi there,\n\nWe just published '{p_title}'. It covers end-to-end architecture and actionable blueprints designed for high-performance teams.\n\nGrab your copy here: https://master-empire-os.onrender.com/books/{p_slug}"
        },
        "seo": {
            "title": f"{p_title} | Comprehensive Guide & Industry Handbook",
            "meta_description": f"Master {p_niche} with {p_title}. Production-grade blueprints, architectures, and implementation patterns."
        },
        "whatsapp_copy": f"🔥 New Release: *{p_title}* is now live. Get instant access here: https://master-empire-os.onrender.com/books/{p_slug}"
    }

    with engine.begin() as conn:
        # Log to system_logs
        conn.execute(text("""
            INSERT INTO system_logs (module, status, message)
            VALUES ('MARKETING_AI', 'EXECUTED', :msg)
        """), {"msg": f"Generated marketing kit for {p_slug} ({clean_campaign}) [hash:{dup_hash}]"})

        # Stage into pending_approvals (Requires Level 2 Human Approval)
        conn.execute(text("""
            INSERT INTO pending_approvals (book_id, status)
            VALUES (:bid, 'PENDING')
        """), {"bid": prod["id"]})

    return {
        "status": "STAGED_FOR_APPROVAL",
        "autonomy_level": 2,
        "data": marketing_kit
    }

# ==================== 4. COMMAND CENTER TELEMETRY UNIFICATION ====================

def get_command_center_telemetry(engine=None) -> Dict[str, Any]:
    """Single batched query aggregator for the Ultra-Premium Command Center."""
    if engine is None:
        engine = get_db_engine()

    metrics = calculate_revenue_metrics(engine)
    acquisition = calculate_acquisition_metrics(engine)

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

        # Marketing kit queues
        mkt_kits = conn.execute(text("""
            SELECT message, created_at FROM system_logs 
            WHERE module = 'MARKETING_AI' ORDER BY id DESC LIMIT 5
        """)).mappings().all()

    return {
        "metrics": metrics,
        "acquisition": acquisition,
        "pending_approvals": [dict(r) for r in pending_items],
        "pipeline": {
            "DRAFT": pipeline_counts.get("DRAFT", 0),
            "PROCESSING": pipeline_counts.get("PROCESSING", 0),
            "COMPLETED": pipeline_counts.get("COMPLETED", 0),
            "PUBLISHED": pipeline_counts.get("PUBLISHED", 0),
            "FAILED": pipeline_counts.get("FAILED", 0)
        },
        "recent_transactions": [dict(r) for r in recent_txs],
        "audit_logs": [dict(r) for r in audit_logs],
        "marketing_queue": [dict(r) for r in mkt_kits]
    }

# ==================== 5. ADMINISTRATIVE APPROVAL / REJECTION ====================

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

        if book:
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
        """), {"msg": f"Admin approved staged item ID: {approval_id}"})

    return {"status": "SUCCESS", "message": f"Approval item ID {approval_id} approved."}

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
        if approval["book_id"]:
            conn.execute(text("UPDATE books SET status = 'FAILED', error_message = :err WHERE id = :bid"),
                         {"err": reason[:250], "bid": approval["book_id"]})

        conn.execute(text("""
            INSERT INTO system_logs (module, status, message)
            VALUES ('APPROVAL_ENGINE', 'REJECTED', :msg)
        """), {"msg": f"Admin rejected item ID: {approval_id}. Reason: {reason}"})

    return {"status": "SUCCESS", "message": f"Approval item ID {approval_id} rejected."}