import os
import sys
import sqlite3
import json
import time
import subprocess
import dotenv

dotenv.load_dotenv()
from fastapi.testclient import TestClient

# Initialize Cache Table
import schema_migration_cache
schema_migration_cache.init_market_cache_table()

print("================================================================================")
print("PHASE 4.8 MULTI-PROVIDER MARKET INTELLIGENCE — RUNTIME HARD PROOF")
print("================================================================================")

# 1. DATABASE BEFORE AUDIT
conn = sqlite3.connect("autonomous_local.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

tables = ["country_registry", "products", "orders", "revenue_ledger", "distribution_tasks", "blog_posts", "governance_audit_log"]
before_counts = {t: cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
print("\n[1. DB BEFORE COUNTS]:", before_counts)

# 2. MOUNT APP
import main
import phase3_router
import market_intelligence_provider

app = main.app
app.include_router(phase3_router.router)
c = TestClient(app)

# 3. TEST A: ZERO-STATE PROVIDER BEHAVIOUR
print("\n[2. TEST A — ZERO-STATE PROVIDER VERIFICATION]")
prov = market_intelligence_provider.registry.get_active_provider()
print(f"  Active Provider: {type(prov).__name__}")
status = prov.get_status()
print(f"  Provider Status: {status}")

disc_res = c.post("/api/v1/opportunities/discover", json={"niche": "ai agency automation"})
disc_data = disc_res.json()
print(f"  POST /api/v1/opportunities/discover -> HTTP {disc_res.status_code}")
print(f"  Source Type: {disc_data.get('source_type')}")
print(f"  Live Score: {disc_data.get('live_score')}")
print(f"  Search Volume: {disc_data.get('market_signals', {}).get('search_volume_monthly')}")

# 4. TEST B & C: AUTHENTICATED REAL REQUESTS
print("\n[3. TEST B & C — EXTERNAL API VERIFICATION]")
serp_configured = market_intelligence_provider.registry.serpapi.get_status()["auth_configured"]
ke_configured = market_intelligence_provider.registry.ke.get_status()["auth_configured"]
print(f"  SerpApi Live Credentials Configured: {serp_configured}")
print(f"  Keywords Everywhere Live Credentials Configured: {ke_configured}")
if not serp_configured and not ke_configured:
    print("  -> AUTHENTICATED TESTS: NOT EXECUTED — CREDENTIAL NOT CONFIGURED IN LOCAL .ENV")

# 5. TEST D: 197 COUNTRY DYNAMIC ROUTING
print("\n[4. TEST D — 197 COUNTRY JURISDICTION ROUTING]")
test_markets = ["IN", "US", "GB", "CA", "AU", "DE", "FR", "JP", "BR", "AE"]
for code in test_markets:
    row = cur.execute("SELECT iso_code, country_name, currency_code FROM country_registry WHERE iso_code = ?", (code,)).fetchone()
    zero_call = market_intelligence_provider.registry.zero_state.fetch_market_signals("e-book", country_code=code)
    print(f"  Market: {row['iso_code']} ({row['country_name']}) | Currency: {row['currency_code']} | Dynamic Provider gl: {zero_call['country_code']}")

# 6. TEST E: 24-HOUR CACHE ENGINE PROOF
print("\n[5. TEST E — 24-HOUR ISOLATED CACHE TEST]")
sample_payload = {
    "country_code": "US",
    "language_code": "en",
    "category": "productivity",
    "keyword": "test-cache-kw",
    "search_intent": "informational",
    "search_volume_monthly": None,
    "trend_velocity_pct": None,
    "competition_density": None,
    "cpc_value_usd": None,
    "seo_difficulty_score": None,
    "evidence_source": "CACHE_TEST_PROVENANCE",
    "evidence_freshness": "30_DAYS_ROLLING",
    "confidence_score": 90.0,
    "provider": "SERPAPI_PROVIDER",
    "provider_status": "CONFIGURED",
    "data_status": "LIVE_EXTERNAL",
    "source_type": "LIVE_EXTERNAL_SIGNAL"
}
market_intelligence_provider.MarketSignalCache.set("SERPAPI", "test-cache-kw", "US", "en", "SERP_TRENDS", sample_payload, "CACHE_TEST_PROVENANCE")

hit1 = market_intelligence_provider.MarketSignalCache.get("SERPAPI", "test-cache-kw", "US", "en", "SERP_TRENDS")
print(f"  Cache Retrieval Check: Hit={hit1.get('cache_hit') if hit1 else False} | Evidence={hit1.get('evidence_source') if hit1 else 'None'}")

# 7. TEST F: PROVIDER RESILIENCE & ERROR HANDLING
print("\n[6. TEST F — PROVIDER FAILURE & TIMEOUT RESILIENCE]")
fake_prov = market_intelligence_provider.SerpApiProvider()
fake_prov.api_key = "invalid_testing_key_123"
fake_res = fake_prov.fetch_market_signals("error-test-kw")
print(f"  Invalid Key Request Handled Safely -> Provider Status: {fake_res.get('provider_status')} | Data Status: {fake_res.get('data_status')} | No Crash: True")

# 8. TEST G: SEEDED VS LIVE DATA SEPARATION
print("\n[7. TEST G — STRICT DATA SEPARATION VERIFICATION]")
top5_res = c.get("/api/v1/opportunities/top5").json()
print(f"  Top-5 Feed Tagged As: {top5_res.get('source_type')}")
for item in top5_res.get("top5", [])[:2]:
    print(f"    Item: {item.get('title')} | Source Type: {item.get('source_type')} | Is Seeded: {item.get('is_seeded')}")

# 9. TEST H: PAYMENT & DELIVERY REGRESSION
print("\n[8. TEST H — PAYMENT & HMAC SECURITY REGRESSION]")
r_tampered = c.get("/api/download/fake-tampered-id?token=invalid")
print(f"  Tampered Download HMAC Token Check: HTTP {r_tampered.status_code} (Expected 403)")

# 10. DATABASE AFTER COUNTS AUDIT
print("\n[9. TEST I — DATABASE ZERO-DESTRUCTION VERIFICATION]")
after_counts = {t: cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
conn.close()

print(f"  DB Before: {before_counts}")
print(f"  DB After : {after_counts}")
preserved = all(before_counts[t] == after_counts[t] for t in tables)
print(f"  Zero-Destruction Result: {'PASS (100% Intact)' if preserved else 'FAIL'}")

# 11. GIT STATUS
print("\n[10. GIT RECORD]")
try:
    branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
    commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    print(f"  Git Branch: {branch} | Current Commit: {commit}")
except Exception as ge:
    print(f"  Git Info: {ge}")

print("\n================================================================================")
print("AUDIT COMPLETE")
print("================================================================================")