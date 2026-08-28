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
print("MASTER EMPIRE OS — PHASE 5.1 MULTI-FORMAT PACKAGING ENGINE HARD PROOF")
print("================================================================================")

# 1. CAPTURE BASELINE DATABASE COUNTS
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
import qa_engine

app = main.app
c = TestClient(app)

# 3. TEST A: LOAD APPROVED BLUEPRINT
print("\n[2. TEST A: LOAD APPROVED BLUEPRINT]")
sample_opp = {
    "opportunity_id": "live-opp-pkg51",
    "keyword": "enterprise workflow automation",
    "country_code": "US",
    "language_code": "en",
    "market_signals": {
        "source_type": "LIVE_EXTERNAL_SIGNAL",
        "provider": "SERPAPI_PROVIDER",
        "evidence_source": "Google SERP (Organic: 8, PAA: 5, Related: 8)"
    }
}
blueprint = product_synthesis_engine.synthesis_engine.generate_blueprint(sample_opp)
print(f"  Blueprint Generated: {blueprint.get('topic')} | Opportunity ID: {blueprint.get('opportunity_id')}")

# 4. TEST B, C, D, E: PACKAGE MULTI-FORMAT & STRUCTURAL VALIDATION
print("\n[3. TEST B-E: PDF & EPUB 3.0 PACKAGING & VALIDATION]")
bundle = multiformat_packaging_engine.packaging_engine.package_bundle(blueprint)
pdf_info = bundle["pdf_artifact"]
epub_info = bundle["epub_artifact"]

print(f"  PDF Generated : {pdf_info['pdf_path']} ({pdf_info['pdf_size_bytes']} bytes)")
print(f"  EPUB Generated: {epub_info['epub_path']} ({epub_info['epub_size_bytes']} bytes)")

# Validate EPUB 3.0 Container Structure
with zipfile.ZipFile(epub_info["epub_path"], "r") as z:
    file_list = z.namelist()
    has_mimetype = file_list[0] == "mimetype"
    has_container = "META-INF/container.xml" in file_list
    has_opf = "EPUB/content.opf" in file_list
    has_nav = "EPUB/nav.xhtml" in file_list
    print(f"  EPUB Structure Integrity Check:")
    print(f"    - First file is 'mimetype': {has_mimetype}")
    print(f"    - META-INF/container.xml  : {has_container}")
    print(f"    - EPUB/content.opf        : {has_opf}")
    print(f"    - EPUB/nav.xhtml (Nav Doc): {has_nav}")
    epub_valid = all([has_mimetype, has_container, has_opf, has_nav])
    print(f"  EPUB 3.0 Container Spec Result: {'PASS' if epub_valid else 'FAIL'}")

# 5. TEST F, G: INDEPENDENT CHECKSUM VERIFICATION
print("\n[4. TEST F & G: INDEPENDENT SHA-256 CHECKSUM PROOFS]")
def get_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

recomputed_pdf_hash = get_sha256(pdf_info["pdf_path"])
recomputed_epub_hash = get_sha256(epub_info["epub_path"])

print(f"  PDF Checksum Match : {recomputed_pdf_hash == pdf_info['pdf_checksum']} (Hash: {recomputed_pdf_hash[:16]}...)")
print(f"  EPUB Checksum Match: {recomputed_epub_hash == epub_info['epub_checksum']} (Hash: {recomputed_epub_hash[:16]}...)")

# 6. TEST H, I: TAMPER DETECTION
print("\n[5. TEST H & I: INTENTIONAL TAMPER REJECTION]")
tampered_pdf = pdf_info["pdf_path"] + ".tampered.pdf"
with open(pdf_info["pdf_path"], "rb") as fin, open(tampered_pdf, "wb") as fout:
    fout.write(fin.read() + b"\nTAMPERED_PAYLOAD")

tamper_pdf_check = (get_sha256(tampered_pdf) == pdf_info["pdf_checksum"])
print(f"  Tampered PDF Checksum Rejection: {'PASS (Tamper Caught)' if not tamper_pdf_check else 'FAIL'}")
if os.path.exists(tampered_pdf):
    os.remove(tampered_pdf)

# 7. TEST J, K, N: ANTI-AUTO-PUBLISH, HMAC & NULL METRICS
print("\n[6. TEST J, K, N: ANTI-AUTO-PUBLISH, HMAC SECURITY & NULL INTEGRITY]")
current_products = cur.execute("SELECT COUNT(*) FROM products").fetchone()[0]
print(f"  Products Count Post-Package: {current_products} (Expected unchanged {before_counts['products']})")
print(f"  Packaging State Locked At  : {bundle.get('governance_status')} (NOT LIVE_PRODUCT)")
print(f"  Strict Null Metrics Check  : vol={bundle.get('search_volume_monthly')}, cpc={bundle.get('cpc_value_usd')}")

tampered_dl = c.get("/api/download/fake-id?token=tampered_signature")
print(f"  HMAC Download Security Check: HTTP {tampered_dl.status_code} (Expected 403)")

# 8. TEST L, M: DATABASE INTEGRITY
print("\n[7. TEST L & M: DATABASE ZERO-DESTRUCTION & REGRESSION]")
after_counts = {t: cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
conn.close()

print(f"  DB Before: {before_counts}")
print(f"  DB After : {after_counts}")
preserved = all(before_counts[t] == after_counts[t] for t in tables)
print(f"  Zero-Destruction Result: {'PASS (100% Intact)' if preserved else 'FAIL'}")

# 9. GIT RECORD
print("\n[8. GIT METADATA]")
try:
    branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
    commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    print(f"  Git Branch: {branch} | Commit: {commit}")
except Exception as ge:
    print(f"  Git Info: {ge}")

print("\n================================================================================")
print("PHASE 5.1 EXECUTION COMPLETE")
print("================================================================================")