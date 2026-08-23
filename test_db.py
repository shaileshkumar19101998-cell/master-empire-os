import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

db_url = os.getenv("DATABASE_URL")
if not db_url:
    print("❌ ERROR: .env file me DATABASE_URL nahi mila!")
    exit(1)

# Neon SSL compatibility
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

try:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version();")).fetchone()
        print("✅ DATABASE CONNECTION SUCCESSFUL!")
        print("Connected to:", result[0][:40], "...")
except Exception as e:
    print("❌ CONNECTION FAILED:", str(e))