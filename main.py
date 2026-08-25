import os
import json
import time
import hmac
import uuid
import hashlib
from typing import Optional
import urllib.request
import base64

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response as PlainResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
DOWNLOAD_SECRET = os.getenv("DOWNLOAD_SECRET") or os.getenv("DOWNLOAD_TOKEN_SECRET", "master_empire_secure_key_2026")

def get_engine():
    if DATABASE_URL:
        pg_url = DATABASE_URL
        if pg_url.startswith("postgres://"):
            pg_url = pg_url.replace("postgres://", "postgresql://", 1)
        try:
            test_engine = create_engine(pg_url, pool_pre_ping=True)
            with test_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return test_engine
        except Exception:
            pass
    return create_engine("sqlite:///./autonomous_local.db", connect_args={"check_same_thread": False})

engine = get_engine()

app = FastAPI(title="Autonomous Business OS - Direct Storage Engine", version="2.3.0")

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
    except Exception as e:
        print("DB Init Note:", e)

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

def generate_signed_token(order_id: str) -> str:
    exp_time = int(time.time()) + 900  # 15 मिनट एक्सपायरी
    msg = f"{order_id}:{exp_time}".encode("utf-8")
    sig = hmac.new(DOWNLOAD_SECRET.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return f"{order_id}.{exp_time}.{sig}"

def verify_signed_token(token: str, order_id: str) -> bool:
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
        #modal {{ display: none; margin-top: 24px; padding: 20px; background: #022c22; border: 1px solid #10b981; border-radius: 8px; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <span style="font-size: 11px; text-transform: uppercase; color: #38bdf8; font-weight: 700;">CLOUD ARCHITECTURE</span>
        <h2 style="color: #f8fafc; margin: 8px 0;">SaaS Architecture & Scale Handbook</h2>
        <p style="color: #94a3b8; font-size: 14px;">Price: ₹1 • Direct Instant Delivery</p>
        
        <label style="font-size: 13px; color: #cbd5e1;">Your Email Address:</label>
        <input type="email" id="email" placeholder="you@example.com" value="mohitkmr78p@gmail.com" required />

        <label style="font-size: 13px; color: #cbd5e1;">Coupon Code (Leave empty for ₹1 checkout, or use <b>SHAILJA</b> / <b>AKHIL</b>):</label>
        <input type="text" id="coupon" placeholder="Optional Coupon" />

        <button class="btn-pay" onclick="initiateCheckout()">Proceed to Checkout</button>

        <div id="modal">
            <h3 style="color: #10b981; margin: 0 0 8px 0;">🎉 Access Granted!</h3>
            <p style="color: #cbd5e1; font-size: 13px; margin-bottom: 16px;">Download token valid for 15 minutes.</p>
            <a id="download-btn" href="#" style="display: inline-block; background: #10b981; color: #022c22; padding: 12px 24px; border-radius: 6px; font-weight: 800; text-decoration: none; font-size: 15px;">📥 Download PDF Handbook</a>
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

                // 1. FREE FLOW
                if (!orderData.requires_payment) {{
                    document.getElementById("download-btn").href = orderData.download_url;
                    document.getElementById("modal").style.display = "block";
                    return;
                }}

                // 2. PAID FLOW
                const sessRes = await fetch("/api/payments/create-session", {{
                    method: "POST",
                    headers: {{ "Content-Type": "application/json" }},
                    body: JSON.stringify({{ order_id: orderData.order_id }})
                }});
                const sess = await sessRes.json();
                if (!sessRes.ok) {{
                    alert("Error: " + (sess.detail || "Unable to start Razorpay."));
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
                            alert("Verification failed.");
                        }}
                    }}
                }};
                const rzp = new Razorpay(options);
                rzp.open();
            }} catch (err) {{
                alert("Error: " + err.message);
            }}
        }}
    </script>
</body>
</html>""")

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

        try:
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO orders (id, customer_email, product_id, coupon_code, order_type, gross_amount, net_amount, status)
                    VALUES (:id, :email, :pid, :cpc, :otype, :gross, :net, :status)
                """), {
                    "id": new_oid, "email": clean_email, "pid": req.product_id,
                    "cpc": req.coupon_code, "otype": order_type,
                    "gross": gross_amount, "net": net_amount, "status": status
                })
        except Exception as dbe:
            print("DB Note:", dbe)

        download_url = None
        if not requires_payment:
            token = generate_signed_token(new_oid)
            download_url = f"/api/download/{new_oid}?token={token}"

        return {
            "order_id": new_oid,
            "requires_payment": requires_payment,
            "download_url": download_url
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/payments/create-session")
def create_payment_session(req: CreatePaymentSessionRequest):
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        raise HTTPException(status_code=500, detail="Razorpay Keys missing in Render Environment.")

    with engine.connect() as conn:
        order = conn.execute(text("SELECT * FROM orders WHERE id = :oid"), {"oid": req.order_id}).mappings().first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")

    amount_paise = int(float(order["net_amount"]) * 100)
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
        raise HTTPException(status_code=502, detail=f"Razorpay session failed: {str(e)}")

@app.post("/api/payments/verify")
def verify_payment_endpoint(req: VerifyPaymentRequest):
    if not RAZORPAY_KEY_SECRET:
        raise HTTPException(status_code=500, detail="Razorpay Secret missing.")

    msg = f"{req.razorpay_order_id}|{req.razorpay_payment_id}".encode("utf-8")
    expected_signature = hmac.new(RAZORPAY_KEY_SECRET.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(req.razorpay_signature, expected_signature):
        raise HTTPException(status_code=400, detail="Invalid signature.")

    with engine.begin() as conn:
        conn.execute(text("UPDATE orders SET status = 'PAID' WHERE id = :id"), {"id": req.order_id})
        conn.execute(text("""
            INSERT INTO payments (order_id, payment_method, transaction_ref, amount, currency, status)
            VALUES (:oid, 'razorpay', :tx_ref, 1.0, 'INR', 'captured')
            ON CONFLICT (transaction_ref) DO NOTHING
        """), {"oid": req.order_id, "tx_ref": req.razorpay_payment_id})
        conn.execute(text("""
            INSERT INTO revenue_ledger (transaction_ref, gross_amount, gateway_fee, net_revenue, currency)
            VALUES (:tx_ref, 1.0, 0.0, 1.0, 'INR')
            ON CONFLICT (transaction_ref) DO NOTHING
        """), {"tx_ref": req.razorpay_payment_id})

    token = generate_signed_token(req.order_id)
    return {
        "status": "PAID",
        "order_id": req.order_id,
        "download_url": f"/api/download/{req.order_id}?token={token}"
    }

@app.post("/api/payments/webhook")
async def razorpay_webhook(request: Request):
    if not RAZORPAY_WEBHOOK_SECRET:
        return Response(content=json.dumps({"error": "No webhook secret"}), status_code=500, media_type="application/json")

    raw_body = await request.body()
    received_signature = request.headers.get("X-Razorpay-Signature", "")

    expected_signature = hmac.new(RAZORPAY_WEBHOOK_SECRET.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    if not received_signature or not hmac.compare_digest(received_signature, expected_signature):
        return Response(content=json.dumps({"error": "Invalid signature"}), status_code=401, media_type="application/json")

    try:
        payload = json.loads(raw_body.decode("utf-8"))
        event_id = request.headers.get("X-Razorpay-Event-Id") or payload.get("event_id") or payload.get("id")

        with engine.begin() as conn:
            if event_id:
                exists = conn.execute(text("SELECT event_id FROM processed_webhook_events WHERE event_id = :eid"), {"eid": event_id}).mappings().first()
                if exists:
                    return Response(content=json.dumps({"status": "ALREADY_PROCESSED"}), status_code=200, media_type="application/json")
                conn.execute(text("INSERT INTO processed_webhook_events (event_id, event_type) VALUES (:eid, :etype) ON CONFLICT (event_id) DO NOTHING"), {"eid": event_id, "etype": payload.get("event", "unknown")})

            if payload.get("event") == "payment.captured":
                payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
                payment_id = payment_entity.get("id")
                rzp_order_id = payment_entity.get("order_id")
                internal_oid = payment_entity.get("notes", {}).get("order_id")

                order = None
                if internal_oid:
                    order = conn.execute(text("SELECT * FROM orders WHERE id = :oid"), {"oid": internal_oid}).mappings().first()
                if not order and rzp_order_id:
                    order = conn.execute(text("SELECT * FROM orders WHERE razorpay_order_id = :rzp_oid"), {"rzp_oid": rzp_order_id}).mappings().first()

                if order:
                    target_oid = order["id"]
                    conn.execute(text("UPDATE orders SET status = 'PAID' WHERE id = :oid"), {"oid": target_oid})
                    conn.execute(text("""
                        INSERT INTO payments (order_id, payment_method, transaction_ref, amount, currency, status)
                        VALUES (:oid, 'razorpay_webhook', :tx_ref, 1.0, 'INR', 'captured')
                        ON CONFLICT (transaction_ref) DO NOTHING
                    """), {"oid": target_oid, "tx_ref": payment_id})
                    conn.execute(text("""
                        INSERT INTO revenue_ledger (transaction_ref, gross_amount, gateway_fee, net_revenue, currency)
                        VALUES (:tx_ref, 1.0, 0.0, 1.0, 'INR')
                        ON CONFLICT (transaction_ref) DO NOTHING
                    """), {"tx_ref": payment_id})

        return Response(content=json.dumps({"status": "SETTLED"}), status_code=200, media_type="application/json")
    except Exception as e:
        return Response(content=json.dumps({"error": str(e)}), status_code=500, media_type="application/json")

@app.get("/api/download/{order_id}")
def download_secure_book(order_id: str, token: Optional[str] = None):
    oid_clean = str(order_id).strip()
    if not token or not verify_signed_token(token, oid_clean):
        raise HTTPException(status_code=403, detail="Invalid or expired download link.")

    with engine.connect() as conn:
        order = conn.execute(text("SELECT status FROM orders WHERE id = :oid"), {"oid": oid_clean}).mappings().first()
        if not order or order["status"] != "PAID":
            raise HTTPException(status_code=403, detail="Order not settled.")

    pdf_path = "books/saas/v1.pdf"
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        return PlainResponse(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=SaaS_Architecture_Handbook.pdf"}
        )

    raise HTTPException(status_code=503, detail="PDF asset not found.")