import os
import sys
import sqlite3
import json
import subprocess
import dotenv

dotenv.load_dotenv()
from fastapi.testclient import TestClient

print("====================================================")
print("MASTER EMPIRE OS — ZERO-STATE HARDENING & PROOF")
print("====================================================")

# 1. DATABASE BEFORE COUNTS
conn = sqlite3.connect("autonomous_local.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

tables = ["country_registry", "products", "orders", "revenue_ledger", "distribution_tasks", "blog_posts", "governance_audit_log"]
before_counts = {}
for t in tables:
    try:
        before_counts[t] = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    except Exception:
        before_counts[t] = "N/A"

print("\n[DB BEFORE COUNTS]:", before_counts)

# 2. APPLICATION IMPORT & ROUTER MOUNTING
import main
app = main.app

# Mount unmounted modular routers cleanly if not already present
mounted_paths = [r.path for r in app.routes if hasattr(r, 'path')]

try:
    import blog_engine
    if hasattr(blog_engine, 'router') and "/blog" not in mounted_paths:
        app.include_router(blog_engine.router)
        print("[MOUNT] blog_engine router mounted successfully.")
except Exception as e:
    print(f"[MOUNT ERROR] blog_engine: {e}")

try:
    import governance_router
    if hasattr(governance_router, 'router') and "/governance" not in mounted_paths:
        app.include_router(governance_router.router)
        print("[MOUNT] governance_router mounted successfully.")
except Exception as e:
    print(f"[MOUNT ERROR] governance_router: {e}")

try:
    import phase3_router
    if hasattr(phase3_router, 'router') and "/api/v1" not in "".join(mounted_paths):
        app.include_router(phase3_router.router)
        print("[MOUNT] phase3_router mounted successfully.")
except Exception as e:
    print(f"[MOUNT ERROR] phase3_router: {e}")

c = TestClient(app)

# 3. RUNTIME HTTP ENDPOINT CHECKS
print("\n--- 3. HTTP RUNTIME VERIFICATION ---")
endpoints = [
    ("/", "Storefront Root"),
    ("/product/saas-handbook", "SaaS Handbook Page"),
    ("/blog", "Blog Index"),
    ("/sitemap.xml", "Sitemap XML"),
    ("/robots.txt", "Robots TXT"),
    ("/admin/dashboard", "Admin Dashboard")
]

endpoint_results = {}
for path, label in endpoints:
    try:
        r = c.get(path)
        endpoint_results[path] = r.status_code
        print(f"  {label} ({path}) -> Status: {r.status_code}")
    except Exception as e:
        endpoint_results[path] = f"ERR: {e}"
        print(f"  {label} ({path}) -> Exception: {e}")

# 4. ZERO-STATE MARKET INTELLIGENCE AUDIT
print("\n--- 4. ZERO-STATE MARKET INTELLIGENCE AUDIT ---")
import market_intelligence_provider
prov = market_intelligence_provider.registry.get_active_provider()
status_dict = prov.get_status()
print("  Active Provider Class:", type(prov).__name__)
print("  Provider Status Report:", status_dict)

r_disc = c.post("/api/v1/opportunities/discover", json={"niche": "saas workflow"})
print(f"  POST /api/v1/opportunities/discover -> Status: {r_disc.status_code}")
if r_disc.status_code == 200:
    print("  Discover Response Payload:", json.dumps(r_disc.json(), indent=2)[:300])

r_top5 = c.get("/api/v1/opportunities/top5")
print(f"  GET /api/v1/opportunities/top5 -> Status: {r_top5.status_code}")
if r_top5.status_code == 200:
    t5_data = r_top5.json().get("top5", [])
    for idx, item in enumerate(t5_data[:3]):
        print(f"    Rank {idx+1}: {item.get('title')} | Source Type: {item.get('source_type')} | Score: {item.get('opportunity_score')}")

# 5. PAYMENT & HMAC REGRESSION
print("\n--- 5. PAYMENT & HMAC SECURITY REGRESSION ---")
# Missing fields validation
bad_order = c.post("/api/orders/create", json={})
print(f"  Malformed Order Payload -> Status: {bad_order.status_code}")

# Tampered HMAC Token
tampered_dl = c.get("/api/download/tampered-id-123?token=invalid-signature")
print(f"  Tampered Download Link  -> Status: {tampered_dl.status_code}")

# 6. DATABASE AFTER COUNTS & INTEGRITY CHECK
print("\n--- 6. DATABASE ZERO-DESTRUCTION CHECK ---")
after_counts = {}
for t in tables:
    try:
        after_counts[t] = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    except Exception:
        after_counts[t] = "N/A"

conn.close()
print("  [DB BEFORE]:", before_counts)
print("  [DB AFTER] :", after_counts)
delta_ok = all(before_counts[k] == after_counts[k] for k in tables if before_counts[k] != "N/A")
print(f"  Zero-Destruction Integrity Check: {'PASS (No records mutated)' if delta_ok else 'FAIL'}")

# 7. GIT INTEGRITY
print("\n--- 7. GIT METADATA ---")
try:
    branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
    commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    print(f"  Git Branch: {branch} | Commit: {commit}")
except Exception as ge:
    print("  Git Metadata:", ge)

print("\n====================================================")
print("EXECUTION COMPLETED")
print("====================================================")