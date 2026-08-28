import os
import sqlite3
import json
import dotenv

dotenv.load_dotenv()
from fastapi.testclient import TestClient
import main

c = TestClient(main.app)

print("====================================================")
print("MASTER EMPIRE OS — EXACT RUNTIME HARD-PROOF AUDIT")
print("====================================================")

print("\n--- 1. STOREFRONT & CATALOG HARD PROOF ---")
r_store = c.get("/")
print(f"Storefront (/) -> Status: {r_store.status_code} | Catalog Title Loaded: {'<title>' in r_store.text}")

conn = sqlite3.connect("autonomous_local.db")
cur = conn.cursor()
products = cur.execute("SELECT * FROM products").fetchall()
print(f"Live Products Count: {len(products)}")
for p in products:
    print(f"  Product Record: {p}")

print("\n--- 2. PAYMENT REGRESSION HARD PROOF ---")
# 1. SHAILJA Promotional Flow
o1 = c.post("/api/orders/create", json={"product_id": "saas-handbook", "customer_email": "test@example.com", "coupon_code": "SHAILJA"})
o1_data = o1.json() if o1.status_code == 200 else {}
print(f"SHAILJA Order Create -> Status: {o1.status_code} | Order: {o1_data.get('order_id')}")
p1 = c.post("/api/payments/create-session", json={"order_id": o1_data.get('order_id', 'fake-id')})
print(f"SHAILJA Bypass Session -> Status: {p1.status_code} | Flow: {p1.json() if p1.status_code==200 else p1.text[:90]}")

# 2. AKHIL Promotional Flow
o2 = c.post("/api/orders/create", json={"product_id": "saas-handbook", "customer_email": "test@example.com", "coupon_code": "AKHIL"})
o2_data = o2.json() if o2.status_code == 200 else {}
print(f"AKHIL Order Create   -> Status: {o2.status_code} | Order: {o2_data.get('order_id')}")
p2 = c.post("/api/payments/create-session", json={"order_id": o2_data.get('order_id', 'fake-id')})
print(f"AKHIL Bypass Session   -> Status: {p2.status_code} | Flow: {p2.json() if p2.status_code==200 else p2.text[:90]}")

# 3. Standard Flow (Razorpay Gateway)
o3 = c.post("/api/orders/create", json={"product_id": "saas-handbook", "customer_email": "test@example.com"})
o3_data = o3.json() if o3.status_code == 200 else {}
print(f"Standard Order Create -> Status: {o3.status_code} | Order: {o3_data.get('order_id')}")
p3 = c.post("/api/payments/create-session", json={"order_id": o3_data.get('order_id', 'fake-id')})
print(f"Standard Gateway Session -> Status: {p3.status_code} | Flow: {p3.json() if p3.status_code==200 else p3.text[:90]}")

print("\n--- 3. SECURE DELIVERY HARD PROOF ---")
r_del = c.get("/api/download/fake-tampered-id?token=invalid")
print(f"Tampered/Invalid Download Token -> Status: {r_del.status_code}")

print("\n--- 4. 197 COUNTRY JURISDICTION HARD PROOF ---")
total_c = cur.execute("SELECT COUNT(*) FROM country_registry").fetchone()[0]
print(f"Total Registered Jurisdictions in DB: {total_c}")
sample_markets = ["IN", "US", "CA", "AU", "GB", "DE", "FR", "JP", "BR", "AE"]
for code in sample_markets:
    row = cur.execute("SELECT iso_code, country_name, currency_code, pricing_tier FROM country_registry WHERE iso_code = ?", (code,)).fetchone()
    if row:
        print(f"  {row[0]}: {row[1]} | Currency: {row[2]} | Tier: {row[3]}")
conn.close()

print("\n--- 8. ZERO-STATE PROVIDER HARD PROOF ---")
import market_intelligence_provider
prov = market_intelligence_provider.registry.get_active_provider()
print(f"Active Provider Type: {type(prov).__name__}")
print(f"Provider Status: {prov.get_status()}")

print("\n====================================================")
print("EXACT AUDIT COMPLETE")
print("====================================================")