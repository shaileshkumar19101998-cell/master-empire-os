import sqlite3

DB_PATH = "autonomous_local.db"

def init_synthesis_tables():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS product_blueprints (
            opportunity_id TEXT PRIMARY KEY,
            topic TEXT NOT NULL,
            target_country TEXT NOT NULL,
            target_language TEXT NOT NULL,
            target_audience TEXT NOT NULL,
            problem_statement TEXT,
            blueprint_json TEXT NOT NULL,
            provenance_json TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS synthesized_products (
            product_job_id TEXT PRIMARY KEY,
            opportunity_id TEXT NOT NULL,
            title TEXT NOT NULL,
            pdf_path TEXT NOT NULL,
            pdf_checksum TEXT NOT NULL,
            total_words INTEGER NOT NULL,
            chapter_count INTEGER NOT NULL,
            qa_status TEXT NOT NULL,
            governance_status TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_synthesis_tables()
    print("Synthesis tables initialized.")