import sqlite3

DB_PATH = "autonomous_local.db"

def init_distribution_tables():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # 1. Isolated Proposals Table (Never alters baseline distribution_tasks)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS distribution_proposals (
            proposal_id TEXT PRIMARY KEY,
            product_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            title TEXT NOT NULL,
            formatted_text TEXT NOT NULL,
            target_url TEXT NOT NULL,
            media_path TEXT,
            status TEXT NOT NULL,
            governance_operator TEXT,
            approval_timestamp REAL,
            created_at REAL NOT NULL
        )
    """)

    # 2. Isolated Syndication Dispatch & Audit Log
    cur.execute("""
        CREATE TABLE IF NOT EXISTS syndication_dispatch_log (
            dispatch_id TEXT PRIMARY KEY,
            proposal_id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            idempotency_key TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL,
            provider_post_id TEXT,
            publication_url TEXT,
            dispatch_mode TEXT NOT NULL,
            error_details TEXT,
            dispatched_at REAL NOT NULL,
            confirmed_at REAL
        )
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_distribution_tables()
    print("Isolated distribution tables initialized successfully.")