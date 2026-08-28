import os
import time
import json
import zipfile
import hashlib
import hmac
import subprocess
import sqlite3
from typing import Dict, Any, Optional
from persistence_guard import persistence_guard

BACKUP_DIR = "backups"
ASSETS_DIR = "generated_products"
OS_DB_PATH = "C:\\Users\\Lenovo\\autonomous_os\\autonomous_local.db"

FORBIDDEN_PATTERNS = [
    ".env", ".git", "credential", "secret", "token", "password", 
    "private_key", "key", "auth", "log", "tmp", "cache", "temp"
]

class BackupEngine:
    @staticmethod
    def _compute_sha256(file_path: str) -> str:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def _is_safe_asset(rel_path: str) -> bool:
        norm = rel_path.lower().replace("\\", "/")
        if not any(norm.endswith(ext) for ext in [".pdf", ".epub", ".svg", ".zip"]):
            return False
        for p in FORBIDDEN_PATTERNS:
            if p in norm:
                return False
        return True

    @staticmethod
    def create_backup(db_path: str = OS_DB_PATH) -> Dict[str, Any]:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        backup_id = f"bkp-{int(time.time())}-{os.urandom(3).hex()}"
        target_dir = os.path.join(BACKUP_DIR, backup_id)
        os.makedirs(target_dir, exist_ok=True)

        db_bak_path = os.path.join(target_dir, "autonomous_local.db.bak")
        assets_zip_path = os.path.join(target_dir, "assets.zip")
        manifest_path = os.path.join(target_dir, "manifest.json")

        # 1. Consistent SQLite backup using Connection.backup()
        if os.path.exists(db_path):
            src_conn = sqlite3.connect(db_path)
            bak_conn = sqlite3.connect(db_bak_path)
            with bak_conn:
                src_conn.backup(bak_conn)
            bak_conn.close()
            src_conn.close()
        else:
            open(db_bak_path, "wb").close()

        # 2. Package generated assets with security filtering
        included_files = []
        if os.path.exists(ASSETS_DIR):
            with zipfile.ZipFile(assets_zip_path, "w", zipfile.ZIP_DEFLATED) as z:
                for root, _, files in os.walk(ASSETS_DIR):
                    for file in files:
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, ASSETS_DIR)
                        if BackupEngine._is_safe_asset(rel_path):
                            z.write(full_path, arcname=rel_path)
                            included_files.append(rel_path)
        else:
            with zipfile.ZipFile(assets_zip_path, "w") as z:
                pass

        db_hash = BackupEngine._compute_sha256(db_bak_path) if os.path.exists(db_bak_path) else ""
        assets_hash = BackupEngine._compute_sha256(assets_zip_path) if os.path.exists(assets_zip_path) else ""

        # 3. Git provenance
        git_commit = "UNKNOWN"
        try:
            git_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        except Exception:
            pass

        schema_fingerprint = persistence_guard.compute_schema_fingerprint(db_path)
        journal_mode = persistence_guard.get_journal_mode(db_path)

        manifest = {
            "backup_id": backup_id,
            "created_at": time.time(),
            "backup_format_version": "1.0.0",
            "database_filename": "autonomous_local.db.bak",
            "journal_mode": journal_mode,
            "git_commit": git_commit,
            "schema_fingerprint": schema_fingerprint,
            "artifacts": {
                "database": {"filename": "autonomous_local.db.bak", "size_bytes": os.path.getsize(db_bak_path) if os.path.exists(db_bak_path) else 0, "sha256": db_hash},
                "assets": {"filename": "assets.zip", "size_bytes": os.path.getsize(assets_zip_path) if os.path.exists(assets_zip_path) else 0, "sha256": assets_hash}
            },
            "included_assets_count": len(included_files),
            "status": "VALID"
        }

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        # 4. HMAC Authenticity Sealing
        secret = os.getenv("BACKUP_HMAC_SECRET", os.getenv("OPERATOR_MASTER_SECRET", "FALLBACK_SECURE_HMAC_KEY"))
        manifest_bytes = json.dumps(manifest, sort_keys=True).encode("utf-8")
        signature = hmac.new(secret.encode("utf-8"), manifest_bytes, hashlib.sha256).hexdigest()
        
        sig_path = os.path.join(target_dir, "manifest.sig")
        with open(sig_path, "w", encoding="utf-8") as f:
            f.write(signature)

        return {
            "backup_id": backup_id,
            "backup_dir": target_dir,
            "manifest": manifest,
            "signature": signature
        }

backup_engine = BackupEngine()