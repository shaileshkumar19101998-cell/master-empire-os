import os
import time
import json
import uuid
import re
from typing import List, Dict, Optional
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel, Field

# Google GenAI SDK (Conditional Import for Zero-Crash Safety)
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PRIMARY_MODEL = os.getenv("PRIMARY_GEMINI_MODEL", "gemini-2.5-flash")
FALLBACK_MODEL = os.getenv("FALLBACK_GEMINI_MODEL", "gemini-2.5-flash")
API_DELAY_SECONDS = int(os.getenv("API_DELAY_SECONDS", "4"))
MAX_RETRIES = int(os.getenv("MAX_API_RETRIES", "3"))

# ====================================================================
# PYDANTIC STRUCTURED SCHEMAS
# ====================================================================

class ChapterOutline(BaseModel):
    chapter_number: int
    title: str
    learning_objectives: List[str]
    key_topics: List[str]
    practical_deliverables: List[str]

class BookOutline(BaseModel):
    title: str
    target_niche: str
    tier_level: str
    target_word_count: int
    executive_summary: str
    table_of_contents: List[ChapterOutline]

class ChapterContent(BaseModel):
    chapter_number: int
    title: str
    word_count: int
    content_markdown: str
    has_code_or_templates: bool
    has_exercises: bool

# ====================================================================
# DATABASE LOGGING & AUDIT UTILITIES
# ====================================================================

def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is missing.")
    return psycopg2.connect(DATABASE_URL)

def log_system_event(module: str, status: str, message: str, job_id: Optional[str] = None):
    try:
        msg = f"[{job_id}] {message}" if job_id else message
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO system_logs (module, status, message, created_at)
            VALUES (%s, %s, %s, NOW());
        """, (module, status, msg[:1000]))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[LOG ERROR] Failed to write system log: {e}")

# ====================================================================
# LLM CLIENT WRAPPER (RESILIENT & TIMEOUT PROTECTED)
# ====================================================================

def get_genai_client():
    if not GENAI_AVAILABLE:
        raise RuntimeError("google-genai SDK is not installed. Please run: pip install google-genai")
    if not GEMINI_API_KEY or GEMINI_API_KEY.strip() == "":
        raise RuntimeError("GEMINI_API_KEY is missing in environment variables.")
    return genai.Client(api_key=GEMINI_API_KEY)

def call_llm_with_retry(prompt: str, system_instruction: str = "", model_name: str = PRIMARY_MODEL, job_id: str = "") -> str:
    client = get_genai_client()
    current_model = model_name

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            config = types.GenerateContentConfig(
                temperature=0.7,
                system_instruction=system_instruction if system_instruction else None
            )
            response = client.models.generate_content(
                model=current_model,
                contents=prompt,
                config=config
            )
            if response and response.text:
                return response.text
            raise ValueError("Empty response received from LLM.")
        except Exception as e:
            err_str = str(e)
            # Permanent Authentication / Key errors -> Do NOT retry
            if "401" in err_str or "403" in err_str or "API_KEY_INVALID" in err_str:
                log_system_event("AI_ENGINE", "AUTH_FAILURE", f"Invalid API credentials on model {current_model}.", job_id)
                raise RuntimeError(f"Permanent LLM Authentication Failure: {err_str}")
            
            # Temporary rate-limits or timeouts -> Retry with exponential backoff
            wait_time = attempt * 3
            print(f"[{job_id}] LLM Attempt {attempt} failed on {current_model}. Retrying in {wait_time}s... Error: {err_str[:120]}")
            time.sleep(wait_time)
            
            # Fallback to secondary model on final retry
            if attempt == MAX_RETRIES - 1 and FALLBACK_MODEL and FALLBACK_MODEL != current_model:
                current_model = FALLBACK_MODEL
                print(f"[{job_id}] Switching to Fallback Model: {current_model}")

    raise RuntimeError(f"LLM generation failed after {MAX_RETRIES} attempts on job {job_id}.")

# ====================================================================
# QUALITY GATE ENGINE
# ====================================================================

def run_quality_gate(book_outline: BookOutline, chapters: List[ChapterContent], job_id: str) -> Dict[str, any]:
    failures = []
    total_words = sum(c.word_count for c in chapters)
    
    # 1. Target Word Count Check
    min_required = int(book_outline.target_word_count * 0.70)  # At least 70% of theoretical target
    if total_words < min_required:
        failures.append(f"Word count failure: Generated {total_words} words (Minimum required: {min_required}).")

    # 2. Chapter Count Check
    expected_chapters = len(book_outline.table_of_contents)
    if len(chapters) != expected_chapters:
        failures.append(f"Chapter count mismatch: Expected {expected_chapters}, got {len(chapters)}.")

    # 3. Chapter Depth & Empty Sections Check
    for c in chapters:
        if c.word_count < 300:
            failures.append(f"Chapter #{c.chapter_number} depth failure: only {c.word_count} words.")
        if "TODO" in c.content_markdown or "Lorem Ipsum" in c.content_markdown or "Insert Code" in c.content_markdown:
            failures.append(f"Chapter #{c.chapter_number} contains placeholder text.")

    # 4. Repetition Filter (Check for excessive duplicate phrases)
    full_text = " ".join(c.content_markdown for c in chapters)
    words = re.findall(r'\b\w+\b', full_text.lower())
    if len(words) > 1000:
        unique_word_ratio = len(set(words)) / len(words)
        if unique_word_ratio < 0.20:
            failures.append(f"Excessive vocabulary repetition detected: unique ratio is {unique_word_ratio:.2f}.")

    is_passed = len(failures) == 0
    return {
        "passed": is_passed,
        "total_words": total_words,
        "total_chapters": len(chapters),
        "failures": failures
    }

# ====================================================================
# MULTI-STAGE RECURSIVE BOOK WRITER
# ====================================================================

def generate_enterprise_book(topic: str, tier: str = "Level 1 — Foundation", target_words: int = 5000) -> Optional[int]:
    job_id = f"JOB-{uuid.uuid4().hex[:8].upper()}"
    print(f"\n=======================================================")
    print(f"🚀 STARTING ATOMIC BOOK GENERATION [{job_id}]")
    print(f"Topic: {topic} | Tier: {tier} | Target: {target_words} words")
    print(f"=======================================================")

    log_system_event("AI_ENGINE", "JOB_START", f"Starting generation for topic '{topic}' ({tier})", job_id)

    # ----------------------------------------------------
    # STAGE 1: MASTER OUTLINE GENERATION (JSON)
    # ----------------------------------------------------
    num_chapters = 5 if target_words <= 6000 else (7 if target_words <= 12000 else 10)
    words_per_chapter = target_words // num_chapters

    outline_prompt = f"""
    Create a detailed, world-class book outline for an authoritative guide on: "{topic}".
    Tier: {tier}
    Total Target Words: {target_words}
    Number of Chapters: {num_chapters} (approx {words_per_chapter} words each).

    Return ONLY a valid JSON object matching this exact schema:
    {{
        "title": "Full Professional Book Title",
        "target_niche": "Target Audience Niche",
        "tier_level": "{tier}",
        "target_word_count": {target_words},
        "executive_summary": "Comprehensive 3-paragraph summary of what this book teaches",
        "table_of_contents": [
            {{
                "chapter_number": 1,
                "title": "Chapter Title",
                "learning_objectives": ["Goal 1", "Goal 2"],
                "key_topics": ["Topic A", "Topic B", "Topic C"],
                "practical_deliverables": ["Checklist", "Real-world Code/Workflow"]
            }}
        ]
    }}
    """

    print(f"[{job_id}] Stage 1: Generating Master Outline via LLM...")
    try:
        raw_outline_text = call_llm_with_retry(
            prompt=outline_prompt,
            system_instruction="You are a world-class technical author and curriculum designer. Output ONLY valid JSON.",
            job_id=job_id
        )
        clean_json_str = re.sub(r'^```json\s*', '', raw_outline_text.strip(), flags=re.MULTILINE)
        clean_json_str = re.sub(r'\s*```$', '', clean_json_str.strip(), flags=re.MULTILINE)
        outline_dict = json.loads(clean_json_str)
        book_outline = BookOutline(**outline_dict)
    except Exception as e:
        log_system_event("AI_ENGINE", "OUTLINE_FAILED", f"Failed to generate valid outline: {e}", job_id)
        print(f"[{job_id}] ❌ OUTLINE GENERATION FAILED: {e}")
        return None

    # ----------------------------------------------------
    # STAGE 2: RECURSIVE CHAPTER-BY-CHAPTER GENERATION
    # ----------------------------------------------------
    generated_chapters: List[ChapterContent] = []
    chapter_summaries: List[str] = []

    for ch_info in book_outline.table_of_contents:
        print(f"[{job_id}] Stage 2: Writing Chapter {ch_info.chapter_number}/{num_chapters} - '{ch_info.title}'...")
        time.sleep(API_DELAY_SECONDS)  # 4-Second Rate Limit Guard

        context_memory = "\n".join(chapter_summaries[-3:]) if chapter_summaries else "First Chapter."

        chapter_prompt = f"""
        You are writing Chapter #{ch_info.chapter_number} for the world-class book: "{book_outline.title}".
        Chapter Title: {ch_info.title}
        Target Chapter Length: {words_per_chapter}+ words.
        Learning Objectives: {', '.join(ch_info.learning_objectives)}
        Key Topics: {', '.join(ch_info.key_topics)}
        Practical Deliverables: {', '.join(ch_info.practical_deliverables)}

        Previous Context Summary:
        {context_memory}

        RULES:
        1. Write deep, practical, professional markdown content.
        2. Zero fluff, zero duplicate filler paragraphs.
        3. Include real code snippets, step-by-step tutorials, checklists, and case studies.
        4. NEVER use fake statistics or guaranteed income claims.
        """

        try:
            ch_text = call_llm_with_retry(
                prompt=chapter_prompt,
                system_instruction="You are an expert industry practitioner. Write comprehensive, actionable textbook-grade chapters.",
                job_id=job_id
            )
            ch_word_count = len(re.findall(r'\b\w+\b', ch_text))
            
            ch_obj = ChapterContent(
                chapter_number=ch_info.chapter_number,
                title=ch_info.title,
                word_count=ch_word_count,
                content_markdown=ch_text,
                has_code_or_templates="```" in ch_text,
                has_exercises="exercise" in ch_text.lower() or "checklist" in ch_text.lower()
            )
            generated_chapters.append(ch_obj)
            chapter_summaries.append(f"Ch {ch_info.chapter_number} ({ch_info.title}): Covered {', '.join(ch_info.key_topics[:2])}.")
            print(f"[{job_id}] -> Chapter {ch_info.chapter_number} completed: {ch_word_count} words.")
        except Exception as e:
            log_system_event("AI_ENGINE", "CHAPTER_FAILED", f"Failed on Chapter {ch_info.chapter_number}: {e}", job_id)
            print(f"[{job_id}] ❌ CHAPTER GENERATION FAILED. Aborting generation to prevent orphan records.")
            return None

    # ----------------------------------------------------
    # STAGE 3: AUTOMATIC QUALITY GATE
    # ----------------------------------------------------
    print(f"[{job_id}] Stage 3: Running Automated Quality Gate...")
    qg_result = run_quality_gate(book_outline, generated_chapters, job_id)

    if not qg_result["passed"]:
        log_system_event("QUALITY_GATE", "FAILED", f"Quality gate rejected book: {'; '.join(qg_result['failures'])}", job_id)
        print(f"[{job_id}] ❌ QUALITY GATE FAILED:")
        for fail in qg_result["failures"]:
            print(f"   - {fail}")
        return None

    print(f"[{job_id}] ✅ QUALITY GATE PASSED! Total Words: {qg_result['total_words']} across {qg_result['total_chapters']} chapters.")

    # ----------------------------------------------------
    # STAGE 4: ATOMIC STAGING INTO PENDING_APPROVALS
    # ----------------------------------------------------
    print(f"[{job_id}] Stage 4: Staging into pending_approvals table...")
    try:
        # Assemble Full Book Document
        assembled_doc = f"# {book_outline.title}\n\n"
        assembled_doc += f"**Niche:** {book_outline.target_niche} | **Tier:** {book_outline.tier_level}\n\n"
        assembled_doc += f"## Executive Summary\n{book_outline.executive_summary}\n\n---\n\n"
        assembled_doc += "## Table of Contents\n"
        for c in generated_chapters:
            assembled_doc += f"- Chapter {c.chapter_number}: {c.title} ({c.word_count} words)\n"
        assembled_doc += "\n---\n\n"

        for c in generated_chapters:
            assembled_doc += f"\n\n# Chapter {c.chapter_number}: {c.title}\n\n{c.content_markdown}\n\n---"

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO pending_approvals (task_type, title, niche, proposed_content, status, created_at)
            VALUES (%s, %s, %s, %s, 'PENDING', NOW())
            RETURNING id;
        """, (
            book_outline.tier_level,
            book_outline.title,
            book_outline.target_niche,
            assembled_doc
        ))
        approval_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        log_system_event("AI_ENGINE", "SUCCESS", f"Book '{book_outline.title}' ({qg_result['total_words']} words) staged for human approval. ID: #{approval_id}", job_id)
        print(f"[{job_id}] 🏆 SUCCESS: Staged as Approval Task #{approval_id} (PENDING_APPROVAL).")
        return approval_id
    except Exception as e:
        log_system_event("AI_ENGINE", "DB_ERROR", f"Failed to stage approval record: {e}", job_id)
        print(f"[{job_id}] ❌ DATABASE INSERTION FAILED: {e}")
        return None

if __name__ == "__main__":
    # Test Run
    print("Worker module loaded. Use 'generate_enterprise_book()' to initiate generation.")