import sqlite3
from fastapi.testclient import TestClient
from main import app
from governance_router import router as gov_router
from phase3_router import router as p3_router

app_used = getattr(app, 'app', app)
if hasattr(app, 'include_router'):
    app.include_router(gov_router)
    app.include_router(p3_router)
elif hasattr(app_used, 'include_router'):
    app_used.include_router(gov_router)
    app_used.include_router(p3_router)

client = TestClient(app_used)

print('=== 1. TOP-5 OPPORTUNITIES API TEST ===')
r_top5 = client.get('/api/v1/opportunities/top5')
print('Status:', r_top5.status_code, '| Count:', r_top5.json().get('count'))

print('\n=== 2. CONTROL CENTER DASHBOARD UI TEST ===')
r_dash = client.get('/admin/dashboard')
print('Status:', r_dash.status_code, '| Has Headline:', 'WHAT SHOULD WE PUBLISH TODAY?' in r_dash.text)

print('\n=== 3. GOVERNANCE DECISION (APPROVE) TEST ===')
r_decide = client.post('/api/v1/governance/decide', json={'opportunity_id': 'zero-debt-wealth-engine', 'decision': 'APPROVE'})
print('Approve Status:', r_decide.status_code, '| Triggered:', r_decide.json().get('pipeline_triggered'))

print('\n=== 4. GOVERNANCE DECISION (SAVE FOR LATER) TEST ===')
r_save = client.post('/api/v1/governance/decide', json={'opportunity_id': 'peak-performance-neuro-habits', 'decision': 'SAVE_FOR_LATER'})
print('Save Status:', r_save.status_code, '| New Status:', r_save.json().get('new_status'))

print('\n=== 5. BASELINE & REGISTRY VERIFICATION ===')
conn = sqlite3.connect('autonomous_local.db')
cur = conn.cursor()
print('Country Registry Count:', len(cur.execute('SELECT * FROM country_registry').fetchall()))
print('Audit Logs Count:', len(cur.execute('SELECT * FROM governance_audit_log').fetchall()))
print('GET /product/saas-handbook ->', client.get('/product/saas-handbook').status_code)
print('GET /product/ai-career-blueprint-2026 ->', client.get('/product/ai-career-blueprint-2026').status_code)
print('GET /sitemap.xml ->', client.get('/sitemap.xml').status_code)
conn.close()
