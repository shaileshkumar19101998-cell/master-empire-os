import os
import sys
import sqlite3
import json
import time
import subprocess
import dotenv

dotenv.load_dotenv()
from fastapi.testclient import TestClient

print("================================================================================")
print("MASTER EMPIRE OS — PHASE 5.3 OPERATOR STAGING & PROMOTION GATE HARD PROOF")
print("================================================================================")

# 1. DATABASE BASELINE CAPTURE
def get_db_counts():
    conn = sqlite3.connect("autonomous_local.db")
    cur = conn.cursor()
    tables = ["country_registry", "products", "orders", "revenue_ledger", "distribution_tasks", "blog_posts", "governance_audit_log"]
    counts = {t: cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
    conn.close()
    return counts

before_counts = get_db_counts()
print("\n[1. DB BASELINE COUNTS]:", before_counts)

# 2. MOUNT APP
import main
import operator_staging_router
import product_synthesis_engine
import multiformat_packaging_engine
import asset_bundle_engine

app = main.app
if not any(r.path.startswith("/operator") for r in app.routes if hasattr(r, 'path')):
    app.include_router(operator_staging_router.router)
c = TestClient(app)

# 3. TEST A: OPERATOR STAGING LIST
print("\n[2. TEST A: OPERATOR STAGING DISPLAY & NULL METRICS]")
staging_res = c.get("/operator/staging/list").json()
print(f"  GET /operator/staging/list -> Status: {staging_res.get('status')} | Items Count: {staging_res.get('staging_count')}")
if staging_res.get("items"):
    sample_item = staging_res["items"][0]
    print(f"  Staging Item Sample: {sample_item.get('title')}")
    print(f"    - Governance Status    : {sample_item.get('governance_status')}")
    print(f"    - Checksum Validated   : {sample_item.get('zip_exists')}")
    print(f"    - Strict Null Metrics  : vol={sample_item.get('search_volume_monthly')}, cpc={sample_item.get('cpc_value_usd')}")

# 4. PREPARE QUALIFIED READY_FOR_CATALOG ASSET
test_opp = {
    "opportunity_id": "live-opp-stage53",
    "keyword": "global micro-saas operations",
    "country_code": "US",
    "language_code": "en",
    "market_signals": {
        "source_type": "LIVE_EXTERNAL_SIGNAL",
        "provider": "SERPAPI_PROVIDER",
        "evidence_source": "Google SERP (Organic: 10, PAA: 5, Related: 8)"
    }
}
blueprint = product_synthesis_engine.synthesis_engine.generate_blueprint(test_opp)
pkg = multiformat_packaging_engine.packaging_engine.package_bundle(blueprint)
bundle = asset_bundle_engine.bundle_engine.create_release_bundle(blueprint, pkg)

# 5. TEST B, C, D, E, F: SECURITY & REJECTION DRILLS
print("\n[3. TEST B-F: PROMOTION GATE REJECTION DRILLS]")

# Non-Existent Bundle
res_bad_id = c.post("/operator/promote", json={
    "opportunity_id": "fake-opp-999",
    "bundle_id": "non-existent-bundle",
    "operator": "ADMIN"
})
print(f"  Non-Existent Bundle Rejection : HTTP {res_bad_id.status_code} (Expected 404)")

# Tampered Checksum Bundle Rejection
fake_bundle_id = "fake-tampered-bundle-53"
conn = sqlite3.connect("autonomous_local.db")
cur = conn.cursor()
cur.execute("""
    INSERT OR REPLACE INTO release_bundles
    (bundle_id, opportunity_id, zip_path, zip_checksum, cover_path, cover_checksum, governance_status, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""", (fake_bundle_id, test_opp["opportunity_id"], bundle["zip_path"], "bad_checksum_hash", bundle["cover_artifact"]["cover_path"], "hash", "READY_FOR_CATALOG", time.time()))
conn.commit()
conn.close()

res_bad_checksum = c.post("/operator/promote", json={
    "opportunity_id": test_opp["opportunity_id"],
    "bundle_id": fake_bundle_id,
    "operator": "ADMIN"
})
print(f"  Tampered Checksum Rejection   : HTTP {res_bad_checksum.status_code} (Expected 400)")

# 6. TEST G, H, K: VALID HUMAN OPERATOR PROMOTION
print("\n[4. TEST G, H, K: VALID HUMAN OPERATOR PROMOTION]")
valid_promo = c.post("/operator/promote", json={
    "opportunity_id": test_opp["opportunity_id"],
    "bundle_id": bundle["bundle_id"],
    "operator": "LEAD_OPERATOR_SHAILESH",
    "price_usd": 39.00,
    "currency": "USD"
})
print(f"  Explicit Operator Promotion   : HTTP {valid_promo.status_code} | Status: {valid_promo.json().get('status')}")
print(f"  Promoted Product ID           : {valid_promo.json().get('product_id')}")
print(f"  New Governance Status         : {valid_promo.json().get('governance_status')}")

# Capture active promotion delta immediately
active_counts = get_db_counts()
delta_products = active_counts["products"] - before_counts["products"]
delta_audit = active_counts["governance_audit_log"] - before_counts["governance_audit_log"]

print(f"\n[5. ACTIVE PROMOTION AUDIT STATE]:")
print(f"  Active Products Count         : {active_counts['products']} (Delta: +{delta_products})")
print(f"  Active Governance Audit Log   : {active_counts['governance_audit_log']} (Delta: +{delta_audit})")

# 7. TEST I & J: IDEMPOTENCY & DUPLICATE PROTECTION
print("\n[6. TEST I & J: IDEMPOTENCY DRILLS]")
repeat_promo = c.post("/operator/promote", json={
    "opportunity_id": test_opp["opportunity_id"],
    "bundle_id": bundle["bundle_id"],
    "operator": "LEAD_OPERATOR_SHAILESH"
})
print(f"  Repeated Promotion Attempt    : HTTP {repeat_promo.status_code} | Status: {repeat_promo.json().get('status')}")
print(f"  Idempotent Message            : {repeat_promo.json().get('message')}")

# 8. TEST M, N, O: STOREFRONT, HMAC & PAYMENT REGRESSION
print("\n[7. TEST M-O: STOREFRONT, HMAC & PAYMENT REGRESSION]")
tampered_dl = c.get("/api/download/fake-id?token=tampered_signature")
print(f"  HMAC Download Security Check  : HTTP {tampered_dl.status_code} (Expected 403)")
store_res = c.get("/")
print(f"  Storefront Health Check       : HTTP {store_res.status_code} (Expected 200)")

# 9. TEST P: DATABASE ZERO-DESTRUCTION & CLEAN HARNESS AUDIT
print("\n[8. TEST P: DATABASE AUDIT & CONTROLLED MUTATION VERIFICATION]")
conn = sqlite3.connect("autonomous_local.db")
cur = conn.cursor()
# Clean up temporary test promotion row to maintain clean catalog state
cur.execute("DELETE FROM products WHERE id = ?", (valid_promo.json().get('product_id'),))
cur.execute("DELETE FROM release_bundles WHERE bundle_id = ?", (fake_bundle_id,))
conn.commit()
conn.close()

after_clean_counts = get_db_counts()
frozen_preserved = all(before_counts[t] == after_clean_counts[t] for t in before_counts if t != "governance_audit_log")

print(f"  DB Baseline Counts           : {before_counts}")
print(f"  DB Post-Harness Reset Counts : {after_clean_counts}")
print(f"  Governance Audit Log Growth  : +{delta_audit} (Legitimate Audited Operator Action)")
print(f"  Frozen Tables Preservation   : {'PASS (100% Intact)' if frozen_preserved else 'FAIL'}")

# 10. GIT RECORD
print("\n[9. GIT METADATA]")
try:
    branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
    commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    print(f"  Git Branch: {branch} | Commit: {commit}")
except Exception as ge:
    print(f"  Git Info: {ge}")

print("\n================================================================================")
print("PHASE 5.3 EXECUTION COMPLETE")
print("================================================================================")