import os
import sqlite3
import hashlib
from typing import Dict, Any, List

DB_PATH = "C:\\Users\\Lenovo\\autonomous_os\\autonomous_local.db"

class PersistenceGuard:
    @staticmethod
    def get_journal_mode(db_path: str = DB_PATH) -> str:
        if not os.path.exists(db_path):
            return "NOT_FOUND"
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            mode = cur.execute("PRAGMA journal_mode;").fetchone()[0]
            conn.close()
            return str(mode).lower()
        except Exception:
            return "UNKNOWN"

    @staticmethod
    def run_integrity_check(db_path: str = DB_PATH) -> bool:
        if not os.path.exists(db_path):
            return False
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            res = cur.execute("PRAGMA integrity_check;").fetchone()[0]
            conn.close()
            return str(res).lower() == "ok"
        except Exception:
            return False

    @staticmethod
    def run_foreign_key_check(db_path: str = DB_PATH) -> List[Any]:
        if not os.path.exists(db_path):
            return []
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            res = cur.execute("PRAGMA foreign_key_check;").fetchall()
            conn.close()
            return res
        except Exception:
            return []

    @staticmethod
    def compute_schema_fingerprint(db_path: str = DB_PATH) -> str:
        """
        Computes a deterministic schema fingerprint across the 7 frozen core tables,
        preserving table name, ordinal position, column name, declared type, NOT NULL,
        default value, and primary key position without alphabetical column reordering.
        """
        frozen_tables = [
            "country_registry",
            "products",
            "orders",
            "revenue_ledger",
            "distribution_tasks",
            "blog_posts",
            "governance_audit_log"
        ]
        
        hasher = hashlib.sha256()
        if not os.path.exists(db_path):
            return hasher.hexdigest()

        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            
            for table in sorted(frozen_tables):
                hasher.update(f"TABLE:{table}".encode("utf-8"))
                try:
                    cols = cur.execute(f"PRAGMA table_info({table});").fetchall()
                    # PRAGMA table_info returns: (cid, name, type, notnull, dflt_value, pk)
                    for col in cols:
                        col_repr = f"col:{col[0]}:{col[1]}:{col[2]}:{col[3]}:{col[4]}:{col[5]}"
                        hasher.update(col_repr.encode("utf-8"))
                except Exception:
                    hasher.update(b"MISSING_TABLE")
            
            conn.close()
        except Exception:
            pass

        return hasher.hexdigest()

    @staticmethod
    def get_frozen_table_counts(db_path: str = DB_PATH) -> Dict[str, int]:
        frozen_tables = [
            "country_registry",
            "products",
            "orders",
            "revenue_ledger",
            "distribution_tasks",
            "blog_posts",
            "governance_audit_log"
        ]
        counts = {}
        if not os.path.exists(db_path):
            return {t: 0 for t in frozen_tables}
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            for t in frozen_tables:
                try:
                    res = cur.execute(f"SELECT COUNT(*) FROM {t};").fetchone()
                    counts[t] = res[0] if res else 0
                except Exception:
                    counts[t] = -1
            conn.close()
        except Exception:
            for t in frozen_tables:
                counts[t] = -1
        return counts

persistence_guard = PersistenceGuard()