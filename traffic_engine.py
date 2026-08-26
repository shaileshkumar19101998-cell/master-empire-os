import sqlite3, json, datetime, os

def get_db():
    conn = sqlite3.connect("autonomous_local.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_distribution_schema():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS distribution_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        task_type TEXT NOT NULL,
        channel TEXT NOT NULL,
        content_type TEXT NOT NULL,
        title TEXT NOT NULL,
        content_payload TEXT NOT NULL,
        source_keyword TEXT,
        search_intent TEXT,
        country_code TEXT DEFAULT 'GLOBAL',
        locale TEXT DEFAULT 'en',
        status TEXT DEFAULT 'READY_FOR_CONNECTION',
        priority INTEGER DEFAULT 1,
        scheduled_at TEXT,
        published_at TEXT,
        external_reference TEXT,
        attempt_count INTEGER DEFAULT 0,
        last_error TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(product_id, task_type, channel, content_type, country_code, source_keyword)
    )""")
    conn.commit()
    conn.close()

def ensure_distribution_plan(product_id: int):
    init_distribution_schema()
    conn = get_db()
    cur = conn.cursor()
    prod = cur.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if not prod or prod["status"] not in ["ACTIVE", "PUBLISHED"]:
        conn.close()
        return {"status": "skipped", "reason": "Product not active or not found"}
    seo = cur.execute("SELECT * FROM product_seo_profiles WHERE product_id = ?", (product_id,)).fetchone()
    primary_kw = seo["primary_keyword"] if seo and seo["primary_keyword"] else prod["title"]
    search_intent = seo["search_intent"] if seo and seo["search_intent"] else "informational"
    now = datetime.datetime.utcnow().isoformat()
    tasks = [
        ("SEO_PILLAR", "BLOG", "ARTICLE", f"Mastering {prod['title']}: Complete Guide", json.dumps({"headline": f"Ultimate Guide to {primary_kw}", "target_audience": prod["target_niche"]}), primary_kw, search_intent, "GLOBAL", 1),
        ("SOCIAL_TEASER", "SOCIAL", "POST", f"Quick Insight on {prod['title']}", json.dumps({"hook": f"Why {primary_kw} is essential in 2026", "cta": "Learn more on the official handbook page."}), primary_kw, "commercial", "GLOBAL", 2),
        ("NEWSLETTER_SNIPPET", "NEWSLETTER", "EMAIL", f"Weekly Breakdown: {prod['title']}", json.dumps({"subject": f"Key takeaways from {prod['title']}", "body": f"Discover practical applications in {prod['target_niche']}."}), primary_kw, search_intent, "GLOBAL", 2),
        ("SEARCH_FAQ_CLUSTER", "SEARCH", "FAQ", f"Top Questions Answered: {primary_kw}", json.dumps({"topic": primary_kw, "schema_type": "FAQPage"}), primary_kw, "informational", "GLOBAL", 3)
    ]
    inserted = 0
    for t_type, chan, c_type, title, payload, kw, intent, country, prio in tasks:
        try:
            cur.execute("""INSERT OR IGNORE INTO distribution_tasks 
                (product_id, task_type, channel, content_type, title, content_payload, source_keyword, search_intent, country_code, status, priority, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'READY_FOR_CONNECTION', ?, ?, ?)""",
                (product_id, t_type, chan, c_type, title, payload, kw, intent, country, prio, now, now))
            if cur.rowcount > 0:
                inserted += 1
        except Exception:
            pass
    conn.commit()
    total_tasks = len(cur.execute("SELECT id FROM distribution_tasks WHERE product_id = ?", (product_id,)).fetchall())
    conn.close()
    return {"status": "success", "product_id": product_id, "new_tasks_created": inserted, "total_tasks": total_tasks}

def sync_distribution_tasks():
    init_distribution_schema()
    conn = get_db()
    cur = conn.cursor()
    prods = cur.execute("SELECT id FROM products WHERE status IN ('ACTIVE', 'PUBLISHED')").fetchall()
    conn.close()
    results = {}
    for p in prods:
        results[p["id"]] = ensure_distribution_plan(p["id"])
    return results
