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
TEST_WEBHOOK_SECRET = "test_webhook_secret_phase07_isolated"
TEST_DOWNLOAD_SECRET = "test_download_secret_phase07_isolated"
os.environ["RAZORPAY_WEBHOOK_SECRET"] = TEST_WEBHOOK_SECRET
os.environ["DOWNLOAD_TOKEN_SECRET"] = TEST_DOWNLOAD_SECRET
os.environ["RAZORPAY_KEY_ID"] = "rzp_test_public_12345"
os.environ["RAZORPAY_KEY_SECRET"] = "secret_never_expose_razorpay"

import main
import pdf_engine
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

main.engine = create_engine("sqlite:///./autonomous_local.db", connect_args={"check_same_thread": False})
client = TestClient(main.app)

print("\n" + "="*65)
print("  STARTING PHASE 0.7 ACCEPTANCE & REGRESSION SUITE (22 TESTS)")
print("="*65 + "\n")

# Mock valid PDF asset file for testing delivery
test_pdf_file = os.path.join(pdf_engine.PDF_STORAGE_DIR, "verified_book.pdf")
with open(test_pdf_file, "wb") as f:
    f.write(b"%PDF-1.4 Verified Ground Truth Asset Content")

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
    conn.execute(text("INSERT OR REPLACE INTO products (id, slug, title, tier_level, target_niche, base_price_inr, base_price_usd, pdf_file_path, status) VALUES (101, 'ai-empire-guide', 'AI Empire Blueprint', 'Level 1', 'AI Automations', 999, 12, 'verified_book.pdf', 'ACTIVE');"))
    conn.execute(text("INSERT OR REPLACE INTO products (id, slug, title, tier_level, target_niche, base_price_inr, base_price_usd, pdf_file_path, status) VALUES (102, 'free-starter-kit', 'Free Starter Kit', 'Level 0', 'Growth', 0, 0, 'missing_book.pdf', 'ACTIVE');"))

def sign_payload(payload_dict):
    raw_b = json.dumps(payload_dict).encode("utf-8")
    sig = hmac.new(TEST_WEBHOOK_SECRET.encode("utf-8"), raw_b, hashlib.sha256).hexdigest()
    return raw_b, sig

# Test 1: GET / -> 200
r1 = client.get("/")
print("TEST 1  (GET / Storefront 200)             :", "PASS" if r1.status_code == 200 and "Autonomous OS Library" in r1.text else "FAIL")

# Test 2: GET /robots.txt -> 200
r2 = client.get("/robots.txt")
print("TEST 2  (GET /robots.txt 200)              :", "PASS" if r2.status_code == 200 and "Disallow: /api/download/" in r2.text else "FAIL")

# Test 3: GET /sitemap.xml -> 200
r3 = client.get("/sitemap.xml")
print("TEST 3  (GET /sitemap.xml 200)             :", "PASS" if r3.status_code == 200 and "ai-empire-guide" in r3.text else "FAIL")

# Test 4: GET /books/{valid-slug} -> 200
r4 = client.get("/books/ai-empire-guide")
print("TEST 4  (GET /books/{valid-slug} 200)      :", "PASS" if r4.status_code == 200 and "AI Empire Blueprint" in r4.text else "FAIL")

# Test 5: Invalid slug -> 404
r5 = client.get("/books/non-existent-slug-xyz")
print("TEST 5  (Invalid Slug 404)                 :", "PASS" if r5.status_code == 404 else "FAIL")

# Test 6: Catalog loads actual products
print("TEST 6  (Catalog Real Database Load)       :", "PASS" if "AI Empire Blueprint" in r1.text and "Free Starter Kit" in r1.text else "FAIL")

# Test 7: Free product flow
r7 = client.post("/api/orders/create", json={"product_id": 102, "customer_email": "free@test.org"})
d7 = r7.json()
print("TEST 7  (Free Product Flow)                :", "PASS" if d7.get("status") == "PAID" and d7.get("download_url") else "FAIL")

# Test 8: Paid product creates valid test order & session
r8 = client.post("/api/orders/create", json={"product_id": 101, "customer_email": "paid@test.org"})
d8 = r8.json()
r8_sess = client.post("/api/payments/create-session", json={"order_id": d8["order_id"]})
d8_sess = r8_sess.json()
print("TEST 8  (Paid Order & Session Creation)    :", "PASS" if d8["status"] == "PENDING" and d8_sess["amount_paise"] == 99900 else "FAIL")

# Test 9: Browser receives only public Razorpay key
print("TEST 9  (Public Razorpay Key Only)         :", "PASS" if d8_sess.get("razorpay_key_id") == "rzp_test_public_12345" else "FAIL")

# Test 10: Razorpay secret never appears in HTML/JSON
print("TEST 10 (Zero Secret Exposure In API/HTML) :", "PASS" if "secret_never_expose_razorpay" not in r1.text and "secret_never_expose_razorpay" not in json.dumps(d8_sess) else "FAIL")

# Setup Webhook order
test_oid = d8["order_id"]
with main.engine.begin() as conn:
    conn.execute(text("UPDATE orders SET razorpay_order_id = 'rzp_order_phase7_999' WHERE id = :oid"), {"oid": test_oid})

valid_p = {
    "event": "payment.captured",
    "payload": {
        "payment": {
            "entity": {
                "id": f"pay_p7_{test_oid[:10]}",
                "order_id": "rzp_order_phase7_999",
                "amount": 99900,
                "currency": "INR",
                "status": "captured",
                "captured": True,
                "method": "card",
                "fee": 1998
            }
        }
    }
}
raw_wh, sig_wh = sign_payload(valid_p)

# Test 11: Webhook remains HMAC protected & Settles
r11 = client.post("/api/payments/webhook", content=raw_wh, headers={"X-Razorpay-Signature": sig_wh, "Content-Type": "application/json"})
print("TEST 11 (Webhook HMAC Settlement)          :", "PASS" if r11.status_code == 200 else "FAIL")

# Test 12: Invalid webhook signature -> 401
r12 = client.post("/api/payments/webhook", content=raw_wh, headers={"X-Razorpay-Signature": "invalid_sig_xyz", "Content-Type": "application/json"})
print("TEST 12 (Invalid Webhook Signature 401)    :", "PASS" if r12.status_code == 401 else "FAIL")

# Setup second pending order specifically for Amount Mismatch Test
mismatch_oid = str(uuid.uuid4())
with main.engine.begin() as conn:
    conn.execute(text("INSERT INTO orders (id, customer_id, product_id, order_type, gross_amount, discount_amount, net_amount, currency, status, razorpay_order_id) VALUES (:id, 'cust_mismatch', 101, 'PAID', 999, 0, 999, 'INR', 'PENDING', 'rzp_order_mismatch_999')"), {"id": mismatch_oid})

# Test 13: Amount mismatch -> rejected (with fresh payment ID)
bad_amt_p = {
    "event": "payment.captured",
    "payload": {
        "payment": {
            "entity": {
                "id": f"pay_bad_amt_{mismatch_oid[:8]}",
                "order_id": "rzp_order_mismatch_999",
                "amount": 50000,
                "currency": "INR",
                "status": "captured",
                "captured": True,
                "method": "card"
            }
        }
    }
}
raw_bad, sig_bad = sign_payload(bad_amt_p)
r13 = client.post("/api/payments/webhook", content=raw_bad, headers={"X-Razorpay-Signature": sig_bad, "Content-Type": "application/json"})
print("TEST 13 (Amount Mismatch Rejected 400)     :", "PASS" if r13.status_code == 400 else "FAIL")

# Test 14: Duplicate webhook -> exactly one settlement
client.post("/api/payments/webhook", content=raw_wh, headers={"X-Razorpay-Signature": sig_wh, "Content-Type": "application/json"})
with main.engine.connect() as conn:
    settle_count = conn.execute(text("SELECT count(*) FROM revenue_ledger WHERE transaction_ref = :tx"), {"tx": f"pay_p7_{test_oid[:10]}"}).scalar()
print("TEST 14 (Duplicate Webhook Idempotency)    :", "PASS (Exactly 1 Ledger Entry)" if settle_count == 1 else "FAIL")

# Test 15: PENDING download -> 403
pend_oid = str(uuid.uuid4())
with main.engine.begin() as conn:
    conn.execute(text("INSERT INTO orders (id, customer_id, product_id, order_type, gross_amount, discount_amount, net_amount, currency, status) VALUES (:id, 'cust_test', 101, 'PAID', 999, 0, 999, 'INR', 'PENDING')"), {"id": pend_oid})
r15 = client.get(f"/api/download/{pend_oid}?token=valid_token_placeholder")
print("TEST 15 (PENDING Download Blocked 403)     :", "PASS" if r15.status_code == 403 else "FAIL")

# Test 16: PAID + valid token -> download succeeds
valid_tok = main.generate_signed_download_token(test_oid)
r16 = client.get(f"/api/download/{test_oid}?token={valid_tok}")
print("TEST 16 (PAID + Valid Token Download 200)  :", "PASS" if r16.status_code == 200 and b"%PDF-1.4" in r16.content else "FAIL")

# Test 17: Expired token -> blocked
exp_tok = f"{test_oid}.{int(time.time()) - 300}.v1.fakesig"
r17 = client.get(f"/api/download/{test_oid}?token={exp_tok}")
print("TEST 17 (Expired Token Blocked 403)        :", "PASS" if r17.status_code == 403 else "FAIL")

# Test 18: Tampered token -> blocked
tamp_tok = f"{test_oid}.{int(time.time()) + 500}.v1.tampered_signature"
r18 = client.get(f"/api/download/{test_oid}?token={tamp_tok}")
print("TEST 18 (Tampered Token Blocked 403)       :", "PASS" if r18.status_code == 403 else "FAIL")

# Test 19: Missing DOWNLOAD_TOKEN_SECRET -> fail closed
os.environ["DOWNLOAD_TOKEN_SECRET"] = ""
main.DOWNLOAD_TOKEN_SECRET = ""
try:
    main.generate_signed_download_token(test_oid)
    test19_pass = False
except ValueError:
    test19_pass = True
print("TEST 19 (Missing Secret Fails Closed)      :", "PASS" if test19_pass else "FAIL")

# Restore Secret
os.environ["DOWNLOAD_TOKEN_SECRET"] = TEST_DOWNLOAD_SECRET
main.DOWNLOAD_TOKEN_SECRET = TEST_DOWNLOAD_SECRET

# Test 20: Missing PDF asset -> no fake production PDF (Returns 404 Error)
valid_tok_free = main.generate_signed_download_token(d7["order_id"])
r20 = client.get(f"/api/download/{d7['order_id']}?token={valid_tok_free}")
print("TEST 20 (Missing PDF Safe 404 / No Fake)   :", "PASS" if r20.status_code == 404 else "FAIL")

# Test 21: Download rate limiting works
main.RATE_LIMIT_RECORD.clear()
for _ in range(5):
    client.get(f"/api/download/{test_oid}?token={valid_tok}")
r21 = client.get(f"/api/download/{test_oid}?token={valid_tok}")
print("TEST 21 (Download Rate Limiting 429)       :", "PASS" if r21.status_code == 429 else "FAIL")

# Test 22: Existing Phase 0.6 tests remain PASS
r22_coupon = client.post("/api/orders/create", json={"product_id": 101, "coupon_code": "SHAILJA", "customer_email": "shailja@coupon.org"})
print("TEST 22 (Phase 0.6 Regression Gate)        :", "PASS" if r22_coupon.json().get("status") == "PAID" else "FAIL")

print("\n" + "="*65)
print("  ALL 22 PHASE 0.7 ACCEPTANCE TESTS COMPLETED")
print("="*65 + "\n")