import os
import json
import time
import hmac
import hashlib
import uuid

# Clean local sqlite test file
if os.path.exists("autonomous_local.db"):
    try:
        os.remove("autonomous_local.db")
    except Exception:
        pass

os.environ["DATABASE_URL"] = "sqlite:///./autonomous_local.db"
TEST_WEBHOOK_SECRET = "test_webhook_secret_phase08_isolated"
TEST_DOWNLOAD_SECRET = "test_download_secret_phase08_isolated"
os.environ["RAZORPAY_WEBHOOK_SECRET"] = TEST_WEBHOOK_SECRET
os.environ["DOWNLOAD_TOKEN_SECRET"] = TEST_DOWNLOAD_SECRET
os.environ["RAZORPAY_KEY_ID"] = "rzp_test_public_12345"
os.environ["RAZORPAY_KEY_SECRET"] = "secret_never_expose_razorpay"
os.environ["R2_ENDPOINT_URL"] = "https://test.r2.cloudflarestorage.com"
os.environ["R2_ACCESS_KEY_ID"] = "test_access_key"
os.environ["R2_SECRET_ACCESS_KEY"] = "test_secret_key"
os.environ["R2_BUCKET_NAME"] = "test-bucket"

import main
import storage_engine
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

main.engine = create_engine("sqlite:///./autonomous_local.db", connect_args={"check_same_thread": False})
client = TestClient(main.app)

# Mock storage_engine functions for deterministic CI/local test verification
MOCK_R2_STORAGE = {"books/ai-empire-guide/v1/ai-empire-guide_v1.pdf": b"%PDF-1.4 Ground Truth"}

def mock_get_r2_client():
    if not os.getenv("R2_ENDPOINT_URL") or not os.getenv("R2_ACCESS_KEY_ID") or not os.getenv("R2_SECRET_ACCESS_KEY"):
        return None
    return True

def mock_object_exists(key):
    return key in MOCK_R2_STORAGE

def mock_generate_presigned_download(key, expiry_seconds=300):
    if key in MOCK_R2_STORAGE:
        return f"https://test.r2.cloudflarestorage.com/{key}?Expires={int(time.time())+expiry_seconds}&Signature=mock_sig"
    return None

storage_engine.get_r2_client = mock_get_r2_client
storage_engine.object_exists = mock_object_exists
storage_engine.generate_presigned_download = mock_generate_presigned_download

print("\n" + "="*65)
print("  STARTING PHASE 0.8 ACCEPTANCE & REGRESSION SUITE")
print("="*65 + "\n")

# Setup tables
with main.engine.begin() as conn:
    conn.execute(text("CREATE TABLE IF NOT EXISTS customers (id TEXT PRIMARY KEY, email TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
    conn.execute(text("CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, slug TEXT, title TEXT, tier_level TEXT, target_niche TEXT, base_price_inr INTEGER, base_price_usd INTEGER, pdf_file_path TEXT, status TEXT);"))
    conn.execute(text("CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, customer_id TEXT, product_id INTEGER, coupon_id INTEGER, order_type TEXT, gross_amount NUMERIC, discount_amount NUMERIC, net_amount NUMERIC, currency TEXT, status TEXT, razorpay_order_id TEXT);"))
    conn.execute(text("CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY AUTOINCREMENT, order_id TEXT, payment_method TEXT, transaction_ref TEXT UNIQUE, amount NUMERIC, currency TEXT, status TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
    conn.execute(text("CREATE TABLE IF NOT EXISTS revenue_ledger (id INTEGER PRIMARY KEY AUTOINCREMENT, transaction_ref TEXT UNIQUE, gross_amount NUMERIC, gateway_fee NUMERIC, net_revenue NUMERIC, currency TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
    conn.execute(text("CREATE TABLE IF NOT EXISTS coupons (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, discount_type TEXT, discount_value NUMERIC, requires_payment INTEGER, is_active INTEGER, expires_at TIMESTAMP, used_count INTEGER DEFAULT 0);"))
    conn.execute(text("CREATE TABLE IF NOT EXISTS system_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, module TEXT, status TEXT, message TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
    conn.execute(text("INSERT OR REPLACE INTO coupons (code, discount_type, discount_value, requires_payment, is_active, expires_at, used_count) VALUES ('SHAILJA', 'PERCENT', 100, 0, 1, '2099-01-01 00:00:00', 0);"))
    conn.execute(text("INSERT OR REPLACE INTO products (id, slug, title, tier_level, target_niche, base_price_inr, base_price_usd, pdf_file_path, status) VALUES (101, 'ai-empire-guide', 'AI Empire Blueprint', 'Level 1', 'AI Automations', 999, 12, 'books/ai-empire-guide/v1/ai-empire-guide_v1.pdf', 'ACTIVE');"))
    conn.execute(text("INSERT OR REPLACE INTO products (id, slug, title, tier_level, target_niche, base_price_inr, base_price_usd, pdf_file_path, status) VALUES (102, 'missing-guide', 'Missing Guide', 'Level 0', 'Growth', 0, 0, 'books/missing/v1/missing.pdf', 'ACTIVE');"))

test_oid = str(uuid.uuid4())
with main.engine.begin() as conn:
    conn.execute(text("INSERT INTO orders (id, customer_id, product_id, order_type, gross_amount, discount_amount, net_amount, currency, status, razorpay_order_id) VALUES (:id, 'cust_p8', 101, 'PAID', 999, 0, 999, 'INR', 'PAID', 'rzp_p8_order')"), {"id": test_oid})

# Test 1: Valid Token -> HTTP 302 Redirect to Presigned URL
valid_token = main.generate_signed_download_token(test_oid)
r1 = client.get(f"/api/download/{test_oid}?token={valid_token}", follow_redirects=False)
print("TEST 1  (PAID + Valid Token -> 302 Presigned URL) :", "PASS" if r1.status_code == 302 and "test.r2.cloudflarestorage.com" in r1.headers.get("location", "") else "FAIL")

# Test 2: Invalid HMAC Token Rejected (403) before storage
r2 = client.get(f"/api/download/{test_oid}?token=invalid_token_xyz", follow_redirects=False)
print("TEST 2  (Invalid HMAC Token Blocked 403)         :", "PASS" if r2.status_code == 403 else "FAIL")

# Test 3: Missing R2 Object -> Safe HTTP 404 (No Fake Delivery)
missing_oid = str(uuid.uuid4())
with main.engine.begin() as conn:
    conn.execute(text("INSERT INTO orders (id, customer_id, product_id, order_type, gross_amount, discount_amount, net_amount, currency, status) VALUES (:id, 'cust_p8', 102, 'FREE', 0, 0, 0, 'INR', 'PAID')"), {"id": missing_oid})
missing_token = main.generate_signed_download_token(missing_oid)
r3 = client.get(f"/api/download/{missing_oid}?token={missing_token}", follow_redirects=False)
print("TEST 3  (Missing R2 Object Returns 404 / No Fake) :", "PASS" if r3.status_code == 404 else "FAIL")

# Test 4: Missing R2 Config -> HTTP 503 Fail Closed
os.environ["R2_ENDPOINT_URL"] = ""
r4 = client.get(f"/api/download/{test_oid}?token={valid_token}", follow_redirects=False)
print("TEST 4  (Missing R2 Config Fails Closed 503)     :", "PASS" if r4.status_code == 503 else "FAIL")
os.environ["R2_ENDPOINT_URL"] = "https://test.r2.cloudflarestorage.com"

# Test 5: Download Rate Limiting (HTTP 429)
main.RATE_LIMIT_RECORD.clear()
for _ in range(5):
    client.get(f"/api/download/{test_oid}?token={valid_token}", follow_redirects=False)
r5 = client.get(f"/api/download/{test_oid}?token={valid_token}", follow_redirects=False)
print("TEST 5  (Download Rate Limiting 429 Active)       :", "PASS" if r5.status_code == 429 else "FAIL")

# Test 6: Phase 0.6 & Phase 0.7 Regression Verification
r6_root = client.get("/")
r6_robots = client.get("/robots.txt")
r6_sitemap = client.get("/sitemap.xml")
r6_book = client.get("/books/ai-empire-guide")
print("TEST 6  (Phase 0.6 & 0.7 Full Regression Gate)   :", "PASS" if all([r.status_code == 200 for r in [r6_root, r6_robots, r6_sitemap, r6_book]]) else "FAIL")

print("\n" + "="*65)
print("  ALL PHASE 0.8 ACCEPTANCE TESTS COMPLETED")
print("="*65 + "\n")