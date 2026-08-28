import os
import hashlib
import sqlite3
from typing import Dict, Any

DB_PATH = "autonomous_local.db"

class StructuralQAEngine:
    MIN_CHAPTERS = 3
    MIN_WORDS = 100

    @staticmethod
    def verify_file_checksum(file_path: str, expected_checksum: str) -> bool:
        if not os.path.exists(file_path):
            return False
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            hasher.update(f.read())
        return hasher.hexdigest() == expected_checksum

    @staticmethod
    def evaluate_product(product_artifact: Dict[str, Any]) -> Dict[str, Any]:
        failures = []
        chapters = product_artifact.get("chapters", [])
        total_words = product_artifact.get("total_words", 0)
        pdf_path = product_artifact.get("pdf_path", "")
        expected_checksum = product_artifact.get("pdf_checksum", "")

        # 1. Structural Checks
        if len(chapters) < StructuralQAEngine.MIN_CHAPTERS:
            failures.append(f"Insufficient chapters: {len(chapters)} < {StructuralQAEngine.MIN_CHAPTERS}")

        if total_words < StructuralQAEngine.MIN_WORDS:
            failures.append(f"Insufficient word count: {total_words} < {StructuralQAEngine.MIN_WORDS}")

        for ch in chapters:
            if not ch.get("chapter_title"):
                failures.append(f"Chapter {ch.get('chapter_id')} missing title")
            if not ch.get("content"):
                failures.append(f"Chapter {ch.get('chapter_id')} missing content")

        # 2. File & Checksum Verification
        if not os.path.exists(pdf_path):
            failures.append("PDF artifact file missing")
        else:
            if not StructuralQAEngine.verify_file_checksum(pdf_path, expected_checksum):
                failures.append("PDF checksum mismatch or tampering detected")

        # 3. Provenance Verification
        prov = product_artifact.get("provenance", {})
        if not prov.get("source_type"):
            failures.append("Missing source provenance metadata")

        qa_passed = len(failures) == 0
        final_qa_status = "QA_PASSED" if qa_passed else "QA_FAILED"
        final_gov_status = "READY_FOR_CATALOG" if qa_passed else "FAILED"

        # Record result in isolated DB table
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO synthesized_products
                (product_job_id, opportunity_id, title, pdf_path, pdf_checksum, total_words, chapter_count, qa_status, governance_status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                product_artifact["product_job_id"],
                product_artifact["opportunity_id"],
                product_artifact["title"],
                pdf_path,
                expected_checksum,
                total_words,
                len(chapters),
                final_qa_status,
                final_gov_status,
                product_artifact.get("created_at", 0)
            ))
            conn.commit()
            conn.close()
        except Exception:
            pass

        return {
            "product_job_id": product_artifact.get("product_job_id"),
            "qa_status": final_qa_status,
            "governance_status": final_gov_status,
            "checks_passed": qa_passed,
            "failures": failures,
            "chapter_count": len(chapters),
            "total_words": total_words,
            "checksum_verified": qa_passed
        }

qa_engine = StructuralQAEngine()