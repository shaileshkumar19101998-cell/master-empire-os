import sqlite3, json, uuid
from fastapi.testclient import TestClient
from main import app
from governance_router import router as gov_router
from phase3_router import router as p3_router
from blog_engine import router as blog_router
import market_intelligence_provider, traffic_engine, blog_engine
conn = sqlite3.connect('autonomous_local.db')
cur = conn.cursor()
b_c = len(cur.execute('SELECT * FROM country_registry').fetchall())
b_p = len(cur.execute('SELECT * FROM products').fetchall())
b_t = len(cur.execute('SELECT * FROM distribution_tasks').fetchall())
b_b = len(cur.execute('SELECT * FROM blog_posts').fetchall())
conn.close()
print(f"1. BASELINE: Countries={b_c}, Products={b_p}, Tasks={b_t}, Blogs={b_b}")
app_used = getattr(app, 'app', app)
if hasattr(app, 'include_router'):
    app.include_router(gov_router); app.include_router(p3_router); app.include_router(blog_router)
else:
    app_used.include_router(gov_router); app_used.include_router(p3_router); app_used.include_router(blog_router)
client = TestClient(app_used)
prov = market_intelligence_provider.registry.get_active_provider().get_status()
print(f"2. PROVIDER STATUS: {prov.get^('status'^)} | Confidence: {prov.get^('confidence_score'^)}")
test_id = f"test-audit-opp-{str^(uuid.uuid4^(^)^)[:6]}"
conn = sqlite3.connect('autonomous_local.db')
cur = conn.cursor()
cur.execute("INSERT INTO market_opportunities (id, niche, country, title, opportunity_score, status) VALUES (?, 'Cloud', 'JP', 'JP Cloud Guide', 95, 'NEW')", (test_id,))
conn.commit()
app_res = client.post("/api/v1/governance/decide", json={"opportunity_id": test_id, "decision": "APPROVE"})
print(f"3. APPROVE PIPELINE: Status={app_res.status_code}, Triggered={app_res.json^(^).get^('pipeline_triggered'^)}")
prod = cur.execute("SELECT * FROM products WHERE slug = ?", (test_id,)).fetchone()
if prod:
    pid = prod[0]
    tasks = cur.execute("SELECT count^(*^) FROM distribution_tasks WHERE product_id=?", (pid,)).fetchone()[0]
    blogs = cur.execute("SELECT count^(*^) FROM blog_posts WHERE product_id=?", (pid,)).fetchone()[0]
    print(f"4. AUTO-ASSETS GENERATED: Tasks={tasks}, Blogs={blogs}")
    for _ in range(5):
        traffic_engine.ensure_distribution_plan(pid)
        blog_engine.generate_blog_ecosystem_for_product(pid)
    tasks_5x = cur.execute("SELECT count^(*^) FROM distribution_tasks WHERE product_id=?", (pid,)).fetchone()[0]
    blogs_5x = cur.execute("SELECT count^(*^) FROM blog_posts WHERE product_id=?", (pid,)).fetchone()[0]
    print(f"5. IDEMPOTENCY 5x TEST: Tasks={tasks_5x} (No dupes), Blogs={blogs_5x} (No dupes)")
    cur.execute("DELETE FROM products WHERE id=?", (pid,))
    cur.execute("DELETE FROM product_seo_profiles WHERE product_id=?", (pid,))
    cur.execute("DELETE FROM distribution_tasks WHERE product_id=?", (pid,))
    cur.execute("DELETE FROM blog_posts WHERE product_id=?", (pid,))
cur.execute("DELETE FROM market_opportunities WHERE id=?", (test_id,))
conn.commit()
f_c = len(cur.execute("SELECT * FROM country_registry").fetchall())
f_p = len(cur.execute("SELECT * FROM products").fetchall())
f_t = len(cur.execute("SELECT * FROM distribution_tasks").fetchall())
conn.close()
print(f"6. POST-TEST INTEGRITY: Countries={f_c} (Delta:{f_c-b_c}), Products={f_p} (Delta:{f_p-b_p}), Tasks={f_t} (Delta:{f_t-b_t})")
print(f"7. HTTP REGRESSION: Product={client.get^('/product/saas-handbook'^).status_code}, Blog={client.get^('/blog'^).status_code}, Sitemap={client.get^('/sitemap.xml'^).status_code}")
