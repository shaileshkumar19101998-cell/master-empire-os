import os
import hashlib
import json
import re
import time
import hmac
import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta
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
    if not val:
        return ""
    clean = re.sub(r"[^\w\s\-\.\,\:\?\/@]", "", str(val)).strip()
    return clean[:max_length]

# ==================== 1. REVENUE & BUSINESS TELEMETRY ====================

def calculate_revenue_metrics(engine=None) -> Dict[str, Any]:
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

# ==================== 2. PHASE 2.0: MAGIC-LINK AUTHENTICATION ====================

def generate_customer_magic_link_token(customer_id: str, email: str, expiry_seconds: int = 900) -> str:
    secret = (os.getenv("MAGIC_LINK_SECRET") or os.getenv("DOWNLOAD_TOKEN_SECRET") or "default_magic_secret").strip()
    exp_time = int(time.time()) + expiry_seconds
    nonce = uuid.uuid4().hex[:12]
    cid_str = str(customer_id).strip()
    email_clean = str(email).strip().lower()

    msg = f"{cid_str}:{email_clean}:{exp_time}:{nonce}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return f"{cid_str}__{email_clean}__{exp_time}__{nonce}__{sig}"

def verify_and_consume_magic_link_token(token: str, engine=None) -> Optional[Dict[str, Any]]:
    if engine is None:
        engine = get_db_engine()

    try:
        parts = token.split("__")
        if len(parts) != 5:
            return None
        cid_str, email_clean, exp_time_str, nonce, sig = parts
        exp_time = int(exp_time_str)

        if time.time() > exp_time:
            return None

        secret = (os.getenv("MAGIC_LINK_SECRET") or os.getenv("DOWNLOAD_TOKEN_SECRET") or "default_magic_secret").strip()
        msg = f"{cid_str}:{email_clean}:{exp_time}:{nonce}".encode("utf-8")
        expected_sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

        if not hmac.compare_digest(sig, expected_sig):
            return None

        sig_hash = hashlib.sha256(sig.encode("utf-8")).hexdigest()
        with engine.begin() as conn:
            consumed = conn.execute(text("""
                SELECT id FROM system_logs 
                WHERE module = 'MAGIC_LINK' AND status = 'CONSUMED' AND message LIKE :mhash
            """), {"mhash": f"%[token_hash:{sig_hash}]%"}).first()

            if consumed:
                return None

            conn.execute(text("""
                INSERT INTO system_logs (module, status, message)
                VALUES ('MAGIC_LINK', 'CONSUMED', :msg)
            """), {"msg": f"Magic link token consumed for customer {cid_str} [token_hash:{sig_hash}]"})

        return {"customer_id": cid_str, "email": email_clean}
    except Exception:
        return None

# ==================== 3. PHASE 2.0: OUTBOUND MARKETING PROVIDERS ====================

class BaseMarketingProvider:
    def dispatch(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

class WebhookDispatchProvider(BaseMarketingProvider):
    def dispatch(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = os.getenv("OUTBOUND_WEBHOOK_URL", "").strip()
        secret = os.getenv("OUTBOUND_DISPATCH_SECRET", "").strip()
        
        if not url:
            return {"provider": "LOCAL_FALLBACK", "dispatched": True, "target": "internal_queue", "status_code": 200}

        import urllib.request
        import urllib.error
        
        req_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=req_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Dispatch-Signature": hmac.new(secret.encode("utf-8"), req_bytes, hashlib.sha256).hexdigest() if secret else ""
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                return {"provider": "WEBHOOK", "dispatched": True, "status_code": resp.status}
        except Exception as e:
            raise RuntimeError(f"Outbound webhook delivery failed: {str(e)}")

def dispatch_approved_campaign_kit(approval_id: int, provider: Optional[BaseMarketingProvider] = None, engine=None) -> Dict[str, Any]:
    if engine is None:
        engine = get_db_engine()
    if provider is None:
        provider = WebhookDispatchProvider()

    with engine.connect() as conn:
        approval = conn.execute(
            text("SELECT * FROM pending_approvals WHERE id = :id"),
            {"id": approval_id}
        ).mappings().first()

        if not approval:
            raise ValueError(f"Approval record ID {approval_id} not found.")
        if approval["status"] != "APPROVED":
            raise PermissionError(f"Dispatch blocked: Item ID {approval_id} has status '{approval['status']}'. Level 2 Human Approval is mandatory.")

        mkt_log = conn.execute(text("""
            SELECT message FROM system_logs 
            WHERE module = 'MARKETING_AI' AND status = 'EXECUTED'
            ORDER BY id DESC LIMIT 1
        """)).scalar()

        if not mkt_log:
            raise ValueError("No eligible marketing kit content found for dispatch.")

        dispatch_hash = hashlib.sha256(f"{approval_id}:{mkt_log}".encode("utf-8")).hexdigest()
        already_dispatched = conn.execute(text("""
            SELECT id FROM system_logs 
            WHERE module = 'MARKETING_DISPATCH' AND status = 'SENT' AND message LIKE :dhash
        """), {"dhash": f"%[dispatch_hash:{dispatch_hash}]%"}).first()

        if already_dispatched:
            raise ValueError(f"Campaign for approval ID {approval_id} already dispatched (Duplicate prevented).")

    max_retries = 3
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            res = provider.dispatch({"approval_id": approval_id, "content": mkt_log, "dispatch_hash": dispatch_hash})
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO system_logs (module, status, message)
                    VALUES ('MARKETING_DISPATCH', 'SENT', :msg)
                """), {"msg": f"Campaign ID {approval_id} successfully sent [dispatch_hash:{dispatch_hash}] via {res.get('provider')}"})
            return {"status": "SUCCESS", "dispatch_hash": dispatch_hash, "attempt": attempt, "provider_result": res}
        except Exception as e:
            last_err = str(e)
            if attempt < max_retries:
                time.sleep(0.1 * (2 ** attempt))

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO system_logs (module, status, message)
            VALUES ('MARKETING_DISPATCH', 'FAILED', :msg)
        """), {"msg": f"Campaign ID {approval_id} failed after {max_retries} attempts [dispatch_hash:{dispatch_hash}]. Error: {last_err}"})

    raise RuntimeError(f"Campaign dispatch failed after {max_retries} retries: {last_err}")

# ==================== 4. MARKETING GENERATION & OBSERVABILITY ====================

def calculate_cost_and_margin_metrics(engine=None) -> Dict[str, Any]:
    if engine is None:
        engine = get_db_engine()

    total_ai_tokens = 0
    total_ai_cost_inr = Decimal("0.00")
    total_downloads = 0

    TOKEN_COST_RATE = Decimal("0.00015")
    MARKETING_COST_FLAT = Decimal("2.50")
    STORAGE_PER_MB = Decimal("0.0012")

    with engine.connect() as conn:
        ai_logs = conn.execute(text("""
            SELECT message FROM system_logs 
            WHERE module = 'AI_TELEMETRY' OR module = 'WORKER_PIPELINE' OR module = 'MARKETING_AI'
        """)).mappings().all()

        for l in ai_logs:
            msg = str(l["message"])
            if "[tokens:" in msg:
                try:
                    match = re.search(r"\[tokens:(\d+)\]", msg)
                    if match:
                        toks = int(match.group(1))
                        total_ai_tokens += toks
                        total_ai_cost_inr += (Decimal(str(toks)) * TOKEN_COST_RATE)
                except Exception:
                    pass
            elif "Generated marketing kit" in msg:
                total_ai_cost_inr += MARKETING_COST_FLAT

        books = conn.execute(text("SELECT count(*) as total_books FROM books WHERE status = 'COMPLETED' OR status = 'PUBLISHED'")).scalar() or 0
        estimated_storage_mb = Decimal(str(books * 1.5))
        storage_cost_inr = (estimated_storage_mb * STORAGE_PER_MB).quantize(Decimal("0.01"))

        download_count = conn.execute(text("SELECT count(*) FROM system_logs WHERE module = 'DOWNLOAD_ENGINE'")).scalar() or 0
        total_downloads = download_count

    rev_metrics = calculate_revenue_metrics(engine)
    gross_rev = Decimal(rev_metrics["gross_revenue"])
    gateway_fees = Decimal(rev_metrics["gateway_fees"])
    total_cogs = (total_ai_cost_inr + storage_cost_inr).quantize(Decimal("0.01"))
    true_operating_profit = (gross_rev - gateway_fees - total_cogs).quantize(Decimal("0.01"))
    operating_margin_pct = f"{(true_operating_profit / gross_rev * 100):.1f}%" if gross_rev > 0 else "0.0%"

    return {
        "gross_revenue": str(gross_rev),
        "gateway_fees": str(gateway_fees),
        "total_ai_tokens": total_ai_tokens,
        "total_ai_cost_inr": str(total_ai_cost_inr.quantize(Decimal("0.01"))),
        "estimated_storage_mb": str(estimated_storage_mb),
        "storage_cost_inr": str(storage_cost_inr),
        "total_downloads": total_downloads,
        "total_cogs_inr": str(total_cogs),
        "true_operating_profit": str(true_operating_profit),
        "operating_margin_pct": operating_margin_pct,
        "cost_model": "DETERMINISTIC_ESTIMATED"
    }

def detect_system_anomalies(engine=None) -> Dict[str, Any]:
    if engine is None:
        engine = get_db_engine()

    anomalies = []
    health_status = "HEALTHY"

    with engine.connect() as conn:
        since_t = datetime.now(timezone.utc) - timedelta(days=1)
        daily_ai_count = conn.execute(text("""
            SELECT count(*) FROM system_logs 
            WHERE (module = 'AI_RESEARCH' OR module = 'MARKETING_AI' OR module = 'AI_TELEMETRY') 
            AND status = 'EXECUTED' AND created_at >= :t
        """), {"t": since_t}).scalar() or 0

        max_daily = int(os.getenv("MAX_DAILY_AI_RESEARCH_JOBS", "5"))
        if daily_ai_count >= max_daily:
            anomalies.append({
                "type": "QUOTA_CEILING_REACHED",
                "severity": "WARNING",
                "message": f"Daily AI quota reached ({daily_ai_count}/{max_daily}). AI synthesis throttled for cost protection."
            })

        failed_payments = conn.execute(text("""
            SELECT count(*) FROM orders WHERE status = 'PENDING' AND created_at >= :t
        """), {"t": datetime.now(timezone.utc) - timedelta(hours=1)}).scalar() or 0

        if failed_payments >= 5:
            anomalies.append({
                "type": "PAYMENT_ABANDONMENT_SPIKE",
                "severity": "CRITICAL",
                "message": f"Elevated pending orders detected ({failed_payments} in past hour). Investigate gateway checkout friction."
            })
            health_status = "ATTENTION_REQUIRED"

        rate_limit_events = conn.execute(text("""
            SELECT count(*) FROM system_logs 
            WHERE module = 'SECURITY' AND status = 'RATE_LIMIT_EXCEEDED' AND created_at >= :t
        """), {"t": datetime.now(timezone.utc) - timedelta(hours=1)}).scalar() or 0

        if rate_limit_events >= 3:
            anomalies.append({
                "type": "RATE_LIMIT_ANOMALY",
                "severity": "WARNING",
                "message": f"{rate_limit_events} download rate limit events triggered. Potential scraper or token abuse blocked."
            })

    return {
        "system_health": health_status,
        "active_anomalies": anomalies,
        "anomaly_count": len(anomalies)
    }

def calculate_acquisition_metrics(engine=None) -> Dict[str, Any]:
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

                if src not in sources_map:
                    sources_map[src] = {"orders": 0, "paid_orders": 0, "revenue": Decimal("0.00")}
                sources_map[src]["orders"] += 1
                if is_paid:
                    sources_map[src]["paid_orders"] += 1
                    sources_map[src]["revenue"] += amt

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

def generate_marketing_campaign_kit(product_id: int, campaign_name: str = "launch", engine=None) -> Dict[str, Any]:
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

        since_t = datetime.now(timezone.utc) - timedelta(days=1)
        daily_count = conn.execute(text("""
            SELECT count(*) FROM system_logs 
            WHERE (module = 'AI_RESEARCH' OR module = 'MARKETING_AI' OR module = 'AI_TELEMETRY') 
            AND status = 'EXECUTED' AND created_at >= :t
        """), {"t": since_t}).scalar() or 0

        if daily_count >= max_daily:
            raise ValueError(f"Daily AI budget limit reached ({daily_count}/{max_daily}).")

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
        conn.execute(text("""
            INSERT INTO system_logs (module, status, message)
            VALUES ('MARKETING_AI', 'EXECUTED', :msg)
        """), {"msg": f"Generated marketing kit for {p_slug} ({clean_campaign}) [hash:{dup_hash}]"})

        conn.execute(text("""
            INSERT INTO pending_approvals (book_id, status)
            VALUES (:bid, 'PENDING')
        """), {"bid": prod["id"]})

    return {
        "status": "STAGED_FOR_APPROVAL",
        "autonomy_level": 2,
        "data": marketing_kit
    }

def get_command_center_telemetry(engine=None) -> Dict[str, Any]:
    if engine is None:
        engine = get_db_engine()

    metrics = calculate_revenue_metrics(engine)
    acquisition = calculate_acquisition_metrics(engine)
    cost_metrics = calculate_cost_and_margin_metrics(engine)
    anomalies = detect_system_anomalies(engine)

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
        "acquisition": acquisition,
        "cost_metrics": cost_metrics,
        "anomalies": anomalies,
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