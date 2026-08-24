import os
import time
import tempfile
import traceback
from datetime import datetime, timedelta
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

import ai_engine
import pdf_engine
import storage_engine

load_dotenv()

db_url = os.getenv("DATABASE_URL", "sqlite:///./autonomous_local.db")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

if "sqlite" in db_url:
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
else:
    engine = create_engine(db_url, pool_pre_ping=True)

MAX_DAILY_JOBS = 5
MAX_RETRIES = 3

def log_system(module: str, status: str, message: str):
    """Log audit message to system_logs without exposing secrets."""
    try:
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO system_logs (module, status, message) VALUES (:m, :s, :msg)"),
                {"m": module, "s": status, "msg": message[:500]}
            )
    except Exception:
        pass

def recover_stale_processing_jobs():
    """Recover jobs stuck in PROCESSING for > 15 minutes."""
    try:
        threshold = datetime.utcnow() - timedelta(minutes=15)
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE books SET status = 'QUEUED' WHERE status = 'PROCESSING' AND updated_at < :t"),
                {"t": threshold}
            )
    except Exception:
        pass

def check_daily_rate_limit() -> bool:
    """Ensure no more than 5 generation jobs run per 24 hours."""
    since_time = datetime.utcnow() - timedelta(days=1)
    with engine.connect() as conn:
        count = conn.execute(
            text("SELECT count(*) FROM books WHERE status IN ('COMPLETED', 'PUBLISHED') AND created_at >= :t"),
            {"t": since_time}
        ).scalar() or 0
        return count < MAX_DAILY_JOBS

def process_single_generation_job(topic: str, niche: str, base_price_inr: int = 999, version: int = 1) -> bool:
    """Execute end-to-end publishing pipeline with R2 upload and approval isolation."""
    if not check_daily_rate_limit():
        log_system("WORKER", "THROTTLED", "Daily limit of 5 generation jobs reached.")
        return False

    # 1. AI Outline & Research
    plan = ai_engine.generate_book_plan(topic, niche)
    slug = plan["slug"]
    
    # 2. Check Idempotency
    with engine.connect() as conn:
        existing_book = conn.execute(
            text("SELECT id FROM books WHERE slug = :s"),
            {"s": slug}
        ).mappings().first()
        if existing_book:
            log_system("WORKER", "SKIPPED", f"Book with slug {slug} already exists.")
            return False

    # 3. Create Book Record
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO books (slug, title, target_niche, status, version, retry_count)
            VALUES (:s, :t, :n, 'PROCESSING', :v, 0)
        """), {"s": slug, "t": plan["title"], "n": plan["niche"], "v": version})
        book_id = conn.execute(text("SELECT id FROM books WHERE slug = :s"), {"s": slug}).scalar()

    temp_pdf = None
    try:
        # 4. Synthesize Chapters with Quality Gate
        compiled_chapters = []
        for chap in plan["chapters"]:
            content = ai_engine.synthesize_chapter_content(
                plan["title"],
                chap["chapter_num"],
                chap["title"],
                chap["summary"]
            )
            compiled_chapters.append({
                "chapter_num": chap["chapter_num"],
                "title": chap["title"],
                "content": content
            })
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO book_chapters (book_id, chapter_number, title, content, status)
                    VALUES (:bid, :cnum, :title, :content, 'COMPLETED')
                """), {"bid": book_id, "cnum": chap["chapter_num"], "title": chap["title"], "content": content})

        # 5. Headless PDF Compilation in /tmp
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
            temp_pdf = tf.name

        sha256_hash = pdf_engine.compile_complete_book_pdf(
            plan["title"],
            plan["niche"],
            compiled_chapters,
            temp_pdf
        )

        # 6. Upload to Private Cloudflare R2
        r2_key = f"books/{slug}/v{version}/{slug}_v{version}.pdf"
        upload_ok = storage_engine.upload_pdf(temp_pdf, r2_key)
        if not upload_ok:
            raise RuntimeError("Cloudflare R2 upload failed.")

        # 7. Verify via HEAD object
        if not storage_engine.object_exists(r2_key):
            raise RuntimeError("Cloudflare R2 HEAD verification failed.")

        # 8. Commit Book & Approval Record
        auto_publish = os.getenv("AUTO_PUBLISH_ENABLED", "false").lower() == "true"
        final_book_status = "PUBLISHED" if auto_publish else "COMPLETED"

        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE books 
                SET status = :st, pdf_file_path = :r2_key, sha256_hash = :hash
                WHERE id = :bid
            """), {"st": final_book_status, "r2_key": r2_key, "hash": sha256_hash, "bid": book_id})

            if auto_publish:
                # Direct product ingestion
                conn.execute(text("""
                    INSERT INTO products (slug, title, tier_level, target_niche, base_price_inr, base_price_usd, pdf_file_path, status)
                    VALUES (:s, :t, 'Tier 1', :n, :inr, 12, :r2_key, 'ACTIVE')
                """), {"s": slug, "t": plan["title"], "n": plan["niche"], "inr": base_price_inr, "r2_key": r2_key})
            else:
                # Enforce Human Approval Gate
                conn.execute(text("""
                    INSERT INTO pending_approvals (book_id, status)
                    VALUES (:bid, 'PENDING')
                """), {"bid": book_id})

        log_system("WORKER", "SUCCESS", f"Successfully synthesized and uploaded {slug} to R2.")
        return True

    except Exception as e:
        log_system("WORKER", "ERROR", f"Job failed for {slug}: {str(e)}")
        with engine.begin() as conn:
            conn.execute(text("UPDATE books SET status = 'FAILED', error_message = :err WHERE id = :bid"),
                         {"err": str(e)[:250], "bid": book_id})
        return False
    finally:
        # 9. Clean up temporary files
        if temp_pdf and os.path.exists(temp_pdf):
            try:
                os.remove(temp_pdf)
            except Exception:
                pass