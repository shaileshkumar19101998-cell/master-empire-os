import os
import time
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, Table, MetaData

load_dotenv()
db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(db_url)
metadata = MetaData()
metadata.reflect(bind=engine)

approvals_table = metadata.tables.get('pending_approvals')
logs_table = metadata.tables.get('system_logs')

def log_event(module: str, status: str, message: str):
    try:
        with engine.begin() as conn:
            conn.execute(logs_table.insert().values(
                module=module,
                status=status,
                message=message,
                created_at=datetime.utcnow()
            ))
    except Exception as e:
        print(f"Logging error: {e}")

def run_research_task_with_retry(topic: str, max_retries: int = 3):
    attempt = 1
    while attempt <= max_retries:
        try:
            print(f"🔄 [Attempt {attempt}/{max_retries}] Executing Research Task: '{topic}'...")
            
            # Simulated Research & Idea Generation Logic
            time.sleep(1) # Processing delay
            idea_title = f"AI Autonomous Blueprint: {topic} Growth Mastery"
            idea_niche = topic
            idea_content = f"Comprehensive framework and scaling models for {topic}."

            # Save to Pending Approvals Table (Human-in-the-Loop)
            with engine.begin() as conn:
                conn.execute(approvals_table.insert().values(
                    task_type="AUTONOMOUS_RESEARCH",
                    title=idea_title,
                    niche=idea_niche,
                    proposed_content=idea_content,
                    status="PENDING",
                    created_at=datetime.utcnow()
                ))
            
            log_event("RESEARCH_WORKER", "SUCCESS", f"Generated idea '{idea_title}' placed in PENDING queue.")
            print(f"✅ Success! Idea queued for Shailesh's approval.")
            return True

        except Exception as e:
            print(f"⚠️ Attempt {attempt} failed: {e}")
            log_event("RESEARCH_WORKER", "RETRY", f"Attempt {attempt} failed: {str(e)}")
            attempt += 1
            time.sleep(2)

    log_event("RESEARCH_WORKER", "FAILED", f"Task '{topic}' failed after {max_retries} attempts.")
    print(f"❌ Task permanently failed after {max_retries} retries.")
    return False

if __name__ == "__main__":
    print("Testing Worker Engine locally...")
    run_research_task_with_retry("B2B AI Automation")