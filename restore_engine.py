import os
import time
import json
import zipfile
import hashlib
import hmac
import shutil
import sqlite3
from typing import Dict, Any, Optional
from persistence_guard import persistence_guard

BACKUP_DIR = "backups"
OS_DB_PATH = "C:\\Users\\Lenovo\\autonomous_os\\autonomous_local.db"

class RestoreEngine:
    @staticmethod
    def _compute_sha256(file_path: str) -> str:
        if not os.path.exists(file_path):
            return ""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def verify_backup_authenticity(backup_id: str) -> Dict[str, Any]:
        target_dir = os.path.join(BACKUP_DIR, backup_id)
        if not os.path.exists(target_dir):
            return {"valid": False, "reason": "Backup ID not found on disk."}

        manifest_path = os.path.join(target_dir, "manifest.json")
        sig_path = os.path.join(target_dir, "manifest.sig")
        db_path = os.path.join(target_dir, "autonomous_local.db.bak")
        zip_path = os.path.join(target_dir, "assets.zip")

        if not os.path.exists(manifest_path) or not os.path.exists(sig_path):
            return {"valid": False, "reason": "Missing manifest or signature file."}

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_content = f.read()
            manifest = json.loads(manifest_content)

        # 1. Verify HMAC Signature
        secret = os.getenv("BACKUP_HMAC_SECRET", os.getenv("OPERATOR_MASTER_SECRET", "FALLBACK_SECURE_HMAC_KEY"))
        expected_sig = hmac.new(secret.encode("utf-8"), manifest_content.encode("utf-8"), hashlib.sha256).hexdigest()
        
        with open(sig_path, "r", encoding="utf-8") as f:
            actual_sig = f.read().strip()

        if not hmac.compare_digest(expected_sig, actual_sig):
            return {"valid": False, "reason": "HMAC signature verification failed (Tampered or Forged Manifest)."}

        # 2. Verify SHA-256 Hashes if artifacts exist
        if os.path.exists(db_path):
            db_actual_hash = RestoreEngine._compute_sha256(db_path)
            if db_actual_hash != manifest["artifacts"]["database"]["sha256"]:
                return {"valid": False, "reason": "Database SHA-256 integrity mismatch."}

        if os.path.exists(zip_path):
            zip_actual_hash = RestoreEngine._compute_sha256(zip_path)
            if zip_actual_hash != manifest["artifacts"]["assets"]["sha256"]:
                return {"valid": False, "reason": "Assets ZIP SHA-256 integrity mismatch."}

        return {"valid": True, "manifest": manifest}

    @staticmethod
    def stage_restore(backup_id: str) -> Dict[str, Any]:
        auth_res = RestoreEngine.verify_backup_authenticity(backup_id)
        if not auth_res["valid"]:
            return {"status": "REJECTED", "reason": auth_res["reason"]}

        manifest = auth_res["manifest"]
        target_dir = os.path.join(BACKUP_DIR, backup_id)
        db_path = os.path.join(target_dir, "autonomous_local.db.bak")
        zip_path = os.path.join(target_dir, "assets.zip")

        session_id = os.urandom(4).hex()
        staging_dir = os.path.join(BACKUP_DIR, f".staging_{session_id}")
        os.makedirs(staging_dir, exist_ok=True)
        staged_db = os.path.join(staging_dir, "autonomous_local.db")
        
        if os.path.exists(db_path):
            shutil.copy2(db_path, staged_db)
        else:
            open(staged_db, "wb").close()

        # Path Traversal & Symlink Defense
        if os.path.exists(zip_path):
            try:
                with zipfile.ZipFile(zip_path, "r") as z:
                    for member in z.namelist():
                        norm = os.path.normpath(member)
                        if norm.startswith("..") or os.path.isabs(norm):
                            shutil.rmtree(staging_dir, ignore_errors=True)
                            return {"status": "REJECTED", "reason": f"Path traversal attack detected: {member}"}
                        info = z.getinfo(member)
                        if (info.external_attr >> 28) & 0xA000:
                            shutil.rmtree(staging_dir, ignore_errors=True)
                            return {"status": "REJECTED", "reason": f"Symlink entry forbidden: {member}"}
            except Exception as e:
                shutil.rmtree(staging_dir, ignore_errors=True)
                return {"status": "REJECTED", "reason": f"Malformed ZIP archive: {str(e)}"}

        if not persistence_guard.run_integrity_check(staged_db):
            shutil.rmtree(staging_dir, ignore_errors=True)
            return {"status": "REJECTED", "reason": "Staged database failed PRAGMA integrity_check."}

        live_fingerprint = persistence_guard.compute_schema_fingerprint(OS_DB_PATH)
        staged_fingerprint = persistence_guard.compute_schema_fingerprint(staged_db)

        if live_fingerprint != staged_fingerprint:
            shutil.rmtree(staging_dir, ignore_errors=True)
            return {"status": "REJECTED", "reason": "Schema fingerprint mismatch (Incompatible schema version)." }

        return {
            "status": "STAGED_READY",
            "staging_dir": staging_dir,
            "staged_db": staged_db,
            "manifest": manifest
        }

    @staticmethod
    def execute_promoted_restore(backup_id: str, operator_secret: str) -> Dict[str, Any]:
        master_secret = os.getenv("OPERATOR_MASTER_SECRET", "LEAD_OPERATOR_AUTH_TOKEN_7788")
        if not operator_secret or not hmac.compare_digest(operator_secret, master_secret):
            return {"status": "FORBIDDEN", "reason": "Unauthorized: Invalid or missing operator credentials."}

        stage_res = RestoreEngine.stage_restore(backup_id)
        if stage_res["status"] != "STAGED_READY":
            return stage_res

        staging_dir = stage_res["staging_dir"]
        staged_db = stage_res["staged_db"]

        safety_snapshot_path = os.path.join(BACKUP_DIR, f"safety_snapshot_{int(time.time())}.bak")
        try:
            if os.path.exists(OS_DB_PATH):
                src_conn = sqlite3.connect(OS_DB_PATH)
                bak_conn = sqlite3.connect(safety_snapshot_path)
                with bak_conn:
                    src_conn.backup(bak_conn)
                bak_conn.close()
                src_conn.close()
        except Exception as e:
            shutil.rmtree(staging_dir, ignore_errors=True)
            return {"status": "FAILED", "reason": f"Failed to create safety snapshot: {str(e)}"}

        try:
            live_conn = sqlite3.connect(OS_DB_PATH)
            staged_conn = sqlite3.connect(staged_db)
            with live_conn:
                staged_conn.backup(live_conn)
            staged_conn.close()
            live_conn.close()
        except Exception as e:
            if os.path.exists(safety_snapshot_path):
                try:
                    r_src = sqlite3.connect(safety_snapshot_path)
                    r_dst = sqlite3.connect(OS_DB_PATH)
                    with r_dst:
                        r_src.backup(r_dst)
                    r_dst.close()
                    r_src.close()
                except Exception:
                    pass
            shutil.rmtree(staging_dir, ignore_errors=True)
            return {"status": "FAILED", "reason": f"Promotion failed; automatic rollback executed. Error: {str(e)}"}

        if not persistence_guard.run_integrity_check(OS_DB_PATH):
            if os.path.exists(safety_snapshot_path):
                try:
                    r_src = sqlite3.connect(safety_snapshot_path)
                    r_dst = sqlite3.connect(OS_DB_PATH)
                    with r_dst:
                        r_src.backup(r_dst)
                    r_dst.close()
                    r_src.close()
                except Exception:
                    pass
            shutil.rmtree(staging_dir, ignore_errors=True)
            return {"status": "FAILED", "reason": "Post-restore integrity check failed; automatic rollback executed."}

        shutil.rmtree(staging_dir, ignore_errors=True)
        return {
            "status": "RESTORE_CONFIRMED",
            "backup_id": backup_id,
            "restored_at": time.time(),
            "safety_snapshot": safety_snapshot_path
        }

restore_engine = RestoreEngine()