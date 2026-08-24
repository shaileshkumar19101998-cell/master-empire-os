import os
import math
import json
import time
import hmac
import hashlib
from decimal import Decimal
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from psycopg2.errors import UniqueViolation

import pdf_engine

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
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "test_webhook_secret_phase06_strictly_isolated")
DOWNLOAD_TOKEN_SECRET = os.getenv("DOWNLOAD_TOKEN_SECRET", "autonomous_os_secure_token_secret_default_key_2026")

app = FastAPI(title="Autonomous Business OS - Global Enterprise Engine", version="9.5.0")

os.makedirs(pdf_engine.PDF_STORAGE_DIR, exist_ok=True)
app.mount("/static/pdfs", StaticFiles(directory=pdf_engine.PDF_STORAGE_DIR), name="pdfs")

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

class ApprovalRequest(BaseModel):
    task_id: int
    decision: str

def generate_signed_download_token(order_id: str, expiry_seconds: int = 86400) -> str:
    exp_time = int(time.time()) + expiry_seconds
    version = "v1"
    oid_str = str(order_id).strip()
    raw_msg = f"{oid_str}:{exp_time}:{version}".encode("utf-8")
    sig = hmac.new(DOWNLOAD_TOKEN_SECRET.encode("utf-8"), raw_msg, hashlib.sha256).hexdigest()
    return f"{oid_str}.{exp_time}.{version}.{sig}"

def verify_signed_download_token(token: str, order_id: str) -> bool:
    try:
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
        expected_sig = hmac.new(DOWNLOAD_TOKEN_SECRET.encode("utf-8"), raw_msg, hashlib.sha256).hexdigest()
        return hmac.compare_digest(t_sig, expected_sig)
    except Exception:
        return False

@app.post("/api/orders/create")
def create_secure_order(req: CreateOrderRequest):
    try:
        import uuid
        with engine.begin() as conn:
            product = conn.execute(
                text("SELECT * FROM products WHERE id = :pid"), 
                {"pid": req.product_id}
            ).mappings().first()
            
            if not product:
                gross_amount = 999
            else:
                gross_amount = product["base_price_inr"]

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
    webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET", "").strip()
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

            if raw_fee is not None:
                gateway_fee = Decimal(str(raw_fee)) / Decimal("100.0")
            else:
                gateway_fee = Decimal("0.00")

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
def download_secure_book(order_id: str, token: Optional[str] = None):
    try:
        oid_clean = str(order_id).strip()
        with engine.connect() as conn:
            order = conn.execute(
                text("SELECT * FROM orders WHERE id = :oid"), 
                {"oid": oid_clean}
            ).mappings().first()
            
            if not order:
                raise HTTPException(status_code=404, detail="Order not found.")
            if order["status"] != "PAID":
                raise HTTPException(status_code=403, detail="Payment pending or incomplete. Access denied.")

            if token and not verify_signed_download_token(token, oid_clean):
                raise HTTPException(status_code=403, detail="Download token is invalid or expired.")

            product = conn.execute(
                text("SELECT * FROM products WHERE id = :pid"), 
                {"pid": order["product_id"]}
            ).mappings().first()
            
            pdf_rel_path = product["pdf_file_path"] if product and product["pdf_file_path"] else "default.pdf"

        clean_name = os.path.basename(pdf_rel_path)
        abs_path = os.path.join(pdf_engine.PDF_STORAGE_DIR, clean_name)
        if not os.path.exists(abs_path):
            abs_path = os.path.join(pdf_engine.PDF_STORAGE_DIR, "default.pdf")
            with open(abs_path, "wb") as f:
                f.write(b"%PDF-1.4 Mock Document Content")
            
        return FileResponse(abs_path, media_type="application/pdf", filename=clean_name)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))