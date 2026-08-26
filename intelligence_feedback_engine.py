import sqlite3, json, datetime

def get_db():
    conn = sqlite3.connect("autonomous_local.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_analytics_schema():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS analytics_performance_matrix (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        opportunity_id TEXT,
        niche TEXT,
        country TEXT,
        currency TEXT,
        price_point REAL,
        order_count INTEGER DEFAULT 0,
        paid_order_count INTEGER DEFAULT 0,
        gross_revenue REAL DEFAULT 0.0,
        net_revenue REAL DEFAULT 0.0,
        performance_score REAL DEFAULT 50.0,
        revenue_signal REAL DEFAULT 50.0,
        conversion_signal REAL DEFAULT 50.0,
        market_signal REAL DEFAULT 50.0,
        calculated_at TEXT,
        period_start TEXT,
        period_end TEXT
    )""")
    conn.commit()
    conn.close()

def sync_intelligence_matrix():
    init_analytics_schema()
    conn = get_db()
    cur = conn.cursor()
    now = datetime.datetime.utcnow().isoformat()
    orders = cur.execute("SELECT * FROM orders").fetchall()
    total_paid = 0
    total_gross = 0.0
    for o in orders:
        if o["coupon_code"] != "SHAILJA" and (o["gross_amount"] or 0) > 0:
            total_paid += 1
            total_gross += float(o["gross_amount"])
    cur.execute("DELETE FROM analytics_performance_matrix WHERE opportunity_id = 'GLOBAL_ROLLUP'")
    cur.execute("""INSERT INTO analytics_performance_matrix 
        (opportunity_id, niche, country, currency, order_count, paid_order_count, gross_revenue, net_revenue, revenue_signal, performance_score, calculated_at)
        VALUES ('GLOBAL_ROLLUP', 'ALL', 'GLOBAL', 'INR', ?, ?, ?, ?, 50.0, 50.0, ?)""",
        (len(orders), total_paid, total_gross, total_gross * 0.98, now))
    conn.commit()
    conn.close()
    return {"status": "synced", "total_orders": len(orders), "paid_orders": total_paid, "gross_revenue": total_gross}

def calculate_bounded_feedback_adjustment(niche: str) -> float:
    conn = get_db()
    cur = conn.cursor()
    row = cur.execute("SELECT SUM(gross_revenue) as rev FROM analytics_performance_matrix WHERE niche = ?", (niche,)).fetchone()
    conn.close()
    if not row or not row["rev"] or row["rev"] == 0:
        return 0.0
    rev = float(row["rev"])
    return min(5.0, max(-5.0, rev / 1000.0))
