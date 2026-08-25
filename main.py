import os
import json
import time
import hmac
import uuid
import hashlib
from typing import Optional, List
import urllib.request
import base64

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response as PlainResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
DOWNLOAD_SECRET = os.getenv("DOWNLOAD_SECRET") or os.getenv("DOWNLOAD_TOKEN_SECRET")
MAGIC_LINK_SECRET = os.getenv("MAGIC_LINK_SECRET") or DOWNLOAD_SECRET

AUTONOMY_LEVEL = 2

if not DOWNLOAD_SECRET:
    raise RuntimeError("CRITICAL: DOWNLOAD_SECRET environment variable is missing. Startup aborted (Fail-Closed).")

def init_production_engine() -> Engine:
    if not DATABASE_URL:
        raise RuntimeError("CRITICAL CONFIGURATION ERROR: DATABASE_URL is missing. Application refuses to start with SQLite in production.")
    
    pg_url = DATABASE_URL
    if pg_url.startswith("postgres://"):
        pg_url = pg_url.replace("postgres://", "postgresql://", 1)
        
    try:
        engine = create_engine(pg_url, pool_pre_ping=True, pool_size=5, max_overflow=10)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as e:
        raise RuntimeError(f"CRITICAL DATABASE CONNECTION FAILURE: Unable to connect to PostgreSQL: {str(e)}")

engine = init_production_engine()

app = FastAPI(title="Autonomous Business OS - Production Baseline", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def init_db():
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY,
                    slug VARCHAR(120) UNIQUE,
                    title VARCHAR(255),
                    base_price_inr INTEGER DEFAULT 1,
                    pdf_file_path VARCHAR(255) DEFAULT 'books/saas/v1.pdf'
                );
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS orders (
                    id VARCHAR(64) PRIMARY KEY,
                    customer_email VARCHAR(255),
                    product_id INTEGER,
                    coupon_code VARCHAR(50),
                    order_type VARCHAR(50) DEFAULT 'PAID',
                    gross_amount NUMERIC DEFAULT 1,
                    net_amount NUMERIC DEFAULT 1,
                    currency VARCHAR(10) DEFAULT 'INR',
                    status VARCHAR(50) DEFAULT 'PENDING',
                    razorpay_order_id VARCHAR(100) UNIQUE,
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
                CREATE TABLE IF NOT EXISTS processed_webhook_events (
                    event_id VARCHAR(120) PRIMARY KEY,
                    event_type VARCHAR(64),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS magic_link_tokens (
                    token_hash VARCHAR(64) PRIMARY KEY,
                    customer_email VARCHAR(255),
                    expires_at BIGINT,
                    consumed_at TIMESTAMP NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            conn.execute(text("""
                INSERT INTO products (id, slug, title, base_price_inr, pdf_file_path)
                VALUES (1, 'saas-scale-handbook', 'SaaS Architecture & Scale Handbook', 1, 'books/saas/v1.pdf')
                ON CONFLICT (id) DO NOTHING;
            """))
    except Exception as e:
        print("Schema init notice:", str(e))

def generate_signed_download_token(order_id: str) -> str:
    exp_time = int(time.time()) + 900
    msg = f"{order_id}:{exp_time}".encode("utf-8")
    sig = hmac.new(DOWNLOAD_SECRET.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return f"{order_id}.{exp_time}.{sig}"

def verify_signed_download_token(token: str, order_id: str) -> bool:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return False
        t_oid, t_exp, t_sig = parts
        if t_oid != str(order_id).strip() or time.time() > int(t_exp):
            return False
        msg = f"{order_id}:{t_exp}".encode("utf-8")
        expected_sig = hmac.new(DOWNLOAD_SECRET.encode("utf-8"), msg, hashlib.sha256).hexdigest()
        return hmac.compare_digest(t_sig, expected_sig)
    except Exception:
        return False

def generate_magic_link_token(email: str) -> str:
    clean_email = email.strip().lower()
    exp_time = int(time.time()) + 900
    raw_token = f"ml_{uuid.uuid4().hex}_{int(time.time())}"
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO magic_link_tokens (token_hash, customer_email, expires_at)
            VALUES (:thash, :email, :exp)
        """), {"thash": token_hash, "email": clean_email, "exp": exp_time})
        
    msg = f"{raw_token}:{exp_time}".encode("utf-8")
    sig = hmac.new(MAGIC_LINK_SECRET.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return f"{raw_token}.{exp_time}.{sig}"

def verify_and_consume_magic_link(token: str) -> Optional[str]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        raw_token, exp_time, sig = parts
        
        if time.time() > int(exp_time):
            return None
            
        msg = f"{raw_token}:{exp_time}".encode("utf-8")
        expected_sig = hmac.new(MAGIC_LINK_SECRET.encode("utf-8"), msg, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
            
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        
        with engine.begin() as conn:
            rec = conn.execute(text("""
                SELECT customer_email, consumed_at, expires_at 
                FROM magic_link_tokens 
                WHERE token_hash = :thash
            """), {"thash": token_hash}).mappings().first()
            
            if not rec or rec["consumed_at"] is not None or time.time() > int(rec["expires_at"]):
                return None
                
            conn.execute(text("""
                UPDATE magic_link_tokens 
                SET consumed_at = CURRENT_TIMESTAMP 
                WHERE token_hash = :thash
            """), {"thash": token_hash})
            
            return rec["customer_email"]
    except Exception:
        return None

class CreateOrderRequest(BaseModel):
    product_id: int = 1
    customer_email: str
    coupon_code: Optional[str] = None

class CreatePaymentSessionRequest(BaseModel):
    order_id: str

class VerifyPaymentRequest(BaseModel):
    order_id: str
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str

class RequestLibraryLinkRequest(BaseModel):
    customer_email: str

@app.get("/", response_class=HTMLResponse)
def get_storefront():
    init_db()
    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Autonomous OS — Digital Catalog</title>
    <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 40px 20px; }}
        .container {{ max-width: 600px; margin: 0 auto; background: #1e293b; padding: 32px; border-radius: 12px; border: 1px solid #334155; }}
        input {{ width: 100%; box-sizing: border-box; padding: 12px; border-radius: 6px; border: 1px solid #475569; background: #0f172a; color: #fff; margin: 8px 0 16px 0; }}
        .btn-pay {{ width: 100%; background: #2563eb; color: #ffffff; padding: 14px; border: none; border-radius: 8px; font-weight: 800; font-size: 16px; cursor: pointer; }}
        .nav-link {{ display: block; text-align: center; margin-top: 18px; color: #38bdf8; font-size: 14px; text-decoration: none; }}
        #modal {{ display: none; margin-top: 24px; padding: 20px; background: #022c22; border: 1px solid #10b981; border-radius: 8px; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <span style="font-size: 11px; text-transform: uppercase; color: #38bdf8; font-weight: 700;">CLOUD ARCHITECTURE</span>
        <h2 style="color: #f8fafc; margin: 8px 0;">SaaS Architecture & Scale Handbook</h2>
        <p style="color: #94a3b8; font-size: 14px;">Price: ₹1 • Instant Verified Digital Asset Delivery</p>
        
        <label style="font-size: 13px; color: #cbd5e1;">Your Email Address:</label>
        <input type="email" id="email" placeholder="you@example.com" value="customer@example.com" required />

        <label style="font-size: 13px; color: #cbd5e1;">Coupon Code (Leave empty for ₹1 checkout, or use <b>SHAILJA</b> / <b>AKHIL</b>):</label>
        <input type="text" id="coupon" placeholder="Optional Coupon" />

        <button class="btn-pay" onclick="initiateCheckout()">Proceed to Checkout</button>

        <a href="/library" class="nav-link">📂 Access Your Existing Purchases (Customer Library)</a>

        <div id="modal">
            <h3 style="color: #10b981; margin: 0 0 8px 0;">🎉 Access Granted!</h3>
            <p style="color: #cbd5e1; font-size: 13px; margin-bottom: 16px;">Download token valid for 15 minutes.</p>
            <a id="download-btn" href="#" style="display: inline-block; background: #10b981; color: #022c22; padding: 12px 24px; border-radius: 6px; font-weight: 800; text-decoration: none; font-size: 15px;">📥 Download Genuine PDF Handbook</a>
        </div>
    </div>
    <script>
        async function initiateCheckout() {{
            const email = document.getElementById("email").value;
            const coupon = document.getElementById("coupon").value;
            if(!email || !email.includes("@")) {{ alert("Please enter a valid email."); return; }}

            try {{
                const res = await fetch("/api/orders/create", {{
                    method: "POST",
                    headers: {{ "Content-Type": "application/json" }},
                    body: JSON.stringify({{ product_id: 1, customer_email: email, coupon_code: coupon }})
                }});
                const orderData = await res.json();

                if (!orderData.requires_payment) {{
                    document.getElementById("download-btn").href = orderData.download_url;
                    document.getElementById("modal").style.display = "block";
                    return;
                }}

                const sessRes = await fetch("/api/payments/create-session", {{
                    method: "POST",
                    headers: {{ "Content-Type": "application/json" }},
                    body: JSON.stringify({{ order_id: orderData.order_id }})
                }});
                const sess = await sessRes.json();
                if (!sessRes.ok) {{
                    alert("Error: " + (sess.detail || "Unable to initialize payment session."));
                    return;
                }}

                const options = {{
                    "key": sess.razorpay_key_id,
                    "amount": sess.amount_paise,
                    "currency": "INR",
                    "name": "Autonomous OS",
                    "description": "SaaS Architecture Handbook",
                    "order_id": sess.razorpay_order_id,
                    "prefill": {{ "email": email }},
                    "theme": {{ "color": "#2563eb" }},
                    "handler": async function (response) {{
                        const verifyRes = await fetch("/api/payments/verify", {{
                            method: "POST",
                            headers: {{ "Content-Type": "application/json" }},
                            body: JSON.stringify({{
                                order_id: orderData.order_id,
                                razorpay_payment_id: response.razorpay_payment_id,
                                razorpay_order_id: response.razorpay_order_id,
                                razorpay_signature: response.razorpay_signature
                            }})
                        }});
                        const verifyData = await verifyRes.json();
                        if(verifyData.download_url) {{
                            document.getElementById("download-btn").href = verifyData.download_url;
                            document.getElementById("modal").style.display = "block";
                        }} else {{
                            alert("Verification failed: " + (verifyData.detail || "Error"));
                        }}
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

@app.get("/library", response_class=HTMLResponse)
def get_customer_library(token: Optional[str] = None):
    init_db()
    verified_email = None
    purchases = []
    
    if token:
        verified_email = verify_and_consume_magic_link(token)
        if verified_email:
            with engine.connect() as conn:
                rows = conn.execute(text("""
                    SELECT o.id as order_id, o.created_at, o.order_type, p.title 
                    FROM orders o
                    LEFT JOIN products p ON o.product_id = p.id
                    WHERE o.customer_email = :email AND o.status = 'PAID'
                    ORDER BY o.created_at DESC
                """), {"email": verified_email}).mappings().all()
                
                for r in rows:
                    t = generate_signed_download_token(r["order_id"])
                    purchases.append({
                        "order_id": r["order_id"],
                        "title": r["title"] or "SaaS Architecture Handbook",
                        "type": r["order_type"],
                        "download_url": f"/api/download/{r['order_id']}?token={t}"
                    })

    purchases_html = ""
    if verified_email:
        if purchases:
            for p in purchases:
                purchases_html += f"""
                <div style="background:#0f172a; border:1px solid #334155; padding:16px; border-radius:8px; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <div style="font-weight:700; color:#f8fafc;">{p['title']}</div>
                        <div style="font-size:12px; color:#94a3b8;">Order: {p['order_id']} | Type: {p['type']}</div>
                    </div>
                    <a href="{p['download_url']}" style="background:#10b981; color:#022c22; text-decoration:none; padding:8px 16px; border-radius:6px; font-weight:700; font-size:13px;">📥 Download</a>
                </div>
                """
        else:
            purchases_html = "<p style='color:#94a3b8;'>No paid or authorized purchases found for this email address.</p>"

    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Customer Asset Library — Autonomous OS</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 40px 20px; }}
        .container {{ max-width: 650px; margin: 0 auto; background: #1e293b; padding: 32px; border-radius: 12px; border: 1px solid #334155; }}
        input {{ width: 100%; box-sizing: border-box; padding: 12px; border-radius: 6px; border: 1px solid #475569; background: #0f172a; color: #fff; margin: 8px 0 16px 0; }}
        .btn {{ width: 100%; background: #0284c7; color: #ffffff; padding: 12px; border: none; border-radius: 6px; font-weight: 700; cursor: pointer; }}
    </style>
</head>
<body>
    <div class="container">
        <h2 style="margin-top:0; color:#f8fafc;">📂 Customer Digital Asset Library</h2>
        
        {f"<p style='color:#10b981;'>Authenticated Session: <b>{verified_email}</b></p>" if verified_email else """
        <p style="color:#94a3b8; font-size:14px;">Enter your purchase email to receive a secure, 1-time 15-minute access link.</p>
        <input type="email" id="lib_email" placeholder="customer@example.com" />
        <button class="btn" onclick="requestLink()">Send Library Access Link</button>
        <div id="status_msg" style="display:none; margin-top:14px; padding:12px; border-radius:6px; font-size:13px;"></div>
        """}

        <div style="margin-top:24px;">
            {purchases_html}
        </div>
        
        <div style="text-align:center; margin-top:24px;">
            <a href="/" style="color:#38bdf8; text-decoration:none; font-size:13px;">← Back to Storefront Catalog</a>
        </div>
    </div>
    <script>
        async function requestLink() {{
            const email = document.getElementById('lib_email').value;
            if(!email || !email.includes('@')) {{ alert('Please enter a valid email.'); return; }}
            const btn = event.target;
            btn.disabled = true;
            btn.innerText = 'Processing...';
            try {{
                const res = await fetch('/api/library/request-link', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ customer_email: email }})
                }});
                const data = await res.json();
                const msgBox = document.getElementById('status_msg');
                msgBox.style.display = 'block';
                if(data.access_url) {{
                    msgBox.style.background = '#022c22';
                    msgBox.style.color = '#10b981';
                    msgBox.innerHTML = 'Direct Access Token Ready (15m TTL): <a style="color:#38bdf8; font-weight:700;" href="' + data.access_url + '">Click here to open your library</a>';
                }} else {{
                    msgBox.style.background = '#0f172a';
                    msgBox.style.color = '#94a3b8';
                    msgBox.innerText = data.message;
                }}
            }} catch(err) {{
                alert('Request failed: ' + err.message);
            }} finally {{
                btn.disabled = false;
                btn.innerText = 'Send Library Access Link';
            }}
        }}
    </script>
</body>
</html>""")

@app.post("/api/library/request-link")
def request_library_magic_link(req: RequestLibraryLinkRequest):
    init_db()
    clean_email = req.customer_email.strip().lower()
    
    with engine.connect() as conn:
        has_orders = conn.execute(text("""
            SELECT id FROM orders WHERE customer_email = :email AND status = 'PAID' LIMIT 1
        """), {"email": clean_email}).mappings().first()

    if not has_orders:
        return {"status": "SUCCESS", "message": "If valid purchases exist for this address, access instructions have been issued."}

    token = generate_magic_link_token(clean_email)
    access_url = f"/library?token={token}"
    return {
        "status": "SUCCESS",
        "message": "Library access link generated (15-min validity).",
        "access_url": access_url
    }

@app.post("/api/orders/create")
def create_secure_order(req: CreateOrderRequest):
    init_db()
    try:
        clean_email = req.customer_email.strip().lower()
        gross_amount = 1
        discount_amount = 0
        order_type = "PAID"
        requires_payment = True

        if req.coupon_code:
            clean_code = req.coupon_code.strip().upper()
            if clean_code in ["SHAILJA", "AKHIL"]:
                discount_amount = 1
                order_type = "FREE"
                requires_payment = False

        net_amount = gross_amount - discount_amount
        status = "PAID" if not requires_payment else "PENDING"
        new_oid = f"ord_{uuid.uuid4().hex[:12]}"

        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO orders (id, customer_email, product_id, coupon_code, order_type, gross_amount, net_amount, status)
                VALUES (:id, :email, :pid, :cpc, :otype, :gross, :net, :status)
            """), {
                "id": new_oid, "email": clean_email, "pid": req.product_id,
                "cpc": req.coupon_code, "otype": order_type,
                "gross": gross_amount, "net": net_amount, "status": status
            })
            
            if not requires_payment:
                conn.execute(text("""
                    INSERT INTO revenue_ledger (transaction_ref, gross_amount, gateway_fee, net_revenue, currency)
                    VALUES (:tx_ref, 0.0, 0.0, 0.0, 'INR')
                    ON CONFLICT (transaction_ref) DO NOTHING
                """), {"tx_ref": f"free_{new_oid}"})

        download_url = None
        if not requires_payment:
            token = generate_signed_download_token(new_oid)
            download_url = f"/api/download/{new_oid}?token={token}"

        return {
            "order_id": new_oid,
            "requires_payment": requires_payment,
            "gross_amount": gross_amount,
            "net_amount": net_amount,
            "download_url": download_url
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/payments/create-session")
def create_payment_session(req: CreatePaymentSessionRequest):
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        raise HTTPException(status_code=500, detail="Razorpay API credentials not configured in environment.")

    with engine.connect() as conn:
        order = conn.execute(text("SELECT * FROM orders WHERE id = :oid"), {"oid": req.order_id}).mappings().first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")
    if order["status"] == "PAID":
        raise HTTPException(status_code=400, detail="Order is already paid.")

    amount_paise = int(float(order["net_amount"]) * 100)
    if amount_paise <= 0:
        raise HTTPException(status_code=400, detail="Order requires zero payment; bypass gate.")

    url = "https://api.razorpay.com/v1/orders"
    payload = json.dumps({
        "amount": amount_paise,
        "currency": "INR",
        "receipt": req.order_id,
        "notes": {"order_id": req.order_id}
    }).encode("utf-8")

    auth_str = base64.b64encode(f"{RAZORPAY_KEY_ID}:{RAZORPAY_KEY_SECRET}".encode("utf-8")).decode("utf-8")
    req_obj = urllib.request.Request(url, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": f"Basic {auth_str}"
    })

    try:
        with urllib.request.urlopen(req_obj) as resp:
            rzp_data = json.loads(resp.read().decode("utf-8"))
            rzp_order_id = rzp_data["id"]

        with engine.begin() as conn:
            conn.execute(text("UPDATE orders SET razorpay_order_id = :rzp_oid WHERE id = :oid"), {
                "rzp_oid": rzp_order_id, "oid": req.order_id
            })

        return {
            "order_id": req.order_id,
            "razorpay_order_id": rzp_order_id,
            "amount_paise": amount_paise,
            "razorpay_key_id": RAZORPAY_KEY_ID
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Razorpay session creation failed: {str(e)}")

@app.post("/api/payments/verify")
def verify_payment_endpoint(req: VerifyPaymentRequest):
    if not RAZORPAY_KEY_SECRET:
        raise HTTPException(status_code=500, detail="Razorpay Secret not configured.")

    msg = f"{req.razorpay_order_id}|{req.razorpay_payment_id}".encode("utf-8")
    expected_signature = hmac.new(RAZORPAY_KEY_SECRET.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(req.razorpay_signature, expected_signature):
        raise HTTPException(status_code=400, detail="Payment signature verification failed.")

    with engine.begin() as conn:
        order = conn.execute(
            text("SELECT * FROM orders WHERE id = :oid AND razorpay_order_id = :rzp_oid"),
            {"oid": req.order_id, "rzp_oid": req.razorpay_order_id}
        ).mappings().first()

        if not order:
            raise HTTPException(status_code=400, detail="Order and Gateway Order ID mismatch.")

        conn.execute(text("UPDATE orders SET status = 'PAID' WHERE id = :id"), {"id": req.order_id})
        conn.execute(text("""
            INSERT INTO payments (order_id, payment_method, transaction_ref, amount, currency, status)
            VALUES (:oid, 'razorpay', :tx_ref, :amt, 'INR', 'captured')
            ON CONFLICT (transaction_ref) DO NOTHING
        """), {"oid": req.order_id, "tx_ref": req.razorpay_payment_id, "amt": float(order["net_amount"])})
        
        conn.execute(text("""
            INSERT INTO revenue_ledger (transaction_ref, gross_amount, gateway_fee, net_revenue, currency)
            VALUES (:tx_ref, :amt, 0.0, :amt, 'INR')
            ON CONFLICT (transaction_ref) DO NOTHING
        """), {"tx_ref": req.razorpay_payment_id, "amt": float(order["net_amount"])})

    token = generate_signed_download_token(req.order_id)
    return {
        "status": "PAID",
        "order_id": req.order_id,
        "download_url": f"/api/download/{req.order_id}?token={token}"
    }

@app.post("/api/payments/webhook")
async def razorpay_webhook(request: Request):
    if not RAZORPAY_WEBHOOK_SECRET:
        return Response(content=json.dumps({"error": "Webhook secret unconfigured"}), status_code=500, media_type="application/json")

    raw_body = await request.body()
    received_signature = request.headers.get("X-Razorpay-Signature", "")

    expected_signature = hmac.new(RAZORPAY_WEBHOOK_SECRET.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    if not received_signature or not hmac.compare_digest(received_signature, expected_signature):
        return Response(content=json.dumps({"error": "Invalid Signature"}), status_code=401, media_type="application/json")

    try:
        payload = json.loads(raw_body.decode("utf-8"))
        event_id = request.headers.get("X-Razorpay-Event-Id") or payload.get("event_id") or payload.get("id")

        with engine.begin() as conn:
            if event_id:
                already_processed = conn.execute(
                    text("SELECT event_id FROM processed_webhook_events WHERE event_id = :eid"),
                    {"eid": event_id}
                ).mappings().first()

                if already_processed:
                    return Response(content=json.dumps({"status": "EVENT_ALREADY_PROCESSED"}), status_code=200, media_type="application/json")

                conn.execute(
                    text("INSERT INTO processed_webhook_events (event_id, event_type) VALUES (:eid, :etype) ON CONFLICT (event_id) DO NOTHING"),
                    {"eid": event_id, "etype": payload.get("event", "unknown")}
                )

            if payload.get("event") == "payment.captured":
                payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
                payment_id = payment_entity.get("id")
                rzp_order_id = payment_entity.get("order_id")
                internal_order_id = payment_entity.get("notes", {}).get("order_id")

                order = None
                if internal_order_id:
                    order = conn.execute(
                        text("SELECT * FROM orders WHERE id = :oid"),
                        {"oid": internal_order_id}
                    ).mappings().first()
                if not order and rzp_order_id:
                    order = conn.execute(
                        text("SELECT * FROM orders WHERE razorpay_order_id = :rzp_oid"),
                        {"rzp_oid": rzp_order_id}
                    ).mappings().first()

                if order:
                    target_oid = order["id"]
                    order_amount = float(order["net_amount"])
                    conn.execute(text("UPDATE orders SET status = 'PAID' WHERE id = :oid"), {"oid": target_oid})
                    conn.execute(text("""
                        INSERT INTO payments (order_id, payment_method, transaction_ref, amount, currency, status)
                        VALUES (:oid, 'razorpay_webhook', :tx_ref, :amt, 'INR', 'captured')
                        ON CONFLICT (transaction_ref) DO NOTHING
                    """), {"oid": target_oid, "tx_ref": payment_id, "amt": order_amount})
                    conn.execute(text("""
                        INSERT INTO revenue_ledger (transaction_ref, gross_amount, gateway_fee, net_revenue, currency)
                        VALUES (:tx_ref, :amt, 0.0, :amt, 'INR')
                        ON CONFLICT (transaction_ref) DO NOTHING
                    """), {"tx_ref": payment_id, "amt": order_amount})

        return Response(content=json.dumps({"status": "SETTLED"}), status_code=200, media_type="application/json")
    except Exception as e:
        return Response(content=json.dumps({"error": str(e)}), status_code=500, media_type="application/json")

@app.get("/api/download/{order_id}")
def download_secure_book(order_id: str, token: Optional[str] = None):
    oid_clean = str(order_id).strip()
    
    if not token or not verify_signed_download_token(token, oid_clean):
        raise HTTPException(status_code=403, detail="Download token is invalid or expired (15-min limit).")

    with engine.connect() as conn:
        order = conn.execute(text("SELECT status FROM orders WHERE id = :oid"), {"oid": oid_clean}).mappings().first()
        if not order or order["status"] != "PAID":
            raise HTTPException(status_code=403, detail="Order authorization check failed: order is not marked as PAID.")

    pdf_path = "books/saas/v1.pdf"
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        return PlainResponse(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=SaaS_Architecture_Handbook.pdf"}
        )

    raise HTTPException(status_code=503, detail="Genuine asset repository unavailable. Dummy fallbacks are permanently disabled.")

@app.post("/api/admin/governance/override")
def financial_override_guard():
    if AUTONOMY_LEVEL >= 2:
        raise HTTPException(
            status_code=403, 
            detail="HTTP 403 Forbidden: Level 2 Autonomy Enforced. Autonomous financial overrides and manual price bypassing are strictly prohibited."
        )
    return {"status": "ALLOWED"}

# ==============================================================================
# PHASE 3 ROUTER MOUNTING (MODULAR & NON-DESTRUCTIVE)
# ==============================================================================
try:
    from phase3_router import setup_phase3_routes
    app.include_router(setup_phase3_routes(engine))
except Exception as p3_err:
    print(f"Phase 3 Router Warning: {str(p3_err)}")