import os
import math
import html
import json
import time
import hmac
import hashlib
from decimal import Decimal
from typing import Optional
from collections import defaultdict

from fastapi import FastAPI, HTTPException, Request, Response, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, Response as PlainResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

import storage_engine
import growth_engine
import ai_engine

load_dotenv()
db_url = os.getenv("DATABASE_URL", "sqlite:///./autonomous_local.db")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

if "sqlite" in db_url:
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
else:
    engine = create_engine(db_url, pool_pre_ping=True)

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
DOWNLOAD_TOKEN_SECRET = os.getenv("DOWNLOAD_TOKEN_SECRET", "")
BI_ADMIN_SECRET = os.getenv("BI_ADMIN_SECRET", "")

RATE_LIMIT_RECORD = defaultdict(list)
RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX_REQ = 5

app = FastAPI(title="Autonomous Business OS - Global Enterprise Engine", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CreateOrderRequest(BaseModel):
    product_id: int
    customer_email: str = "customer@global-enterprise.org"
    coupon_code: Optional[str] = None

class CreatePaymentSessionRequest(BaseModel):
    order_id: str

class AdminActionRequest(BaseModel):
    approval_id: int
    reason: Optional[str] = "Admin Decision"
    financial_override: Optional[bool] = False

def generate_signed_download_token(order_id: str, expiry_seconds: int = 86400) -> str:
    secret = os.getenv("DOWNLOAD_TOKEN_SECRET") or DOWNLOAD_TOKEN_SECRET
    if not secret:
        raise ValueError("DOWNLOAD_TOKEN_SECRET missing. Fail closed.")
    exp_time = int(time.time()) + expiry_seconds
    version = "v1"
    oid_str = str(order_id).strip()
    raw_msg = f"{oid_str}:{exp_time}:{version}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), raw_msg, hashlib.sha256).hexdigest()
    return f"{oid_str}.{exp_time}.{version}.{sig}"

def verify_signed_download_token(token: str, order_id: str) -> bool:
    try:
        secret = os.getenv("DOWNLOAD_TOKEN_SECRET") or DOWNLOAD_TOKEN_SECRET
        if not secret:
            return False
        parts = token.split(".")
        if len(parts) != 4:
            return False
        t_oid_str, t_exp_str, t_ver, t_sig = parts
        t_exp = int(t_exp_str)
        oid_str = str(order_id).strip()

        if t_oid_str != oid_str:
            return False
        if time.time() > t_exp:
            return False

        raw_msg = f"{oid_str}:{t_exp}:{t_ver}".encode("utf-8")
        expected_sig = hmac.new(secret.encode("utf-8"), raw_msg, hashlib.sha256).hexdigest()
        return hmac.compare_digest(t_sig, expected_sig)
    except Exception:
        return False

# ==================== STOREFRONT & SEO ====================

@app.get("/", response_class=HTMLResponse)
def get_storefront():
    cards_html = ""
    try:
        with engine.connect() as conn:
            products = conn.execute(
                text("SELECT id, slug, title, tier_level, target_niche, base_price_inr, base_price_usd FROM products WHERE status = 'ACTIVE'")
            ).mappings().all()

        for p in products:
            price_val = int(p.get("base_price_inr") or 0)
            is_free = price_val == 0
            price_badge = '<span style="color: #10b981; font-weight: bold;">FREE</span>' if is_free else f'₹{price_val}'
            cta_text = "Get Free Asset" if is_free else "Buy Now"
            p_title = html.escape(str(p.get('title') or ''))
            p_niche = html.escape(str(p.get('target_niche') or ''))
            p_tier = html.escape(str(p.get('tier_level') or 'Tier 1'))
            p_slug = html.escape(str(p.get('slug') or ''))
            p_id = p.get("id")

            cards_html += f"""
            <div style="background: #1e293b; border-radius: 12px; padding: 24px; border: 1px solid #334155; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <span style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #38bdf8; font-weight: 600;">{p_niche}</span>
                    <h3 style="color: #f8fafc; margin: 10px 0 8px 0; font-size: 18px;">{p_title}</h3>
                    <p style="color: #94a3b8; font-size: 13px; line-height: 1.5; margin-bottom: 16px;">Tier: {p_tier} • Complete enterprise blueprint.</p>
                </div>
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                        <span style="font-size: 20px; font-weight: 700; color: #f8fafc;">{price_badge}</span>
                        <a href="/books/{p_slug}" style="color: #38bdf8; font-size: 13px; text-decoration: none;">Details &rarr;</a>
                    </div>
                    <button onclick="initiateCheckout({p_id})" style="width: 100%; background: #2563eb; color: #ffffff; padding: 12px; border: none; border-radius: 8px; font-weight: 600; cursor: pointer;">
                        {cta_text}
                    </button>
                </div>
            </div>
            """
    except Exception:
        cards_html = "<div style='color: #94a3b8; padding: 20px;'>Catalog repository initializing. Check back momentarily.</div>"

    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Autonomous OS — Digital Publishing Catalog</title>
    <link rel="canonical" href="https://master-empire-os.onrender.com/">
    <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
    <style>
        body {{ font-family: -apple-system, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 0; }}
        .container {{ max-width: 1100px; margin: 0 auto; padding: 40px 20px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 24px; margin-top: 32px; }}
    </style>
</head>
<body>
    <div class="container">
        <header style="border-bottom: 1px solid #334155; padding-bottom: 24px; display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h1 style="color: #f8fafc; margin: 0; font-size: 24px;">Autonomous OS Library</h1>
                <p style="color: #94a3b8; margin: 4px 0 0 0; font-size: 14px;">Instant cryptographically-authorized technical assets</p>
            </div>
            <a href="/docs" style="color: #38bdf8; text-decoration: none; font-size: 13px; border: 1px solid #334155; padding: 8px 16px; border-radius: 6px;">API Docs</a>
        </header>
        <div class="grid">{cards_html}</div>
    </div>
    <script>
        async function initiateCheckout(productId) {{
            const email = prompt("Enter your email for digital asset delivery:", "customer@global-enterprise.org");
            if (!email) return;
            const res = await fetch("/api/orders/create", {{
                method: "POST",
                headers: {{ "Content-Type": "application/json" }},
                body: JSON.stringify({{ product_id: productId, customer_email: email }})
            }});
            const data = await res.json();
            if (data.download_url) {{
                window.location.href = data.download_url;
                return;
            }}
            const sessRes = await fetch("/api/payments/create-session", {{
                method: "POST",
                headers: {{ "Content-Type": "application/json" }},
                body: JSON.stringify({{ order_id: data.order_id }})
            }});
            const sess = await sessRes.json();
            const options = {{
                "key": sess.razorpay_key_id,
                "amount": sess.amount_paise,
                "currency": "INR",
                "name": "Autonomous OS",
                "description": "Digital Asset Purchase",
                "order_id": sess.razorpay_order_id,
                "handler": function (response) {{
                    alert("Payment received! Digital asset will be available upon settlement confirmation.");
                }}
            }};
            const rzp = new Razorpay(options);
            rzp.open();
        }}
    </script>
</body>
</html>""")

@app.get("/books/{slug}", response_class=HTMLResponse)
def get_product_detail(slug: str):
    slug_clean = slug.strip().lower()
    with engine.connect() as conn:
        p = conn.execute(
            text("SELECT id, slug, title, tier_level, target_niche, base_price_inr, base_price_usd FROM products WHERE slug = :slug AND status = 'ACTIVE'"),
            {"slug": slug_clean}
        ).mappings().first()

    if not p:
        raise HTTPException(status_code=404, detail="Book not found in public catalog.")

    is_free = p["base_price_inr"] == 0
    price_str = "FREE" if is_free else f"₹{p['base_price_inr']}"

    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{html.escape(p['title'])} — Autonomous OS</title>
    <link rel="canonical" href="https://master-empire-os.onrender.com/books/{p['slug']}">
    <style>
        body {{ font-family: -apple-system, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 40px 20px; }}
        .box {{ max-width: 650px; margin: 0 auto; background: #1e293b; padding: 32px; border-radius: 12px; border: 1px solid #334155; }}
    </style>
</head>
<body>
    <div class="box">
        <a href="/" style="color: #38bdf8; text-decoration: none; font-size: 13px;">&larr; Back to Catalog</a>
        <h1 style="color: #f8fafc; font-size: 24px; margin-top: 16px;">{html.escape(p['title'])}</h1>
        <p style="color: #94a3b8;">Category: {html.escape(p['target_niche'])} | Tier: {p['tier_level']}</p>
        <h2 style="color: #10b981; margin: 20px 0;">{price_str}</h2>
        <a href="/" style="display: inline-block; background: #2563eb; color: #fff; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: 600;">Purchase on Catalog</a>
    </div>
</body>
</html>""")

@app.get("/robots.txt", response_class=PlainResponse)
def get_robots():
    content = "User-agent: *\nAllow: /\nDisallow: /api/download/\nDisallow: /api/payments/\nDisallow: /admin/\nDisallow: /api/admin/\nSitemap: https://master-empire-os.onrender.com/sitemap.xml\n"
    return PlainResponse(content, media_type="text/plain")

@app.get("/sitemap.xml", response_class=PlainResponse)
def get_sitemap():
    urls = ['<url><loc>https://master-empire-os.onrender.com/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>']
    try:
        with engine.connect() as conn:
            products = conn.execute(text("SELECT slug FROM products WHERE status = 'ACTIVE'")).mappings().all()
        for p in products:
            if p.get("slug"):
                urls.append(f'<url><loc>https://master-empire-os.onrender.com/books/{p["slug"]}</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>')
    except Exception:
        pass

    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{''.join(urls)}
</urlset>"""
    return PlainResponse(xml_content, media_type="application/xml")

# ==================== PHASE 1.1: ULTRA-PREMIUM AI COMMAND CENTER ====================

@app.get("/admin/bi-dashboard", response_class=HTMLResponse)
@app.get("/admin/bi-dashboard/", response_class=HTMLResponse)
def get_bi_dashboard(request: Request, x_admin_secret: Optional[str] = Header(None)):
    configured_secret = (os.getenv("BI_ADMIN_SECRET") or BI_ADMIN_SECRET).strip()
    query_secret = request.query_params.get("secret", "")
    provided_secret = x_admin_secret or query_secret

    if not configured_secret or not provided_secret or not hmac.compare_digest(provided_secret, configured_secret):
        raise HTTPException(status_code=401, detail="Unauthorized access to Command Center.")

    t_data = growth_engine.get_command_center_telemetry(engine)
    m = t_data["metrics"]

    # Approvals HTML
    approvals_html = ""
    if not t_data["pending_approvals"]:
        approvals_html = "<tr><td colspan='4' style='padding: 16px; text-align: center; color: #64748b;'>No items pending human approval. System autonomous queue optimal.</td></tr>"
    else:
        for app_item in t_data["pending_approvals"]:
            app_title = html.escape(str(app_item.get('title') or 'Pending Growth Recommendation'))
            app_niche = html.escape(str(app_item.get('target_niche') or 'Strategy'))
            approvals_html += f"""
            <tr style="border-bottom: 1px solid #1e293b;">
                <td style="padding: 14px 16px; font-weight: 600; color: #f8fafc;">{app_title}<br><span style="font-size: 11px; color: #38bdf8; font-weight: normal;">Niche: {app_niche}</span></td>
                <td style="padding: 14px 16px; color: #f59e0b; font-size: 12px;"><span style="background: rgba(245,158,11,0.1); padding: 4px 8px; border-radius: 4px; border: 1px solid rgba(245,158,11,0.3);">STAGED FOR APPROVAL</span></td>
                <td style="padding: 14px 16px; color: #94a3b8; font-size: 12px;">{app_item['created_at']}</td>
                <td style="padding: 14px 16px; text-align: right;">
                    <button onclick="processApproval({app_item['id']}, 'approve')" style="background: #10b981; color: #022c22; font-weight: 700; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; margin-right: 6px; font-size: 12px;">APPROVE</button>
                    <button onclick="processApproval({app_item['id']}, 'reject')" style="background: #ef4444; color: #450a0a; font-weight: 700; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 12px;">REJECT</button>
                </td>
            </tr>
            """

    # Transactions HTML
    tx_html = ""
    for tx in t_data["recent_transactions"]:
        tx_title = html.escape(str(tx.get('title') or 'Enterprise Product'))
        tx_status_badge = '<span style="color:#10b981; font-weight:bold;">PAID</span>' if tx['status'] == 'PAID' else '<span style="color:#f59e0b;">PENDING</span>'
        tx_html += f"""
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid #1e293b;">
            <div>
                <div style="color: #f8fafc; font-size: 13px; font-weight: 600;">{tx_title}</div>
                <div style="color: #64748b; font-size: 11px;">Ref: {str(tx['id'])[:8]}... • {tx['created_at']}</div>
            </div>
            <div style="text-align: right;">
                <div style="color: #f8fafc; font-size: 13px; font-weight: 700;">₹{tx['net_amount']}</div>
                <div style="font-size: 11px;">{tx_status_badge}</div>
            </div>
        </div>
        """

    # Audit Logs HTML
    logs_html = "".join([
        f"<div style='font-family: monospace; font-size: 11px; padding: 6px 0; border-bottom: 1px solid #1e293b; color: #94a3b8;'>"
        f"<span style='color: #38bdf8;'>[{html.escape(str(l['module']))}]</span> "
        f"<span style='color: #10b981;'>{html.escape(str(l['status']))}</span>: {html.escape(str(l['message']))}"
        f"</div>"
        for l in t_data["audit_logs"]
    ])

    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Autonomous OS — Ultra-Premium Command Center</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b0f19; color: #e2e8f0; margin: 0; padding: 0; -webkit-font-smoothing: antialiased; }}
        .header {{ background: #0f172a; border-bottom: 1px solid #1e293b; padding: 16px 32px; display: flex; justify-content: space-between; align-items: center; }}
        .badge-live {{ background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); padding: 4px 10px; border-radius: 9999px; font-size: 11px; font-weight: 700; letter-spacing: 0.5px; display: flex; align-items: center; gap: 6px; }}
        .badge-live::before {{ content: ""; width: 6px; height: 6px; background: #10b981; border-radius: 50%; box-shadow: 0 0 8px #10b981; }}
        .badge-autonomy {{ background: rgba(56, 189, 248, 0.1); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); padding: 4px 10px; border-radius: 9999px; font-size: 11px; font-weight: 600; }}
        .container {{ max-width: 1300px; margin: 0 auto; padding: 32px 24px; }}
        .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 28px; }}
        .kpi-card {{ background: #131b2e; border: 1px solid #1e293b; border-radius: 12px; padding: 20px; }}
        .kpi-label {{ color: #64748b; font-size: 11px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; }}
        .kpi-val {{ font-size: 26px; font-weight: 800; color: #f8fafc; margin: 8px 0 4px 0; font-variant-numeric: tabular-nums; }}
        .grid-2 {{ display: grid; grid-template-columns: 2fr 1fr; gap: 24px; margin-bottom: 28px; }}
        .panel {{ background: #131b2e; border: 1px solid #1e293b; border-radius: 12px; padding: 24px; }}
        .panel-title {{ font-size: 15px; font-weight: 700; color: #f8fafc; margin: 0 0 16px 0; display: flex; justify-content: space-between; align-items: center; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ text-align: left; font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; padding: 12px 16px; background: #0f172a; }}
        .pipeline-stepper {{ display: flex; justify-content: space-between; background: #0f172a; padding: 16px; border-radius: 8px; border: 1px solid #1e293b; margin-top: 12px; }}
        .step {{ text-align: center; font-size: 11px; color: #94a3b8; }}
        .step-val {{ font-size: 18px; font-weight: 800; color: #f8fafc; margin-top: 4px; }}
    </style>
</head>
<body>
    <div class="header">
        <div style="display: flex; align-items: center; gap: 16px;">
            <h1 style="margin: 0; font-size: 18px; font-weight: 800; color: #f8fafc; letter-spacing: -0.5px;">AUTONOMOUS OS</h1>
            <span class="badge-live">SYSTEM LIVE</span>
            <span class="badge-autonomy">LEVEL 2: HUMAN-GATED</span>
        </div>
        <div style="display: flex; align-items: center; gap: 16px; font-size: 12px; color: #94a3b8;">
            <span>AI Capacity: <strong style="color: #f8fafc;">Active (5/Day Max)</strong></span>
            <span>Storage: <strong style="color: #10b981;">R2 Private</strong></span>
        </div>
    </div>

    <div class="container">
        <!-- Telemetry Row -->
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-label">Gross Revenue</div>
                <div class="kpi-val" style="color: #10b981;">₹{m['gross_revenue']}</div>
                <span style="font-size: 11px; color: #64748b;">Deterministic Settled</span>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Net Margin</div>
                <div class="kpi-val" style="color: #38bdf8;">₹{m['net_revenue']}</div>
                <span style="font-size: 11px; color: #64748b;">After Gateway Fees</span>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Paid Orders</div>
                <div class="kpi-val">{m['paid_orders']} <span style="font-size: 14px; color: #64748b;">/ {m['total_orders']}</span></div>
                <span style="font-size: 11px; color: #10b981;">Conversion: {m['conversion_rate']}</span>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Average Order Value</div>
                <div class="kpi-val" style="color: #f59e0b;">₹{m['average_order_value']}</div>
                <span style="font-size: 11px; color: #64748b;">Per verified buyer</span>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Health Index</div>
                <div class="kpi-val" style="color: #a855f7;">{m['health_score']}%</div>
                <span style="font-size: 11px; color: #10b981;">Optimal Status</span>
            </div>
        </div>

        <!-- Action Center: Human Approval Gate -->
        <div class="panel" style="margin-bottom: 28px; border-left: 4px solid #f59e0b;">
            <div class="panel-title">
                <span>ACTION CENTER — PENDING HUMAN APPROVAL</span>
                <span style="font-size: 12px; color: #f59e0b; font-weight: normal;">Mandatory Gate (Level 2 Autonomy)</span>
            </div>
            <table>
                <thead><tr><th>Generated Asset / Opportunity</th><th>Action Status</th><th>Created</th><th style="text-align: right;">Decision</th></tr></thead>
                <tbody>{approvals_html}</tbody>
            </table>
        </div>

        <!-- Two Column Control Matrix -->
        <div class="grid-2">
            <div>
                <!-- Publishing Pipeline State Machine -->
                <div class="panel" style="margin-bottom: 24px;">
                    <div class="panel-title">Autonomous Publishing Pipeline</div>
                    <div class="pipeline-stepper">
                        <div class="step"><div>DRAFT</div><div class="step-val" style="color: #94a3b8;">{t_data['pipeline']['DRAFT']}</div></div>
                        <div class="step"><div>PROCESSING</div><div class="step-val" style="color: #38bdf8;">{t_data['pipeline']['PROCESSING']}</div></div>
                        <div class="step"><div>COMPLETED</div><div class="step-val" style="color: #f59e0b;">{t_data['pipeline']['COMPLETED']}</div></div>
                        <div class="step"><div>PUBLISHED</div><div class="step-val" style="color: #10b981;">{t_data['pipeline']['PUBLISHED']}</div></div>
                        <div class="step"><div>FAILED</div><div class="step-val" style="color: #ef4444;">{t_data['pipeline']['FAILED']}</div></div>
                    </div>
                </div>

                <!-- AI Growth Intelligence -->
                <div class="panel">
                    <div class="panel-title">AI Growth Intelligence & Opportunities <span style="font-size: 11px; background: rgba(56,189,248,0.1); color: #38bdf8; padding: 2px 8px; border-radius: 4px;">AI RECOMMENDATION ONLY</span></div>
                    <div style="background: #0f172a; padding: 16px; border-radius: 8px; border: 1px solid #1e293b; margin-bottom: 12px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <strong style="color: #f8fafc; font-size: 13px;">High Potential Blueprint: Autonomous Multi-Agent SaaS</strong>
                            <span style="color: #10b981; font-weight: bold; font-size: 12px;">Score: 84/100 (Grade A)</span>
                        </div>
                        <p style="color: #94a3b8; font-size: 12px; margin: 8px 0 0 0; line-height: 1.4;">
                            Identified high demand with low direct competitive saturation in enterprise workflow niches. Staged for synthesis.
                        </p>
                    </div>
                </div>
            </div>

            <div>
                <!-- Real-time Transactions -->
                <div class="panel" style="margin-bottom: 24px;">
                    <div class="panel-title">Live Transaction Stream</div>
                    {tx_html if tx_html else "<div style='color:#64748b; font-size:12px;'>No recent orders recorded.</div>"}
                </div>

                <!-- System Audit Stream -->
                <div class="panel">
                    <div class="panel-title">Audit Log Stream</div>
                    {logs_html if logs_html else "<div style='color:#64748b; font-size:12px;'>No system logs available.</div>"}
                </div>
            </div>
        </div>
    </div>

    <script>
        async function processApproval(approvalId, action) {{
            const secret = prompt("Enter BI Admin Secret to authenticate action:");
            if (!secret) return;
            const endpoint = action === "approve" ? "/api/admin/approve" : "/api/admin/reject";
            const res = await fetch(endpoint, {{
                method: "POST",
                headers: {{ "Content-Type": "application/json", "x-admin-secret": secret }},
                body: JSON.stringify({{ approval_id: approvalId }})
            }});
            const data = await res.json();
            if (res.ok) {{
                alert(data.message);
                window.location.reload();
            }} else {{
                alert("Action Failed: " + (data.detail || "Unauthorized"));
            }}
        }}
    </script>
</body>
</html>""")

# ==================== ADMIN ACTION ENDPOINTS ====================

@app.post("/api/admin/approve")
def approve_job_endpoint(req: AdminActionRequest, x_admin_secret: Optional[str] = Header(None)):
    configured_secret = (os.getenv("BI_ADMIN_SECRET") or BI_ADMIN_SECRET).strip()
    if not configured_secret or not x_admin_secret or not hmac.compare_digest(x_admin_secret, configured_secret):
        raise HTTPException(status_code=401, detail="Unauthorized.")
    if req.financial_override:
        raise HTTPException(status_code=403, detail="Financial manipulation is strictly prohibited.")
    try:
        return growth_engine.approve_pending_job(req.approval_id, engine)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/admin/reject")
def reject_job_endpoint(req: AdminActionRequest, x_admin_secret: Optional[str] = Header(None)):
    configured_secret = (os.getenv("BI_ADMIN_SECRET") or BI_ADMIN_SECRET).strip()
    if not configured_secret or not x_admin_secret or not hmac.compare_digest(x_admin_secret, configured_secret):
        raise HTTPException(status_code=401, detail="Unauthorized.")
    if req.financial_override:
        raise HTTPException(status_code=403, detail="Financial manipulation is strictly prohibited.")
    try:
        return growth_engine.reject_pending_job(req.approval_id, req.reason or "Admin Rejected", engine)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==================== PAYMENT & ORDER ENDPOINTS (PHASE 0.6 UNTOUCHED) ====================

@app.post("/api/payments/create-session")
def create_payment_session(req: CreatePaymentSessionRequest):
    with engine.connect() as conn:
        order = conn.execute(
            text("SELECT * FROM orders WHERE id = :oid"),
            {"oid": req.order_id}
        ).mappings().first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")
    if order["status"] == "PAID":
        raise HTTPException(status_code=400, detail="Order already paid.")

    net_amt = Decimal(str(order["net_amount"]))
    amount_paise = int(net_amt * 100)

    return {
        "order_id": str(order["id"]),
        "razorpay_order_id": order["razorpay_order_id"] or f"order_{str(order['id'])[:14]}",
        "amount_paise": amount_paise,
        "currency": "INR",
        "razorpay_key_id": os.getenv("RAZORPAY_KEY_ID", "")
    }

@app.post("/api/orders/create")
def create_secure_order(req: CreateOrderRequest):
    try:
        import uuid
        with engine.begin() as conn:
            product = conn.execute(
                text("SELECT * FROM products WHERE id = :pid"), 
                {"pid": req.product_id}
            ).mappings().first()
            
            gross_amount = product["base_price_inr"] if product else 999

            cust = conn.execute(
                text("SELECT id FROM customers WHERE email = :email"), 
                {"email": req.customer_email.strip().lower()}
            ).mappings().first()
            
            if not cust:
                cust_id = str(uuid.uuid4())
                conn.execute(
                    text("INSERT INTO customers (id, email) VALUES (:id, :email)"), 
                    {"id": cust_id, "email": req.customer_email.strip().lower()}
                )
            else:
                cust_id = str(cust["id"])

            coupon_id = None
            discount_amount = 0
            order_type = "PAID"
            requires_payment = True

            if req.coupon_code:
                code_clean = req.coupon_code.strip().upper()
                coupon = conn.execute(
                    text("SELECT * FROM coupons WHERE code = :code AND is_active = 1"),
                    {"code": code_clean}
                ).mappings().first()

                if coupon:
                    coupon_id = coupon["id"]
                    if coupon["discount_type"] == "PERCENT":
                        discount_amount = math.floor(gross_amount * (coupon["discount_value"] / 100))
                    requires_payment = bool(coupon["requires_payment"])
                    if not requires_payment or discount_amount >= gross_amount:
                        order_type = "FREE"
                        requires_payment = False
            elif gross_amount == 0:
                order_type = "FREE"
                requires_payment = False

            net_amount = max(0, gross_amount - discount_amount)
            initial_status = "PAID" if not requires_payment else "PENDING"
            
            new_oid = str(uuid.uuid4())
            conn.execute(text("""
                INSERT INTO orders (id, customer_id, product_id, coupon_id, order_type, gross_amount, discount_amount, net_amount, currency, status)
                VALUES (:id, :cid, :pid, :cpid, :otype, :gross, :disc, :net, 'INR', :status)
            """), {
                "id": new_oid, "cid": cust_id, "pid": req.product_id, "cpid": coupon_id,
                "otype": order_type, "gross": gross_amount, "disc": discount_amount,
                "net": net_amount, "status": initial_status
            })

            download_url = None
            if not requires_payment:
                token = generate_signed_download_token(new_oid)
                download_url = f"/api/download/{new_oid}?token={token}"
                if coupon_id:
                    conn.execute(text("UPDATE coupons SET used_count = used_count + 1 WHERE id = :id"), {"id": coupon_id})

            return {
                "order_id": new_oid,
                "gross_amount": gross_amount,
                "discount_amount": discount_amount,
                "net_amount": net_amount,
                "requires_payment": requires_payment,
                "order_type": order_type,
                "status": initial_status,
                "download_url": download_url
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/payments/webhook")
async def razorpay_payment_webhook(request: Request):
    webhook_secret = (os.getenv("RAZORPAY_WEBHOOK_SECRET") or RAZORPAY_WEBHOOK_SECRET).strip()
    if not webhook_secret:
        return Response(
            content=json.dumps({"error": "Webhook secret not configured on server"}),
            status_code=500,
            media_type="application/json"
        )

    raw_body = await request.body()
    received_signature = request.headers.get("X-Razorpay-Signature", "")

    expected_signature = hmac.new(
        webhook_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256
    ).hexdigest()

    if not received_signature or not hmac.compare_digest(received_signature, expected_signature):
        return Response(content=json.dumps({"error": "Invalid Webhook Signature"}), status_code=401, media_type="application/json")

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception:
        return Response(content=json.dumps({"error": "Malformed JSON Payload"}), status_code=400, media_type="application/json")

    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    if not payment_entity:
        return Response(content=json.dumps({"error": "Missing Payment Entity"}), status_code=400, media_type="application/json")

    payment_id = payment_entity.get("id")
    rzp_order_id = payment_entity.get("order_id")
    gateway_amount_paise = payment_entity.get("amount")
    currency = payment_entity.get("currency")
    p_status = payment_entity.get("status")
    captured = payment_entity.get("captured")
    p_method = payment_entity.get("method", "razorpay")
    raw_fee = payment_entity.get("fee")

    if p_status != "captured" or not captured or currency != "INR":
        return Response(content=json.dumps({"error": "Payment is not in captured INR state"}), status_code=400, media_type="application/json")

    try:
        with engine.begin() as conn:
            existing_ledger = conn.execute(
                text("SELECT id FROM revenue_ledger WHERE transaction_ref = :tx_ref"),
                {"tx_ref": payment_id}
            ).mappings().first()

            if existing_ledger:
                return Response(content=json.dumps({"status": "ALREADY_SETTLED", "ledger_id": existing_ledger["id"]}), status_code=200, media_type="application/json")

            order = conn.execute(
                text("SELECT * FROM orders WHERE razorpay_order_id = :rzp_oid"),
                {"rzp_oid": rzp_order_id}
            ).mappings().first()

            if not order:
                return Response(content=json.dumps({"error": "Order mapping not found"}), status_code=404, media_type="application/json")

            expected_paise = int(Decimal(str(order["net_amount"])) * 100)
            if gateway_amount_paise != expected_paise:
                return Response(content=json.dumps({"error": "Payment amount mismatch"}), status_code=400, media_type="application/json")

            gateway_fee = Decimal(str(raw_fee)) / Decimal("100.0") if raw_fee is not None else Decimal("0.00")
            gross_inr = Decimal(str(order["net_amount"]))
            net_inr = gross_inr - gateway_fee

            conn.execute(text("UPDATE orders SET status = 'PAID' WHERE id = :id"), {"id": order["id"]})

            conn.execute(text("""
                INSERT INTO payments (order_id, payment_method, transaction_ref, amount, currency, status)
                VALUES (:oid, :pmethod, :tx_ref, :amt, 'INR', 'captured')
            """), {
                "oid": str(order["id"]),
                "pmethod": p_method,
                "tx_ref": payment_id,
                "amt": float(gross_inr)
            })

            conn.execute(text("""
                INSERT INTO revenue_ledger (transaction_ref, gross_amount, gateway_fee, net_revenue, currency)
                VALUES (:tx_ref, :gross, :fee, :net, 'INR')
            """), {
                "tx_ref": payment_id,
                "gross": float(gross_inr),
                "fee": float(gateway_fee),
                "net": float(net_inr)
            })

        return Response(content=json.dumps({"status": "SETTLED", "order_id": str(order["id"])}), status_code=200, media_type="application/json")
    except Exception as e:
        return Response(content=json.dumps({"error": f"Settlement Failed: {str(e)}"}), status_code=500, media_type="application/json")

@app.get("/api/download/{order_id}")
def download_secure_book(order_id: str, request: Request, token: Optional[str] = None):
    oid_clean = str(order_id).strip()
    if not token or not verify_signed_download_token(token, oid_clean):
        raise HTTPException(status_code=403, detail="Download token is invalid, expired, or missing.")

    client_ip = request.client.host if request.client else "127.0.0.1"
    curr_time = time.time()
    RATE_LIMIT_RECORD[client_ip] = [t for t in RATE_LIMIT_RECORD[client_ip] if curr_time - t < RATE_LIMIT_WINDOW]
    if len(RATE_LIMIT_RECORD[client_ip]) >= RATE_LIMIT_MAX_REQ:
        raise HTTPException(status_code=429, detail="Too many download requests. Please retry in a few seconds.")
    RATE_LIMIT_RECORD[client_ip].append(curr_time)

    try:
        with engine.connect() as conn:
            order = conn.execute(
                text("SELECT * FROM orders WHERE id = :oid"), 
                {"oid": oid_clean}
            ).mappings().first()
            
            if not order:
                raise HTTPException(status_code=404, detail="Order not found.")
            if order["status"] != "PAID":
                raise HTTPException(status_code=403, detail="Payment pending or incomplete. Access denied.")

            product = conn.execute(
                text("SELECT * FROM products WHERE id = :pid"), 
                {"pid": order["product_id"]}
            ).mappings().first()
            
            pdf_object_key = product["pdf_file_path"] if product and product["pdf_file_path"] else None

        if not pdf_object_key:
            raise HTTPException(status_code=404, detail="Digital asset object key not configured for this product.")

        client = storage_engine.get_r2_client()
        if not client:
            raise HTTPException(status_code=503, detail="Persistent object storage service unavailable.")

        if not storage_engine.object_exists(pdf_object_key):
            raise HTTPException(status_code=404, detail="Digital asset not found in storage repository.")

        presigned_url = storage_engine.generate_presigned_download(pdf_object_key, expiry_seconds=300)
        if not presigned_url:
            raise HTTPException(status_code=503, detail="Failed to generate secure download authorization.")

        return RedirectResponse(url=presigned_url, status_code=302)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))