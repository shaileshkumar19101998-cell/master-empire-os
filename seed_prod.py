import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv("DATABASE_URL", "sqlite:///./autonomous_local.db")

if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

# Render Postgres requires SSL mode
if db_url and "postgresql://" in db_url and "sslmode" not in db_url:
    db_url += "?sslmode=require" if "?" not in db_url else "&sslmode=require"

if "sqlite" in db_url:
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
else:
    engine = create_engine(db_url, pool_pre_ping=True)

with engine.begin() as conn:
    # Ensure tables exist
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            slug VARCHAR(120) UNIQUE NOT NULL,
            title VARCHAR(255) NOT NULL,
            tier_level VARCHAR(50) DEFAULT 'Tier 1',
            target_niche VARCHAR(120) NOT NULL,
            base_price_inr INTEGER NOT NULL DEFAULT 999,
            base_price_usd INTEGER NOT NULL DEFAULT 12,
            pdf_file_path VARCHAR(255),
            status VARCHAR(50) DEFAULT 'ACTIVE'
        );
    """))

    # Upsert product
    conn.execute(text("""
        INSERT INTO products (slug, title, tier_level, target_niche, base_price_inr, base_price_usd, pdf_file_path, status)
        VALUES ('saas-architecture-handbook', 'SaaS Architecture & Scale Handbook', 'Tier 1', 'Cloud Architecture', 1, 1, 'books/saas/v1.pdf', 'ACTIVE')
        ON CONFLICT (slug) DO NOTHING;
    """))
    print("SUCCESS: 1 Rupee Test Product Published to Production Database!")