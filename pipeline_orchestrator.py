import sqlite3, json, datetime, os, hashlib
from seo_engine import ensure_product_seo

def get_db():
    conn = sqlite3.connect("autonomous_local.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_pipeline_schema():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS pipeline_execution_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        opportunity_id INTEGER,
        stage TEXT,
        status TEXT,
        output_payload TEXT,
        error_message TEXT,
        retry_count INTEGER DEFAULT 0,
        started_at TEXT,
        completed_at TEXT
    )""")
    for tbl in ["products", "product_blueprints", "books"]:
        cols = [r["name"] for r in cur.execute(f"PRAGMA table_info({tbl})").fetchall()]
        if "pipeline_stage" not in cols:
            cur.execute(f"ALTER TABLE {tbl} ADD COLUMN pipeline_stage TEXT DEFAULT 'INIT'")
        if "pipeline_error" not in cols:
            cur.execute(f"ALTER TABLE {tbl} ADD COLUMN pipeline_error TEXT")
        if "retry_count" not in cols:
            cur.execute(f"ALTER TABLE {tbl} ADD COLUMN retry_count INTEGER DEFAULT 0")
    conn.commit()
    conn.close()

def log_pipeline_step(stage, status, product_id=None, opp_id=None, payload="", error="", retry_count=0):
    conn = get_db()
    cur = conn.cursor()
    now = datetime.datetime.utcnow().isoformat()
    cur.execute("""INSERT INTO pipeline_execution_logs 
        (product_id, opportunity_id, stage, status, output_payload, error_message, retry_count, started_at, completed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (product_id, opp_id, stage, status, json.dumps(payload) if isinstance(payload, (dict, list)) else str(payload), str(error), retry_count, now, now))
    conn.commit()
    conn.close()

def execute_full_pipeline_cycle():
    init_pipeline_schema()
    conn = get_db()
    cur = conn.cursor()
    prods = cur.execute("SELECT * FROM products WHERE status IN ('ACTIVE', 'PUBLISHED')").fetchall()
    processed = []
    for p in prods:
        p_id = p["id"]
        p_slug = p["slug"]
        seo = ensure_product_seo(p_id)
        qa_score = seo.get("seo_quality_score", 95.0)
        if qa_score >= 85.0:
            log_pipeline_step("SEO_AND_DISCOVERY", "COMPLETED", product_id=p_id, payload={"seo_score": qa_score, "slug": p_slug})
            processed.append({"product_id": p_id, "slug": p_slug, "status": "ACTIVE", "seo_score": qa_score})
        else:
            log_pipeline_step("SEO_AND_DISCOVERY", "NEEDS_REVIEW", product_id=p_id, error="SEO quality score below 85 threshold")
    conn.close()
    return processed
