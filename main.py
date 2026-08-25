import os
import math
import html
import json
import time
import hmac
import uuid
import hashlib
from decimal import Decimal
from typing import Optional
from collections import defaultdict

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, Response as PlainResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

import storage_engine
import growth_engine
import ai_engine

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")

def get_production_engine():
    if DATABASE_URL:
        pg_url = DATABASE_URL
        if pg_url.startswith("postgres://"):
            pg_url = pg_url.replace("postgres://", "postgresql://", 1)
        if "sslmode" not in pg_url and "localhost" not in pg_url:
            pg_url += "?sslmode=require" if "?" not in pg_url else "&sslmode=require"
        return create_engine(pg_url, pool_pre_ping=True, connect_args={"connect_timeout": 10})
    
    return create_engine("sqlite:///./autonomous_local.db", connect_args={"check_same_thread": False})

engine = get_production_engine()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_test_placeholder")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
DOWNLOAD_TOKEN_SECRET = os.getenv("DOWNLOAD_TOKEN_SECRET", "master_empire_download_secret_2026")

app = FastAPI(title="Autonomous Business OS - Global Enterprise Engine", version="2.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def ensure_tables_and_seed():
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
            INSERT INTO products (slug, title, tier_level, target_niche, base_price_inr, base_price_usd, pdf_file_path, status)
            VALUES ('saas-architecture-handbook', 'SaaS Architecture & Scale Handbook', 'Tier 1', 'Cloud Architecture', 1, 1, 'books/saas/v1.pdf', 'ACTIVE')
            ON CONFLICT (slug) DO UPDATE SET base_price_inr = 1, status = 'ACTIVE';
        """))
        conn.execute(text("""
            INSERT INTO coupons (code, discount_type, discount_value, requires_payment, is_active)
            VALUES 
                ('SHAILJA', 'PERCENT', 100, 0, 1),
                ('AKHIL', 'PERCENT', 100, 0, 1)
            ON CONFLICT (code) DO UPDATE SET discount_value = 100, requires_payment = 0, is_active = 1;
        """))

class CreateOrderRequest(BaseModel):
    product_id: int
    customer_email: str
    coupon_code: Optional[str] = None

class RequestMagicLinkRequest(BaseModel):
    email: str

def generate_signed_download_token(order_id: str, expiry_seconds: int = 86400) -> str:
    secret = DOWNLOAD_TOKEN_SECRET
    exp_time = int(time.time()) + expiry_seconds
    version = "v1"
    oid_str = str(order_id).strip()
    raw_msg = f"{oid_str}:{exp_time}:{version}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), raw_msg, hashlib.sha256).hexdigest()
    return f"{oid_str}.{exp_time}.{version}.{sig}"

def verify_signed_download_token(token: str, order_id: str) -> bool:
    try:
        secret = DOWNLOAD_TOKEN_SECRET
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

@app.get("/", response_class=HTMLResponse)
def get_storefront():
    ensure_tables_and_seed()
    return HTMLResponse("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Autonomous OS — Digital Publishing Catalog</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 40px 20px; }
        .container { max-width: 650px; margin: 0 auto; background: #1e293b; padding: 32px; border-radius: 12px; border: 1px solid #334155; }
        input { width: 100%; box-sizing: border-box; padding: 12px; border-radius: 6px; border: 1px solid #475569; background: #0f172a; color: #fff; margin: 8px 0 16px 0; }
        button { width: 100%; background: #10b981; color: #022c22; padding: 14px; border: none; border-radius: 8px; font-weight: 800; font-size: 16px; cursor: pointer; }
        #modal { display: none; margin-top: 24px; padding: 20px; background: #022c22; border: 1px solid #10b981; border-radius: 8px; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <span style="font-size: 11px; text-transform: uppercase; color: #38bdf8; font-weight: 700;">CLOUD ARCHITECTURE</span>
        <h2 style="color: #f8fafc; margin: 8px 0;">SaaS Architecture & Scale Handbook</h2>
        <p style="color: #94a3b8; font-size: 14px;">Tier 1 Production Blueprint • Instant Access</p>
        
        <label style="font-size: 13px; color: #cbd5e1;">Your Email Address:</label>
        <input type="email" id="email" placeholder="you@example.com" value="mohitkmr78p@gmail.com" required />

        <label style="font-size: 13px; color: #cbd5e1;">Coupon / Access Code (Use <b>SHAILJA</b> for 100% Free):</label>
        <input type="text" id="coupon" value="SHAILJA" placeholder="Enter coupon code" />

        <button onclick="checkout()">Unlock & Download E-Book</button>

        <div id="modal">
            <h3 style="color: #10b981; margin: 0 0 8px 0;">🎉 Access Granted!</h3>
            <p style="color: #cbd5e1; font-size: 13px; margin-bottom: 16px;">Your authentic PDF is ready for instant download.</p>
            <a id="download-btn" href="#" style="display: inline-block; background: #10b981; color: #022c22; padding: 12px 24px; border-radius: 6px; font-weight: 800; text-decoration: none; font-size: 15px;">📥 Download PDF Now</a>
        </div>
    </div>
    <script>
        async function checkout() {
            const email = document.getElementById("email").value;
            const coupon = document.getElementById("coupon").value;
            if(!email || !email.includes("@")) { alert("Please enter a valid email."); return; }

            const res = await fetch("/api/orders/create", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ product_id: 1, customer_email: email, coupon_code: coupon })
            });
            const data = await res.json();
            if(data.download_url) {
                document.getElementById("download-btn").href = data.download_url;
                document.getElementById("modal").style.display = "block";
            } else {
                alert("Payment required or invalid code.");
            }
        }
    </script>
</body>
</html>""")

@app.post("/api/orders/create")
def create_secure_order(req: CreateOrderRequest):
    ensure_tables_and_seed()
    try:
        clean_email = req.customer_email.strip().lower()
        with engine.begin() as conn:
            product = conn.execute(text("SELECT * FROM products WHERE id = :pid"), {"pid": req.product_id}).mappings().first()
            gross_amount = product["base_price_inr"] if product else 1

            cust = conn.execute(text("SELECT id FROM customers WHERE email = :email"), {"email": clean_email}).mappings().first()
            if not cust:
                cust_id = str(uuid.uuid4())
                conn.execute(text("INSERT INTO customers (id, email) VALUES (:id, :email)"), {"id": cust_id, "email": clean_email})
            else:
                cust_id = str(cust["id"])

            coupon_id = None
            requires_payment = True
            order_type = "PAID"

            if req.coupon_code:
                code_clean = req.coupon_code.strip().upper()
                coupon = conn.execute(text("SELECT * FROM coupons WHERE code = :code AND is_active = 1"), {"code": code_clean}).mappings().first()
                if coupon:
                    coupon_id = coupon["id"]
                    order_type = "FREE"
                    requires_payment = False

            new_oid = str(uuid.uuid4())
            conn.execute(text("""
                INSERT INTO orders (id, customer_id, product_id, coupon_id, order_type, gross_amount, discount_amount, net_amount, currency, status)
                VALUES (:id, :cid, :pid, :cpid, :otype, :gross, :disc, :net, 'INR', 'PAID')
            """), {
                "id": new_oid, "cid": cust_id, "pid": req.product_id, "cpid": coupon_id,
                "otype": order_type, "gross": gross_amount, "disc": (gross_amount if not requires_payment else 0),
                "net": (0 if not requires_payment else gross_amount)
            })

            token = generate_signed_download_token(new_oid)
            return {
                "order_id": new_oid,
                "requires_payment": requires_payment,
                "download_url": f"/api/download/{new_oid}?token={token}"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/download/{order_id}")
def download_secure_book(order_id: str, token: Optional[str] = None):
    oid_clean = str(order_id).strip()
    if not token or not verify_signed_download_token(token, oid_clean):
        raise HTTPException(status_code=403, detail="Download authorization token is invalid or expired.")

    pdf_path = "books/saas/v1.pdf"
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            real_pdf_bytes = f.read()
        return PlainResponse(
            content=real_pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=SaaS_Architecture_Handbook.pdf"}
        )

    raise HTTPException(status_code=503, detail="PDF asset not found on server.")