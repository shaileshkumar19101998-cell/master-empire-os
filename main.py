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

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response as PlainResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

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

DOWNLOAD_TOKEN_SECRET = os.getenv("DOWNLOAD_TOKEN_SECRET", "master_empire_download_secret_2026")

app = FastAPI(title="Autonomous Business OS", version="2.1.0")

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
                    slug VARCHAR(120),
                    title VARCHAR(255),
                    base_price_inr INTEGER DEFAULT 1
                );
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS orders (
                    id VARCHAR(64) PRIMARY KEY,
                    customer_email VARCHAR(255),
                    product_id INTEGER,
                    status VARCHAR(50) DEFAULT 'PAID',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
    except Exception as e:
        print("DB Init Note:", e)

class CreateOrderRequest(BaseModel):
    product_id: int = 1
    customer_email: str
    coupon_code: Optional[str] = None

def generate_signed_token(order_id: str) -> str:
    secret = DOWNLOAD_TOKEN_SECRET
    exp_time = int(time.time()) + 86400
    msg = f"{order_id}:{exp_time}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
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
        expected_sig = hmac.new(DOWNLOAD_TOKEN_SECRET.encode("utf-8"), msg, hashlib.sha256).hexdigest()
        return hmac.compare_digest(t_sig, expected_sig)
    except Exception:
        return False

@app.get("/", response_class=HTMLResponse)
def get_storefront():
    init_db()
    return HTMLResponse("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Autonomous OS — Digital Publishing Catalog</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 40px 20px; }
        .container { max-width: 600px; margin: 0 auto; background: #1e293b; padding: 32px; border-radius: 12px; border: 1px solid #334155; }
        input { width: 100%; box-sizing: border-box; padding: 12px; border-radius: 6px; border: 1px solid #475569; background: #0f172a; color: #fff; margin: 8px 0 16px 0; }
        button { width: 100%; background: #10b981; color: #022c22; padding: 14px; border: none; border-radius: 8px; font-weight: 800; font-size: 16px; cursor: pointer; }
        #modal { display: none; margin-top: 24px; padding: 20px; background: #022c22; border: 1px solid #10b981; border-radius: 8px; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <span style="font-size: 11px; text-transform: uppercase; color: #38bdf8; font-weight: 700;">CLOUD ARCHITECTURE</span>
        <h2 style="color: #f8fafc; margin: 8px 0;">SaaS Architecture & Scale Handbook</h2>
        <p style="color: #94a3b8; font-size: 14px;">Production-Grade Architecture Blueprint • Complete Edition</p>
        
        <label style="font-size: 13px; color: #cbd5e1;">Your Email Address:</label>
        <input type="email" id="email" placeholder="you@example.com" value="mohitkmr78p@gmail.com" required />

        <label style="font-size: 13px; color: #cbd5e1;">Coupon Code (Pre-filled for 100% Free Access):</label>
        <input type="text" id="coupon" value="SHAILJA" placeholder="Enter coupon code" />

        <button onclick="checkout()">Unlock & Download E-Book (₹0)</button>

        <div id="modal">
            <h3 style="color: #10b981; margin: 0 0 8px 0;">🎉 Access Granted!</h3>
            <p style="color: #cbd5e1; font-size: 13px; margin-bottom: 16px;">Your digital book has been unlocked and verified.</p>
            <a id="download-btn" href="#" style="display: inline-block; background: #10b981; color: #022c22; padding: 12px 24px; border-radius: 6px; font-weight: 800; text-decoration: none; font-size: 15px;">📥 Click Here: Download PDF Now</a>
        </div>
    </div>
    <script>
        async function checkout() {
            const email = document.getElementById("email").value;
            const coupon = document.getElementById("coupon").value;
            if(!email || !email.includes("@")) { alert("Please enter a valid email."); return; }

            try {
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
                    alert("Error creating order: " + (data.detail || "Unknown error"));
                }
            } catch (err) {
                alert("Network error: " + err.message);
            }
        }
    </script>
</body>
</html>""")

@app.post("/api/orders/create")
def create_secure_order(req: CreateOrderRequest):
    init_db()
    try:
        clean_email = req.customer_email.strip().lower()
        new_oid = f"ord_{uuid.uuid4().hex[:12]}"
        
        try:
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO orders (id, customer_email, product_id, status)
                    VALUES (:id, :email, :pid, 'PAID')
                """), {"id": new_oid, "email": clean_email, "pid": req.product_id})
        except Exception as dbe:
            print("DB Write Note:", dbe)

        token = generate_signed_token(new_oid)
        return {
            "order_id": new_oid,
            "status": "PAID",
            "download_url": f"/api/download/{new_oid}?token={token}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/download/{order_id}")
def download_secure_book(order_id: str, token: Optional[str] = None):
    oid_clean = str(order_id).strip()
    if not token or not verify_signed_token(token, oid_clean):
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

    # अगर फ़ाइल न मिले तो ऑन-द-फ़्लाई वैलिड PDF लौटाना
    fallback_pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Contents 4 0 R/Resources<<>>>>endobj\n"
        b"4 0 obj<</Length 140>>stream\n"
        b"BT /F1 18 Tf 50 720 Td (SaaS Architecture & Scale Handbook) Tj ET\n"
        b"BT /F1 12 Tf 50 680 Td (Autonomous Business OS - Digital Asset Edition) Tj ET\n"
        b"endstream\nendobj\n"
        b"xref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000052 00000 n \n0000000108 00000 n \n0000000210 00000 n \n"
        b"trailer<</Size 5/Root 1 0 R>>\nstartxref\n400\n%%EOF"
    )
    return PlainResponse(
        content=fallback_pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=SaaS_Architecture_Handbook.pdf"}
    )