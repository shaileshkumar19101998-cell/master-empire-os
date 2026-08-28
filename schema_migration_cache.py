import sqlite3
import os

DB_PATH = "autonomous_local.db"

def init_market_cache_table():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS market_signal_cache (
            cache_key TEXT PRIMARY KEY,
            provider TEXT NOT NULL,
            keyword TEXT NOT NULL,
            country_code TEXT NOT NULL,
            language_code TEXT NOT NULL,
            metric_type TEXT NOT NULL,
            normalized_payload TEXT NOT NULL,
            source_evidence TEXT,
            fetched_at REAL NOT NULL,
            expires_at REAL NOT NULL
        )
    """)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_market_cache_table()
    print("market_signal_cache table initialized successfully.")