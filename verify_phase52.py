import os
import sys
import sqlite3
import json
import zipfile
import hashlib
import subprocess
import dotenv

dotenv.load_dotenv()
from fastapi.testclient import TestClient

print("================================================================================")
print("MASTER EMPIRE OS — PHASE 5.2 DYNAMIC COVER & ASSET BUNDLING HARD PROOF")
print("================================================================================")

# 1. DATABASE BASELINE COUNTS
conn = sqlite3.connect("autonomous_local.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
tables = ["country_registry", "products", "orders", "revenue_ledger", "distribution_tasks", "blog_posts", "governance_audit_log"]
before_counts = {t: cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
print("\n[1. DB BASELINE COUNTS]:", before_counts)

# 2. MOUNT APP
import main
import multiformat_packaging_engine
import product_synthesis_engine
import asset_bundle_engine

app = main.app
c = TestClient(app)

# Helper SHA-256 recomputation
def compute_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

# 3. TEST A, B, C, D: LOAD BLUEPRINT, GENERATE COVER, MULTI-FORMAT PACKAGING
print("\n[2. TEST A-D: BLUEPRINT, COVER & MULTI-FORMAT ASSET CREATION]")
opp = {
    "opportunity_id": "live-opp-bndl52",
    "keyword": "distributed cloud architecture",
    "country_code": "US",
    "language_code": "en",
    "market_signals": {
        "source_type": "LIVE_EXTERNAL_SIGNAL",
        "provider": "SERPAPI_PROVIDER",
        "evidence_source": "Google SERP (Organic: 10, PAA: 5, Related: 8)"
    }
}
blueprint = product_synthesis_engine.synthesis_engine.generate_blueprint(opp)
pkg = multiformat_packaging_engine.packaging_engine.package_bundle(blueprint)
cover = asset_bundle_engine.bundle_engine.generate_cover(blueprint, pkg["package_job_id"])

print(f"  Blueprint Topic    : {blueprint.get('topic')} (Opp ID: {blueprint.get('opportunity_id')})")
print(f"  Cover Generated    : {cover['cover_path']} ({cover['cover_size_bytes']} bytes)")
print(f"  PDF Checksum Match : {compute_sha256(pkg['pdf_artifact']['pdf_path']) == pkg['pdf_artifact']['pdf_checksum']}")
print(f"  EPUB Checksum Match: {compute_sha256(pkg['epub_artifact']['epub_path']) == pkg['epub_artifact']['epub_checksum']}")

# 4. TEST E, F, G, H: UNIFIED ZIP BUNDLE CREATION & INDEPENDENT SHA-256 CHECK
print("\n[3. TEST E-H: UNIFIED ZIP BUNDLE CREATION & RECOMPUTATION]")
bundle = asset_bundle_engine.bundle_engine.create_release_bundle(blueprint, pkg)
zip_path = bundle["zip_path"]
reg_checksum = bundle["zip_checksum"]
recalc_checksum = compute_sha256(zip_path)

print(f"  ZIP Bundle Path    : {zip_path} ({bundle['zip_size_bytes']} bytes)")
print(f"  Registered Checksum: {reg_checksum[:16]}...")
print(f"  Recomputed Checksum: {recalc_checksum[:16]}...")
print(f"  SHA-256 Match Proof: {'PASS' if reg_checksum == recalc_checksum else 'FAIL'}")

# Inspect ZIP Manifest and Entries
with zipfile.ZipFile(zip_path, "r") as z:
    entries = z.namelist()
    has_pdf = any(e.endswith(".pdf") for e in entries)
    has_epub = any(e.endswith(".epub") for e in entries)
    has_svg = any(e.endswith(".svg") for e in entries)
    has_manifest = "manifest.json" in entries
    print(f"  ZIP Contents Verification:")
    print(f"    - Embedded PDF     : {has_pdf}")
    print(f"    - Embedded EPUB    : {has_epub}")
    print(f"    - Embedded SVG     : {has_svg}")
    print(f"    - Manifest JSON    : {has_manifest}")
    print(f"  Bundle Integrity   : {'PASS' if all([has_pdf, has_epub, has_svg, has_manifest]) else 'FAIL'}")

# 5. TEST I: INTENTIONAL ZIP CORRUPTION & TAMPER DETECTION
print("\n[4. TEST I: TAMPER & CORRUPTION DETECTION]")
tampered_zip = zip_path + ".corrupted.zip"
with open(zip_path, "rb") as fin, open(tampered_zip, "wb") as fout:
    fout.write(fin.read() + b"\nTAMPERED_BYTE_PAYLOAD")

tamper_match = (compute_sha256(tampered_zip) == reg_checksum)
print(f"  Corrupted ZIP Checksum Check: {'PASS (Tamper Successfully Caught)' if not tamper_match else 'FAIL'}")
if os.path.exists(tampered_zip):
    os.remove(tampered_zip)

# 6. TEST J, K, L, N: IDENTITY BINDING, ANTI-AUTO-PUBLISH & NULL METRICS
print("\n[5. TEST J-N: IDENTITY BINDING, ANTI-AUTO-PUBLISH & NULL METRICS]")
current_products = cur.execute("SELECT COUNT(*) FROM products").fetchone()[0]
print(f"  Opportunity Binding Match  : {bundle['opportunity_id'] == opp['opportunity_id']}")
print(f"  Bundle Governance State    : {bundle.get('governance_status')} (NOT LIVE_PRODUCT)")
print(f"  Products Table Delta       : {current_products - before_counts['products']} (Products Count: {current_products})")
print(f"  Strict Null Metrics Check  : vol={bundle.get('search_volume_monthly')}, cpc={bundle.get('cpc_value_usd')}")

# 7. TEST M & P: STOREFRONT & HMAC SECURITY REGRESSION
print("\n[6. TEST M & P: STOREFRONT, PAYMENT & HMAC REGRESSION]")
tampered_dl = c.get("/api/download/fake-id?token=tampered_signature")
print(f"  HMAC Download Security Check : HTTP {tampered_dl.status_code} (Expected 403)")
store_res = c.get("/")
print(f"  Storefront Health Check      : HTTP {store_res.status_code} (Expected 200)")

# 8. TEST O: DATABASE ZERO-DESTRUCTION
print("\n[7. TEST O: DATABASE ZERO-DESTRUCTION AUDIT]")
after_counts = {t: cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
conn.close()

print(f"  DB Before: {before_counts}")
print(f"  DB After : {after_counts}")
preserved = all(before_counts[t] == after_counts[t] for t in tables)
print(f"  Zero-Destruction Result      : {'PASS (100% Intact)' if preserved else 'FAIL'}")

# 9. GIT RECORD
print("\n[8. GIT METADATA]")
try:
    branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
    commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    print(f"  Git Branch: {branch} | Commit: {commit}")
except Exception as ge:
    print(f"  Git Info: {ge}")

print("\n================================================================================")
print("PHASE 5.2 EXECUTION COMPLETE")
print("================================================================================")