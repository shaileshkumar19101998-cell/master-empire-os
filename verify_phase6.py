import os
import sys
import sqlite3
import json
import time
import subprocess
import dotenv

dotenv.load_dotenv()
from fastapi.testclient import TestClient

# 1. Run Additive Isolated Migration
import distribution_schema_migration
distribution_schema_migration.init_distribution_tables()

print("================================================================================")
print("MASTER EMPIRE OS — PHASE 6 MULTI-CHANNEL DISTRIBUTION HARD PROOF")
print("================================================================================")

# 2. CAPTURE BASELINE DATABASE COUNTS
conn = sqlite3.connect("autonomous_local.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
tables = ["country_registry", "products", "orders", "revenue_ledger", "distribution_tasks", "blog_posts", "governance_audit_log"]
before_counts = {t: cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
print("\n[1. DB BASELINE COUNTS]:", before_counts)

# 3. MOUNT APP
import main
import distribution_router
import distribution_orchestrator

app = main.app
if not any(r.path.startswith("/api/v1/distribution") for r in app.routes if hasattr(r, 'path')):
    app.include_router(distribution_router.router)
c = TestClient(app)

SECRET_KEY = os.getenv("OPERATOR_MASTER_SECRET", "LEAD_OPERATOR_AUTH_TOKEN_7788")
AUTH_HEADER = {"x-operator-secret": SECRET_KEY}

# 4. TEST A & B: UNAUTHORIZED / FORGED ACCESS REJECTION
print("\n[2. TEST A & B: AUTHORIZATION SECURITY DRILLS]")
unauth_res = c.post("/api/v1/distribution/stage", json={"product_id": "prod-001"})
print(f"  Missing Operator Token Rejection : HTTP {unauth_res.status_code} (Expected 403)")

forged_res = c.post("/api/v1/distribution/stage", json={"product_id": "prod-001"}, headers={"x-operator-secret": "forged_secret"})
print(f"  Forged Operator Token Rejection  : HTTP {forged_res.status_code} (Expected 403)")

# 5. TEST C: CONNECTOR STATUS & CREDENTIAL SAFETY
print("\n[3. TEST C: CONNECTOR STATUS & ZERO-SECRET LEAKAGE]")
status_res = c.get("/api/v1/distribution/connectors/status").json()
print(f"  Active Connectors Checked: {len(status_res.get('connectors', []))}")
for conn_stat in status_res.get("connectors", []):
    print(f"    - Platform: {conn_stat.get('channel')} | Status: {conn_stat.get('status')} | Auth Configured: {conn_stat.get('auth_configured')}")
    assert "token" not in conn_stat and "key" not in conn_stat, "Secret leakage detected in status output!"

# 6. TEST D & E: PROPOSAL STAGING WITHOUT DISPATCH
print("\n[4. TEST D & E: PROPOSAL STAGING & ZERO DISPATCH]")
first_prod_row = cur.execute("SELECT * FROM products LIMIT 1").fetchone()
target_pid = str(first_prod_row["id"]) if first_prod_row and "id" in first_prod_row.keys() else "prod-001"

stage_http = c.post("/api/v1/distribution/stage", json={"product_id": target_pid}, headers=AUTH_HEADER)
stage_res = stage_http.json()
proposals = stage_res.get("proposals", [])
print(f"  Target Product ID         : {target_pid}")
print(f"  Stage Endpoint HTTP Status: {stage_http.status_code}")
print(f"  Staged Proposals Count    : {len(proposals)}")

if not proposals:
    print("  ERROR: No proposals returned:", stage_res)
    conn.close()
    sys.exit(1)

sample_proposal = proposals[0]
print(f"  Sample Proposal State     : {sample_proposal['status']}")
print(f"  Sample Target URL         : {sample_proposal['target_url']}")

# 7. TEST F: UNAPPROVED DISPATCH BLOCKED (HUMAN APPROVAL GATE)
print("\n[5. TEST F: GOVERNANCE BARRIER (UNAPPROVED DISPATCH)]")
unapproved_dispatch = c.post("/api/v1/distribution/dispatch", json={
    "proposal_id": sample_proposal["proposal_id"],
    "operator_identity": "ATTEMPTED_AUTO_WORKER",
    "dry_run": True
}, headers=AUTH_HEADER)
print(f"  Unapproved Dispatch Blocked : HTTP {unapproved_dispatch.status_code} (Expected 403)")
print(f"  Rejection Detail            : {unapproved_dispatch.json().get('detail')}")

# 8. TEST G & H: HUMAN APPROVAL & CONTROLLED DISPATCH
print("\n[6. TEST G & H: HUMAN APPROVAL & SANDBOX DISPATCH]")
appr_res = c.post("/api/v1/distribution/approve", json={
    "proposal_id": sample_proposal["proposal_id"],
    "operator_identity": "LEAD_OPERATOR_SHAILESH"
}, headers=AUTH_HEADER).json()
print(f"  Human Approval Stamped: Status = {appr_res.get('approval', {}).get('status')} by {appr_res.get('approval', {}).get('operator')}")

dispatch_res = c.post("/api/v1/distribution/dispatch", json={
    "proposal_id": sample_proposal["proposal_id"],
    "operator_identity": "LEAD_OPERATOR_SHAILESH",
    "dry_run": True
}, headers=AUTH_HEADER).json()
disp_data = dispatch_res.get("dispatch_result", {})
print(f"  Dispatch Execution Result : Status = {disp_data.get('status')} (Mode: {disp_data.get('dispatch_mode')})")
print(f"  Provider Post ID          : {disp_data.get('provider_post_id')}")
print(f"  Publication URL           : {disp_data.get('publication_url')}")

# 9. TEST I: IDEMPOTENCY & DUPLICATE DISPATCH PROTECTION
print("\n[7. TEST I: IDEMPOTENCY DRILL]")
repeat_dispatch = c.post("/api/v1/distribution/dispatch", json={
    "proposal_id": sample_proposal["proposal_id"],
    "operator_identity": "LEAD_OPERATOR_SHAILESH",
    "dry_run": True
}, headers=AUTH_HEADER).json()
repeat_data = repeat_dispatch.get("dispatch_result", {})
print(f"  Repeated Dispatch Attempt : Status = {repeat_data.get('status')}")
print(f"  Idempotency Message       : {repeat_data.get('message')}")

# 10. TEST J, K, L: REGRESSION & SECURITY CHECKS
print("\n[8. TEST J-L: STOREFRONT, HMAC & PAYMENT REGRESSION]")
tampered_dl = c.get("/api/download/fake-id?token=tampered_signature")
print(f"  HMAC Download Security Check : HTTP {tampered_dl.status_code} (Expected 403)")
store_res = c.get("/")
print(f"  Storefront Health Check      : HTTP {store_res.status_code} (Expected 200)")

# 11. TEST M: DATABASE ZERO-DESTRUCTION AUDIT
print("\n[9. TEST M: DATABASE ZERO-DESTRUCTION AUDIT]")
after_counts = {t: cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
conn.close()

print(f"  DB Before: {before_counts}")
print(f"  DB After : {after_counts}")
preserved = all(before_counts[t] == after_counts[t] for t in tables)
print(f"  Zero-Destruction Result      : {'PASS (100% Intact across all 7 frozen tables)' if preserved else 'FAIL'}")

# 12. GIT RECORD
print("\n[10. GIT METADATA]")
try:
    branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
    commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    print(f"  Git Branch: {branch} | Commit: {commit}")
except Exception as ge:
    print(f"  Git Info: {ge}")

print("\n================================================================================")
print("PHASE 6 EXECUTION COMPLETE")
print("================================================================================")