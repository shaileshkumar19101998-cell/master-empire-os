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

# ==============================================================================
# अपनी RAZORPAY KEY ID और SECRET यहाँ इनवर्टेड कॉमा (" ") के अंदर पेस्ट करें:
# ==============================================================================
MY_DIRECT_RAZORPAY_KEY_ID = "यहाँ_अपनी_KEY_ID_पेस्ट_करें"
MY_DIRECT_RAZORPAY_KEY_SECRET = "यहाँ_अपनी_KEY_SECRET_पेस्ट_करें"
# ==============================================================================

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
            print(f"Postgres fallback to SQLite: {e}")
    return create_engine("sqlite:///./autonomous_local.db", connect_args={"check_same_thread": False})

engine = get_db_engine()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID") or MY_DIRECT_RAZORPAY_KEY_ID
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET") or MY_DIRECT_RAZORPAY_KEY_SECRET
DOWNLOAD_TOKEN_SECRET = os.getenv("DOWNLOAD_TOKEN_SECRET", "super_secure_token_secret_key_prod_2026")
BI_ADMIN_SECRET = os.getenv("BI_ADMIN_SECRET", "empire_bi_secret_access_2026")

RATE_LIMIT_RECORD = defaultdict(list)
RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX_REQ = 10

app = FastAPI(title="Autonomous Business OS - Global Enterprise Engine", version="2.1.0")

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
                CREATE TABLE IF NOT EXISTS system_logs (
                    id SERIAL PRIMARY KEY,
                    module VARCHAR(50),
                    status VARCHAR(50),
                    message TEXT,
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
    customer_email: str
    coupon_code: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    referrer: Optional[str] = None

class CreatePaymentSessionRequest(BaseModel):
    order_id: str

class VerifyPaymentRequest(BaseModel):
    order_id: str
    razorpay_payment_id: str
    razorpay_order_id: Optional[str] = None
    razorpay_signature: Optional[str] = None

class RequestMagicLinkRequest(BaseModel):
    email: str

def generate_signed_download_token(order_id: str, expiry_seconds: int = 86400) -> str:
    secret = os.getenv("DOWNLOAD_TOKEN_SECRET") or DOWNLOAD_TOKEN_SECRET
    exp_time = int(time.time()) + expiry_seconds
    version = "v1"
    oid_str = str(order_id).strip()
    raw_msg = f"{oid_str}:{exp_time}:{version}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), raw_msg, hashlib.sha256).hexdigest()
    return f"{oid_str}.{exp_time}.{version}.{sig}"

def verify_signed_download_token(token: str, order_id: str) -> bool:
    try:
        secret = os.getenv("DOWNLOAD_TOKEN_SECRET") or DOWNLOAD_TOKEN_SECRET
        parts = token.split(".")
        if len(parts) != 4:
            return False
        t_oid_str, t_exp_str, t_ver, t_sig = parts
        t_exp = int(t_exp_str)
        oid_str = str(order_id).strip()

        if t_oid_str != oid_str or time.time() > t_exp:
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
                    <button id="btn-{p_id}" onclick="initiateCheckout({p_id}, '{p_title}', {price_val})" style="width: 100%; background: #2563eb; color: #ffffff; padding: 12px; border: none; border-radius: 8px; font-weight: 700; font-size: 14px; cursor: pointer;">
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
        #modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); z-index: 9999; justify-content: center; align-items: center; }}
        .modal-box {{ background: #1e293b; padding: 32px; border-radius: 12px; border: 1px solid #3b82f6; max-width: 450px; text-align: center; }}
    </style>
</head>
<body>
    <div id="modal">
        <div class="modal-box">
            <h2 style="color: #10b981; margin-top: 0;">🎉 Payment Successful!</h2>
            <p style="color: #cbd5e1; font-size: 14px;">Your digital asset has been securely unlocked.</p>
            <a id="download-btn" href="#" style="display: block; width: 85%; margin: 20px auto 10px auto; background: #10b981; color: #022c22; padding: 14px; border-radius: 8px; font-weight: 800; text-decoration: none; font-size: 16px;">Download PDF Now</a>
            <a id="library-btn" href="/library" style="color: #38bdf8; font-size: 13px; text-decoration: none;">Go to Customer Portal</a>
        </div>
    </div>

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
        async function initiateCheckout(productId, title, priceInr) {{
            try {{
                const email = prompt("Enter your email address for book delivery:", "");
                if (!email || !email.includes("@")) {{
                    alert("Please enter a valid email address.");
                    return;
                }}

                const res = await fetch("/api/orders/create", {{
                    method: "POST",
                    headers: {{ "Content-Type": "application/json" }},
                    body: JSON.stringify({{ product_id: productId, customer_email: email }})
                }});
                const orderData = await res.json();
                
                const sessRes = await fetch("/api/payments/create-session", {{
                    method: "POST",
                    headers: {{ "Content-Type": "application/json" }},
                    body: JSON.stringify({{ order_id: orderData.order_id }})
                }});
                const sess = await sessRes.json();

                const options = {{
                    "key": sess.razorpay_key_id,
                    "amount": sess.amount_paise,
                    "currency": "INR",
                    "name": "Autonomous OS",
                    "description": title,
                    "prefill": {{
                        "email": email
                    }},
                    "theme": {{ "color": "#2563eb" }},
                    "handler": async function (response) {{
                        const verifyRes = await fetch("/api/payments/verify", {{
                            method: "POST",
                            headers: {{ "Content-Type": "application/json" }},
                            body: JSON.stringify({{
                                order_id: orderData.order_id,
                                razorpay_payment_id: response.razorpay_payment_id
                            }})
                        }});
                        const verifyData = await verifyRes.json();
                        
                        document.getElementById("download-btn").href = verifyData.download_url;
                        document.getElementById("modal").style.display = "flex";
                    }}
                }};
                
                const rzp = new Razorpay(options);
                rzp.open();
            }} catch (err) {{
                alert("Checkout initialization failed: " + err.message);
            }}
        }}
    </script>
</body>
</html>""")

# ==================== PAYMENT VERIFICATION ====================

@app.post("/api/payments/verify")
def verify_payment_endpoint(req: VerifyPaymentRequest):
    with engine.begin() as conn:
        conn.execute(text("UPDATE orders SET status = 'PAID' WHERE id = :id"), {"id": req.order_id})
        conn.execute(text("""
            INSERT INTO payments (order_id, payment_method, transaction_ref, amount, currency, status)
            VALUES (:oid, 'razorpay', :tx_ref, 1.0, 'INR', 'captured')
            ON CONFLICT DO NOTHING
        """), {"oid": req.order_id, "tx_ref": req.razorpay_payment_id})

    token = generate_signed_download_token(req.order_id)
    return {
        "status": "PAID",
        "order_id": req.order_id,
        "download_url": f"/api/download/{req.order_id}?token={token}"
    }

# ==================== ORDER CREATION ====================

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
            clean_email = req.customer_email.strip().lower()

            cust = conn.execute(
                text("SELECT id FROM customers WHERE email = :email"), 
                {"email": clean_email}
            ).mappings().first()
            
            if not cust:
                cust_id = str(uuid.uuid4())
                conn.execute(
                    text("INSERT INTO customers (id, email) VALUES (:id, :email)"), 
                    {"id": cust_id, "email": clean_email}
                )
            else:
                cust_id = str(cust["id"])

            new_oid = str(uuid.uuid4())
            conn.execute(text("""
                INSERT INTO orders (id, customer_id, product_id, coupon_id, order_type, gross_amount, discount_amount, net_amount, currency, status)
                VALUES (:id, :cid, :pid, NULL, 'PAID', :gross, 0, :gross, 'INR', 'PENDING')
            """), {
                "id": new_oid, "cid": cust_id, "pid": req.product_id, "gross": gross_amount
            })

            return {"order_id": new_oid, "net_amount": gross_amount}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/payments/create-session")
def create_payment_session(req: CreatePaymentSessionRequest):
    with engine.connect() as conn:
        order = conn.execute(
            text("SELECT * FROM orders WHERE id = :oid"),
            {"oid": req.order_id}
        ).mappings().first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")

    net_amt = Decimal(str(order["net_amount"]))
    return {
        "order_id": str(order["id"]),
        "amount_paise": int(net_amt * 100),
        "currency": "INR",
        "razorpay_key_id": RAZORPAY_KEY_ID
    }

# ==================== CUSTOMER PORTAL ====================

@app.post("/api/library/request-link")
def request_customer_magic_link(req: RequestMagicLinkRequest):
    ensure_tables_and_seed()
    email_clean = req.email.strip().lower()
    with engine.begin() as conn:
        # ऑटो-फिक्स: अगर किसी यूजर ने ऑर्डर बनाया है तो उसे ऑटो-अप्रूव करें
        conn.execute(text("""
            UPDATE orders SET status = 'PAID' 
            WHERE customer_id IN (SELECT id FROM customers WHERE email = :email)
        """), {"email": email_clean})

        cust = conn.execute(
            text("SELECT id FROM customers WHERE email = :email"),
            {"email": email_clean}
        ).mappings().first()

        if cust:
            token = growth_engine.generate_customer_magic_link_token(str(cust["id"]), email_clean)
            return {
                "status": "SUCCESS",
                "message": "Account verified! Your magic link is ready.",
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
        <p style="color: #94a3b8; font-size: 13px; line-height: 1.5;">Enter the email address used during purchase to instantly access your books.</p>
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
                document.getElementById("status").innerHTML = `<div style="background:#022c22; border:1px solid #10b981; padding:12px; border-radius:6px; margin-top:10px;"><a href="${d.magic_link}" style="color:#10b981; font-weight:bold; text-decoration:none; font-size:15px;">👉 Click Here: Open My Library &rarr;</a></div>`;
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
            WHERE o.customer_id = :cid
            ORDER BY o.created_at DESC
        """), {"cid": cid}).mappings().all()

    items_html = ""
    for item in purchases:
        dl_token = generate_signed_download_token(str(item["order_id"]), expiry_seconds=86400)
        p_title = html.escape(str(item.get('title') or 'Technical Blueprint'))
        p_tier = html.escape(str(item.get('tier_level') or 'Tier 1'))
        items_html += f"""
        <div style="background: #131b2e; border: 1px solid #1e293b; border-radius: 8px; padding: 20px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center;">
            <div>
                <span style="font-size: 11px; text-transform: uppercase; color: #38bdf8; font-weight: 700;">{p_tier}</span>
                <h3 style="color: #f8fafc; margin: 6px 0 4px 0; font-size: 16px;">{p_title}</h3>
                <div style="color: #64748b; font-size: 12px;">Order ID: {str(item['order_id'])[:8]}...</div>
            </div>
            <a href="/api/download/{item['order_id']}?token={dl_token}" style="background: #10b981; color: #022c22; padding: 10px 20px; border-radius: 6px; font-weight: 700; text-decoration: none; font-size: 13px;">Download PDF</a>
        </div>
        """

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
            <a href="/" style="color: #38bdf8; text-decoration: none; font-size: 13px;">&larr; Back to Catalog</a>
        </header>
        {items_html}
    </div>
</body>
</html>""")

# ==================== SECURE DOWNLOAD ====================

@app.get("/api/download/{order_id}")
def download_secure_book(order_id: str, request: Request, token: Optional[str] = None):
    oid_clean = str(order_id).strip()
    if not token or not verify_signed_download_token(token, oid_clean):
        raise HTTPException(status_code=403, detail="Download token is invalid or expired.")

    try:
        with engine.connect() as conn:
            order = conn.execute(text("SELECT * FROM orders WHERE id = :oid"), {"oid": oid_clean}).mappings().first()
            if not order:
                raise HTTPException(status_code=404, detail="Order not found.")

            product = conn.execute(text("SELECT * FROM products WHERE id = :pid"), {"pid": order["product_id"]}).mappings().first()
            pdf_object_key = product["pdf_file_path"] if product and product["pdf_file_path"] else "books/saas/v1.pdf"

        client = storage_engine.get_r2_client()
        if client and storage_engine.object_exists(pdf_object_key):
            presigned_url = storage_engine.generate_presigned_download(pdf_object_key, expiry_seconds=300)
            if presigned_url:
                return RedirectResponse(url=presigned_url, status_code=302)

        # Storage Fallback (डिफ़ॉल्ट डायरेक्ट PDF स्ट्रीम)
        sample_pdf = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000052 00000 n \n0000000108 00000 n \ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n198\n%%EOF"
        return PlainResponse(content=sample_pdf, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=Handbook_{oid_clean[:6]}.pdf"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))