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
raw_db_url = os.getenv("DATABASE_URL", "sqlite:///./autonomous_local.db")

def get_db_engine():
    if raw_db_url and raw_db_url.startswith("postgres"):
        pg_url = raw_db_url.replace("postgres://", "postgresql://", 1)
        if "sslmode" not in pg_url:
            pg_url += "?sslmode=require" if "?" not in pg_url else "&sslmode=require"
        try:
            test_engine = create_engine(pg_url, pool_pre_ping=True, connect_args={"connect_timeout": 5})
            with test_engine.connect() as test_conn:
                test_conn.execute(text("SELECT 1"))
            return test_engine
        except Exception as e:
            print(f"Postgres connection fallback to SQLite: {e}")
    return create_engine("sqlite:///./autonomous_local.db", connect_args={"check_same_thread": False})

engine = get_db_engine()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
DOWNLOAD_TOKEN_SECRET = os.getenv("DOWNLOAD_TOKEN_SECRET", "")
BI_ADMIN_SECRET = os.getenv("BI_ADMIN_SECRET", "")

RATE_LIMIT_RECORD = defaultdict(list)
RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX_REQ = 5

app = FastAPI(title="Autonomous Business OS - Global Enterprise Engine", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def ensure_tables_and_seed():
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS books (
                    id SERIAL PRIMARY KEY,
                    slug VARCHAR(120) UNIQUE,
                    title VARCHAR(255),
                    target_niche VARCHAR(120),
                    status VARCHAR(50),
                    version INTEGER DEFAULT 1,
                    retry_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    pdf_file_path VARCHAR(255),
                    sha256_hash VARCHAR(64),
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    slug VARCHAR(120) UNIQUE,
                    title VARCHAR(255),
                    tier_level VARCHAR(50) DEFAULT 'Tier 1',
                    target_niche VARCHAR(120),
                    base_price_inr INTEGER DEFAULT 1,
                    base_price_usd INTEGER DEFAULT 1,
                    pdf_file_path VARCHAR(255),
                    status VARCHAR(50) DEFAULT 'ACTIVE'
                );
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS customers (
                    id VARCHAR(64) PRIMARY KEY,
                    email VARCHAR(255) UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS orders (
                    id VARCHAR(64) PRIMARY KEY,
                    customer_id VARCHAR(64),
                    product_id INTEGER,
                    coupon_id INTEGER,
                    order_type VARCHAR(50) DEFAULT 'PAID',
                    gross_amount NUMERIC DEFAULT 0,
                    discount_amount NUMERIC DEFAULT 0,
                    net_amount NUMERIC DEFAULT 0,
                    currency VARCHAR(10) DEFAULT 'INR',
                    status VARCHAR(50) DEFAULT 'PENDING',
                    razorpay_order_id VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS payments (
                    id SERIAL PRIMARY KEY,
                    order_id VARCHAR(64),
                    payment_method VARCHAR(50),
                    transaction_ref VARCHAR(100) UNIQUE,
                    amount NUMERIC,
                    currency VARCHAR(10) DEFAULT 'INR',
                    status VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS revenue_ledger (
                    id SERIAL PRIMARY KEY,
                    transaction_ref VARCHAR(100) UNIQUE,
                    gross_amount NUMERIC,
                    gateway_fee NUMERIC,
                    net_revenue NUMERIC,
                    currency VARCHAR(10) DEFAULT 'INR',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS coupons (
                    id SERIAL PRIMARY KEY,
                    code VARCHAR(50) UNIQUE,
                    discount_type VARCHAR(20),
                    discount_value NUMERIC,
                    requires_payment INTEGER DEFAULT 1,
                    is_active INTEGER DEFAULT 1,
                    expires_at TIMESTAMP,
                    used_count INTEGER DEFAULT 0
                );
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS system_logs (
                    id SERIAL PRIMARY KEY,
                    module VARCHAR(50),
                    status VARCHAR(50),
                    message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS pending_approvals (
                    id SERIAL PRIMARY KEY,
                    book_id INTEGER,
                    status VARCHAR(50) DEFAULT 'PENDING',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))

            conn.execute(text("""
                INSERT INTO products (slug, title, tier_level, target_niche, base_price_inr, base_price_usd, pdf_file_path, status)
                VALUES ('saas-architecture-handbook', 'SaaS Architecture & Scale Handbook', 'Tier 1', 'Cloud Architecture', 1, 1, 'books/saas/v1.pdf', 'ACTIVE')
                ON CONFLICT (slug) DO UPDATE SET base_price_inr = 1, status = 'ACTIVE';
            """))
    except Exception as e:
        print(f"Table auto-seed notice: {e}")

class CreateOrderRequest(BaseModel):
    product_id: int
    customer_email: str = "customer@global-enterprise.org"
    coupon_code: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    referrer: Optional[str] = None

class CreatePaymentSessionRequest(BaseModel):
    order_id: str

class AdminActionRequest(BaseModel):
    approval_id: int
    reason: Optional[str] = "Admin Decision"
    financial_override: Optional[bool] = False

class GenerateMarketingKitRequest(BaseModel):
    product_id: int
    campaign_name: Optional[str] = "launch"
    financial_override: Optional[bool] = False

class DispatchCampaignRequest(BaseModel):
    approval_id: int
    financial_override: Optional[bool] = False

class RequestMagicLinkRequest(BaseModel):
    email: str

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

# ==================== STOREFRONT ====================

@app.get("/", response_class=HTMLResponse)
def get_storefront():
    ensure_tables_and_seed()
    cards_html = ""
    try:
        with engine.connect() as conn:
            products = conn.execute(
                text("SELECT id, slug, title, tier_level, target_niche, base_price_inr, base_price_usd FROM products WHERE status = 'ACTIVE'")
            ).mappings().all()

        for p in products:
            price_val = int(p.get("base_price_inr") or 1)
            p_title = html.escape(str(p.get('title') or 'SaaS Architecture & Scale Handbook'))
            p_niche = html.escape(str(p.get('target_niche') or 'Cloud Architecture'))
            p_tier = html.escape(str(p.get('tier_level') or 'Tier 1'))
            p_slug = html.escape(str(p.get('slug') or ''))
            p_id = p.get("id")

            cards_html += f"""
            <div style="background: #1e293b; border-radius: 12px; padding: 24px; border: 1px solid #334155; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <span style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #38bdf8; font-weight: 600;">{p_niche}</span>
                    <h3 style="color: #f8fafc; margin: 10px 0 8px 0; font-size: 18px;">{p_title}</h3>
                    <p style="color: #94a3b8; font-size: 13px; line-height: 1.5; margin-bottom: 16px;">Tier: {p_tier} • Production-grade architecture blueprint.</p>
                </div>
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                        <span style="font-size: 22px; font-weight: 700; color: #10b981;">₹{price_val}</span>
                        <a href="/books/{p_slug}" style="color: #38bdf8; font-size: 13px; text-decoration: none;">Details &rarr;</a>
                    </div>
                    <button onclick="initiateCheckout({p_id}, '{p_title}', {price_val})" style="width: 100%; background: #2563eb; color: #ffffff; padding: 12px; border: none; border-radius: 8px; font-weight: 700; font-size: 14px; cursor: pointer;">
                        Buy Now (₹{price_val})
                    </button>
                </div>
            </div>
            """
    except Exception as ex:
        cards_html = f"<div style='color: #94a3b8; padding: 20px;'>Catalog initializing: {html.escape(str(ex))}</div>"

    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Autonomous OS — Digital Publishing Catalog</title>
    <link rel="canonical" href="https://master-empire-os.onrender.com/">
    <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 0; }}
        .container {{ max-width: 1100px; margin: 0 auto; padding: 40px 20px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 24px; margin-top: 32px; }}
    </style>
</head>
<body>
    <div class="container">
        <header style="border-bottom: 1px solid #334155; padding-bottom: 24px; display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h1 style="color: #f8fafc; margin: 0; font-size: 24px;">Autonomous OS Library</h1>
                <p style="color: #94a3b8; margin: 4px 0 0 0; font-size: 14px;">Instant cryptographically-authorized technical assets</p>
            </div>
            <div>
                <a href="/library" style="color: #10b981; text-decoration: none; font-size: 13px; border: 1px solid #10b981; padding: 8px 16px; border-radius: 6px; margin-right: 8px;">My Library</a>
                <a href="/docs" style="color: #38bdf8; text-decoration: none; font-size: 13px; border: 1px solid #334155; padding: 8px 16px; border-radius: 6px;">API Docs</a>
            </div>
        </header>
        <div class="grid">{cards_html}</div>
    </div>
    <script>
        function getUTMParams() {{
            const p = new URLSearchParams(window.location.search);
            return {{
                utm_source: p.get("utm_source") || "direct",
                utm_medium: p.get("utm_medium") || "organic",
                utm_campaign: p.get("utm_campaign") || "web",
                referrer: document.referrer || "direct"
            }};
        }}

        async function initiateCheckout(productId, title, priceInr) {{
            const email = prompt("Enter your email address for asset delivery:", "customer@global-enterprise.org");
            if (!email) return;

            const phone = prompt("Enter phone number for payment gateway receipt (optional):", "9876543210") || "9999999999";
            const utm = getUTMParams();

            const res = await fetch("/api/orders/create", {{
                method: "POST",
                headers: {{ "Content-Type": "application/json" }},
                body: JSON.stringify({{ product_id: productId, customer_email: email, ...utm }})
            }});
            const data = await res.json();
            
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
                "description": title,
                "prefill": {{
                    "name": "Customer",
                    "email": email,
                    "contact": phone
                }},
                "theme": {{ "color": "#2563eb" }},
                "handler": function (response) {{
                    alert("Payment received successfully! Transaction reference: " + (response.razorpay_payment_id || "captured"));
                    window.location.href = "/library";
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
    ensure_tables_and_seed()
    slug_clean = slug.strip().lower()
    with engine.connect() as conn:
        p = conn.execute(
            text("SELECT id, slug, title, tier_level, target_niche, base_price_inr, base_price_usd FROM products WHERE slug = :slug AND status = 'ACTIVE'"),
            {"slug": slug_clean}
        ).mappings().first()

    if not p:
        raise HTTPException(status_code=404, detail="Book not found in public catalog.")

    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
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
        <h2 style="color: #10b981; margin: 20px 0;">₹{p['base_price_inr']}</h2>
        <a href="/" style="display: inline-block; background: #2563eb; color: #fff; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: 600;">Purchase on Catalog</a>
    </div>
</body>
</html>""")

@app.get("/robots.txt", response_class=PlainResponse)
def get_robots():
    content = "User-agent: *\nAllow: /\nDisallow: /api/download/\nDisallow: /api/payments/\nDisallow: /admin/\nDisallow: /api/admin/\nDisallow: /library/\nSitemap: https://master-empire-os.onrender.com/sitemap.xml\n"
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

# ==================== CUSTOMER PORTAL ====================

@app.post("/api/library/request-link")
def request_customer_magic_link(req: RequestMagicLinkRequest):
    ensure_tables_and_seed()
    email_clean = req.email.strip().lower()
    with engine.connect() as conn:
        cust = conn.execute(
            text("SELECT id FROM customers WHERE email = :email"),
            {"email": email_clean}
        ).mappings().first()

        if cust:
            paid_count = conn.execute(
                text("SELECT count(*) FROM orders WHERE customer_id = :cid AND status = 'PAID'"),
                {"cid": str(cust["id"])}
            ).scalar() or 0

            if paid_count > 0:
                token = growth_engine.generate_customer_magic_link_token(str(cust["id"]), email_clean)
                return {
                    "status": "SUCCESS",
                    "message": "If an active account exists with paid assets, a secure magic access link has been generated.",
                    "magic_link": f"/library?token={token}"
                }

    return {
        "status": "SUCCESS",
        "message": "If an active account exists with paid assets, a secure magic access link has been generated."
    }

@app.get("/library", response_class=HTMLResponse)
def get_customer_library(token: Optional[str] = None):
    ensure_tables_and_seed()
    if not token:
        return HTMLResponse("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Customer Asset Portal — Autonomous OS</title>
    <style>
        body { font-family: -apple-system, sans-serif; background: #0b0f19; color: #e2e8f0; margin: 0; padding: 40px 20px; display: flex; justify-content: center; align-items: center; min-height: 80vh; }
        .card { background: #131b2e; border: 1px solid #1e293b; border-radius: 12px; padding: 32px; max-width: 420px; width: 100%; }
        input { width: 100%; box-sizing: border-box; padding: 12px; border-radius: 6px; border: 1px solid #334155; background: #0f172a; color: #f8fafc; margin: 12px 0 20px 0; }
        button { width: 100%; background: #2563eb; color: #fff; padding: 12px; border: none; border-radius: 6px; font-weight: 700; cursor: pointer; }
    </style>
</head>
<body>
    <div class="card">
        <h2 style="color: #f8fafc; margin-top: 0;">Access Your Library</h2>
        <p style="color: #94a3b8; font-size: 13px; line-height: 1.5;">Enter the email address used during purchase. We'll generate a single-use, 15-minute magic link to access your blueprints.</p>
        <input type="email" id="email" placeholder="you@company.com" required />
        <button onclick="requestLink()">Send Magic Access Link</button>
        <div id="status" style="margin-top: 16px; font-size: 13px;"></div>
    </div>
    <script>
        async function requestLink() {
            const email = document.getElementById("email").value;
            if(!email) return;
            const res = await fetch("/api/library/request-link", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email: email })
            });
            const d = await res.json();
            if(d.magic_link) {
                document.getElementById("status").innerHTML = `<span style="color:#10b981;">Access link ready:</span> <a href="${d.magic_link}" style="color:#38bdf8;">Open My Library &rarr;</a>`;
            } else {
                document.getElementById("status").innerText = d.message;
            }
        }
    </script>
</body>
</html>""")

    auth_data = growth_engine.verify_and_consume_magic_link_token(token, engine)
    if not auth_data:
        raise HTTPException(status_code=401, detail="Magic access link is invalid, expired, or has already been used.")

    cid = auth_data["customer_id"]
    with engine.connect() as conn:
        purchases = conn.execute(text("""
            SELECT o.id as order_id, o.net_amount, o.created_at, p.id as product_id, p.title, p.slug, p.tier_level
            FROM orders o
            LEFT JOIN products p ON o.product_id = p.id
            WHERE o.customer_id = :cid AND o.status = 'PAID'
            ORDER BY o.created_at DESC
        """), {"cid": cid}).mappings().all()

    items_html = ""
    for item in purchases:
        dl_token = generate_signed_download_token(str(item["order_id"]), expiry_seconds=3600)
        p_title = html.escape(str(item.get('title') or 'Technical Blueprint'))
        p_tier = html.escape(str(item.get('tier_level') or 'Tier 1'))
        items_html += f"""
        <div style="background: #131b2e; border: 1px solid #1e293b; border-radius: 8px; padding: 20px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center;">
            <div>
                <span style="font-size: 11px; text-transform: uppercase; color: #38bdf8; font-weight: 700;">{p_tier}</span>
                <h3 style="color: #f8fafc; margin: 6px 0 4px 0; font-size: 16px;">{p_title}</h3>
                <div style="color: #64748b; font-size: 12px;">Order ID: {str(item['order_id'])[:8]}... • Settled on {item['created_at']}</div>
            </div>
            <a href="/api/download/{item['order_id']}?token={dl_token}" style="background: #10b981; color: #022c22; padding: 10px 20px; border-radius: 6px; font-weight: 700; text-decoration: none; font-size: 13px;">Download PDF</a>
        </div>
        """

    if not purchases:
        items_html = "<div style='color: #94a3b8; text-align: center; padding: 32px;'>No active paid purchases found for this account.</div>"

    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My Digital Library — Autonomous OS</title>
    <style>
        body {{ font-family: -apple-system, sans-serif; background: #0b0f19; color: #e2e8f0; margin: 0; padding: 40px 20px; }}
        .container {{ max-width: 800px; margin: 0 auto; }}
    </style>
</head>
<body>
    <div class="container">
        <header style="border-bottom: 1px solid #1e293b; padding-bottom: 20px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h1 style="color: #f8fafc; margin: 0; font-size: 22px;">My Digital Asset Library</h1>
                <p style="color: #94a3b8; margin: 4px 0 0 0; font-size: 13px;">Authenticated via cryptographic magic token</p>
            </div>
            <a href="/" style="color: #38bdf8; text-decoration: none; font-size: 13px;">&larr; Catalog</a>
        </header>
        {items_html}
    </div>
</body>
</html>""")

# ==================== ADMIN DISPATCH ====================

@app.post("/api/admin/dispatch-campaign")
def dispatch_campaign_endpoint(req: DispatchCampaignRequest, x_admin_secret: Optional[str] = Header(None)):
    configured_secret = (os.getenv("BI_ADMIN_SECRET") or BI_ADMIN_SECRET).strip()
    if not configured_secret or not x_admin_secret or not hmac.compare_digest(x_admin_secret, configured_secret):
        raise HTTPException(status_code=401, detail="Unauthorized.")
    if req.financial_override:
        raise HTTPException(status_code=403, detail="Financial manipulation is strictly prohibited.")
    try:
        return growth_engine.dispatch_approved_campaign_kit(req.approval_id, engine=engine)
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== COMMAND CENTER ====================

@app.get("/admin/bi-dashboard", response_class=HTMLResponse)
@app.get("/admin/bi-dashboard/", response_class=HTMLResponse)
def get_bi_dashboard(request: Request, x_admin_secret: Optional[str] = Header(None)):
    configured_secret = (os.getenv("BI_ADMIN_SECRET") or BI_ADMIN_SECRET).strip()
    query_secret = request.query_params.get("secret", "")
    provided_secret = x_admin_secret or query_secret

    if not configured_secret or not provided_secret or not hmac.compare_digest(provided_secret, configured_secret):
        raise HTTPException(status_code=401, detail="Unauthorized access to Command Center.")

    ensure_tables_and_seed()
    t_data = growth_engine.get_command_center_telemetry(engine)
    m = t_data["metrics"]
    cost_m = t_data["cost_metrics"]
    anom = t_data["anomalies"]

    approvals_html = ""
    if not t_data["pending_approvals"]:
        approvals_html = "<tr><td colspan='4' style='padding: 16px; text-align: center; color: #64748b;'>No items pending human approval. System autonomous queue optimal.</td></tr>"
    else:
        for app_item in t_data["pending_approvals"]:
            app_title = html.escape(str(app_item.get('title') or 'Staged Marketing Asset / Book'))
            app_niche = html.escape(str(app_item.get('target_niche') or 'Growth Strategy'))
            approvals_html += f"""
            <tr style="border-bottom: 1px solid #1e293b;">
                <td style="padding: 14px 16px; font-weight: 600; color: #f8fafc;">{app_title}<br><span style="font-size: 11px; color: #38bdf8; font-weight: normal;">Category: {app_niche}</span></td>
                <td style="padding: 14px 16px; color: #f59e0b; font-size: 12px;"><span style="background: rgba(245,158,11,0.1); padding: 4px 8px; border-radius: 4px; border: 1px solid rgba(245,158,11,0.3);">STAGED FOR APPROVAL</span></td>
                <td style="padding: 14px 16px; color: #94a3b8; font-size: 12px;">{app_item['created_at']}</td>
                <td style="padding: 14px 16px; text-align: right;">
                    <button onclick="processApproval({app_item['id']}, 'approve')" style="background: #10b981; color: #022c22; font-weight: 700; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; margin-right: 6px; font-size: 12px;">APPROVE</button>
                    <button onclick="processApproval({app_item['id']}, 'reject')" style="background: #ef4444; color: #450a0a; font-weight: 700; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 12px;">REJECT</button>
                </td>
            </tr>
            """

    radar_html = ""
    if not anom["active_anomalies"]:
        radar_html = "<div style='color: #10b981; font-size: 12px; padding: 12px; background: rgba(16, 185, 129, 0.05); border-radius: 6px; border: 1px solid rgba(16, 185, 129, 0.2);'>🛡️ Zero anomalies detected across payments, AI token quotas, and storage bounds.</div>"
    else:
        for a in anom["active_anomalies"]:
            sev_color = "#ef4444" if a["severity"] == "CRITICAL" else "#f59e0b"
            radar_html += f"""
            <div style="padding: 10px 14px; background: rgba(239, 68, 68, 0.08); border-left: 3px solid {sev_color}; margin-bottom: 8px; border-radius: 4px;">
                <div style="font-weight: 700; font-size: 11px; color: {sev_color};">{a['type']}</div>
                <div style="font-size: 12px; color: #e2e8f0; margin-top: 2px;">{html.escape(a['message'])}</div>
            </div>
            """

    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
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
        .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 28px; }}
        .panel {{ background: #131b2e; border: 1px solid #1e293b; border-radius: 12px; padding: 24px; }}
        .panel-title {{ font-size: 15px; font-weight: 700; color: #f8fafc; margin: 0 0 16px 0; display: flex; justify-content: space-between; align-items: center; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ text-align: left; font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; padding: 12px 16px; background: #0f172a; }}
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
            <span>System Status: <strong style="color: #10b981;">{anom['system_health']}</strong></span>
            <span>AI Capacity: <strong style="color: #f8fafc;">Active (5 Max/Day)</strong></span>
        </div>
    </div>

    <div class="container">
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-label">Gross Revenue</div>
                <div class="kpi-val" style="color: #10b981;">₹{cost_m['gross_revenue']}</div>
                <span style="font-size: 11px; color: #64748b;">Deterministic Settled</span>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">True Operating Profit</div>
                <div class="kpi-val" style="color: #38bdf8;">₹{cost_m['true_operating_profit']}</div>
                <span style="font-size: 11px; color: #10b981;">Operating Margin: {cost_m['operating_margin_pct']}</span>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Total AI Costs</div>
                <div class="kpi-val" style="color: #f59e0b;">₹{cost_m['total_ai_cost_inr']}</div>
                <span style="font-size: 11px; color: #64748b;">Tokens: {cost_m['total_ai_tokens']}</span>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">R2 Storage Footprint</div>
                <div class="kpi-val" style="color: #a855f7;">{cost_m['estimated_storage_mb']} <span style="font-size: 14px; color: #64748b;">MB</span></div>
                <span style="font-size: 11px; color: #64748b;">Cost: ₹{cost_m['storage_cost_inr']} • Downloads: {cost_m['total_downloads']}</span>
            </div>
        </div>

        <div class="panel" style="margin-bottom: 28px; border-left: 4px solid #f59e0b;">
            <div class="panel-title">
                <span>ACTION CENTER — PENDING HUMAN APPROVAL</span>
                <span style="font-size: 12px; color: #f59e0b; font-weight: normal;">Mandatory Gate (Level 2 Autonomy)</span>
            </div>
            <table>
                <thead><tr><th>Asset / Marketing Kit</th><th>Status</th><th>Created</th><th style="text-align: right;">Decision</th></tr></thead>
                <tbody>{approvals_html}</tbody>
            </table>
        </div>

        <div class="grid-2">
            <div class="panel">
                <div class="panel-title">System Anomalies & Security Radar</div>
                {radar_html}
            </div>

            <div class="panel">
                <div class="panel-title">Financial Unit Economics Breakdown</div>
                <table style="font-size: 13px;">
                    <tr style="border-bottom: 1px solid #1e293b;"><td style="padding: 8px 0; color: #94a3b8;">Gross Settled Revenue:</td><td style="text-align: right; font-weight: bold; color: #10b981;">₹{cost_m['gross_revenue']}</td></tr>
                    <tr style="border-bottom: 1px solid #1e293b;"><td style="padding: 8px 0; color: #94a3b8;">Gateway Settlement Fees:</td><td style="text-align: right; color: #ef4444;">- ₹{cost_m['gateway_fees']}</td></tr>
                    <tr style="border-bottom: 1px solid #1e293b;"><td style="padding: 8px 0; color: #94a3b8;">AI Synthesis & Marketing COGS:</td><td style="text-align: right; color: #ef4444;">- ₹{cost_m['total_ai_cost_inr']}</td></tr>
                    <tr style="border-bottom: 1px solid #1e293b;"><td style="padding: 8px 0; color: #94a3b8;">Cloudflare R2 Storage Cost:</td><td style="text-align: right; color: #ef4444;">- ₹{cost_m['storage_cost_inr']}</td></tr>
                    <tr><td style="padding: 10px 0; font-weight: bold; color: #f8fafc;">Net Retained Earnings:</td><td style="text-align: right; font-weight: 800; color: #38bdf8; font-size: 15px;">₹{cost_m['true_operating_profit']}</td></tr>
                </table>
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

# ==================== ADMIN ACTIONS ====================

@app.post("/api/admin/generate-marketing-kit")
def generate_marketing_kit_endpoint(req: GenerateMarketingKitRequest, x_admin_secret: Optional[str] = Header(None)):
    configured_secret = (os.getenv("BI_ADMIN_SECRET") or BI_ADMIN_SECRET).strip()
    if not configured_secret or not x_admin_secret or not hmac.compare_digest(x_admin_secret, configured_secret):
        raise HTTPException(status_code=401, detail="Unauthorized.")
    if req.financial_override:
        raise HTTPException(status_code=403, detail="Financial manipulation is strictly prohibited.")
    try:
        return growth_engine.generate_marketing_campaign_kit(req.product_id, req.campaign_name or "launch", engine)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

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

# ==================== PAYMENT & ORDER ENDPOINTS ====================

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
            
            gross_amount = product["base_price_inr"] if product else 1

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

            clean_src = growth_engine.sanitize_text(req.utm_source, max_length=50) or "direct"
            clean_med = growth_engine.sanitize_text(req.utm_medium, max_length=50) or "organic"
            clean_cmp = growth_engine.sanitize_text(req.utm_campaign, max_length=50) or "web"
            clean_ref = growth_engine.sanitize_text(req.referrer, max_length=150) or "direct"

            attr_payload = json.dumps({
                "order_id": new_oid,
                "utm_source": clean_src,
                "utm_medium": clean_med,
                "utm_campaign": clean_cmp,
                "referrer": clean_ref,
                "net_amount": float(net_amount),
                "status": initial_status
            })
            conn.execute(text("""
                INSERT INTO system_logs (module, status, message)
                VALUES ('ATTRIBUTION', 'CAPTURED', :msg)
            """), {"msg": attr_payload})

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
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO system_logs (module, status, message)
                VALUES ('SECURITY', 'RATE_LIMIT_EXCEEDED', :msg)
            """), {"msg": f"Rate limit reached for IP: {client_ip} on order {oid_clean}"})
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

        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO system_logs (module, status, message)
                VALUES ('DOWNLOAD_ENGINE', 'SERVED', :msg)
            """), {"msg": f"Presigned URL generated for order {oid_clean}"})

        return RedirectResponse(url=presigned_url, status_code=302)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))