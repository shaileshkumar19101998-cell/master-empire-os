import os
import zipfile
import hashlib
import json
import time
import uuid
import sqlite3
from typing import Dict, Any, Optional

DB_PATH = "autonomous_local.db"
OUTPUT_DIR = "generated_products"
os.makedirs(OUTPUT_DIR, exist_ok=True)

class AssetBundleEngine:
    @staticmethod
    def _compute_sha256(file_path: str) -> str:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def generate_cover(blueprint: Dict[str, Any], job_id: str) -> Dict[str, Any]:
        """
        Generates a clean, deterministic SVG cover asset without fabricated claims.
        """
        cover_path = os.path.join(OUTPUT_DIR, f"{job_id}_cover.svg")
        topic = blueprint.get("topic", "Executive Manual")
        target_country = blueprint.get("target_country", "US")
        target_lang = blueprint.get("target_language", "en")
        audience = blueprint.get("target_audience", "Practitioners")

        svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 1200" width="800" height="1200">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0f172a" />
      <stop offset="100%" stop-color="#1e293b" />
    </linearGradient>
  </defs>
  <rect width="800" height="1200" fill="url(#bg)" />
  <rect x="40" y="40" width="720" height="1120" fill="none" stroke="#38bdf8" stroke-width="2" opacity="0.3"/>
  <text x="400" y="250" font-family="system-ui, sans-serif" font-size="20" font-weight="600" fill="#38bdf8" text-anchor="middle" letter-spacing="4">EXECUTIVE PLAYBOOK</text>
  <text x="400" y="450" font-family="system-ui, sans-serif" font-size="42" font-weight="800" fill="#ffffff" text-anchor="middle">{topic.upper()}</text>
  <text x="400" y="520" font-family="system-ui, sans-serif" font-size="22" font-weight="400" fill="#94a3b8" text-anchor="middle">Operational Blueprint &amp; Execution Framework</text>
  <line x1="200" y1="580" x2="600" y2="580" stroke="#38bdf8" stroke-width="2" opacity="0.5"/>
  <text x="400" y="800" font-family="system-ui, sans-serif" font-size="18" fill="#cbd5e1" text-anchor="middle">Target: {audience}</text>
  <text x="400" y="840" font-family="system-ui, sans-serif" font-size="16" fill="#64748b" text-anchor="middle">Jurisdiction: {target_country} | Language: {target_lang}</text>
  <text x="400" y="1050" font-family="system-ui, sans-serif" font-size="14" fill="#475569" text-anchor="middle">MASTER EMPIRE OS • DETERMINISTIC BLUEPRINT</text>
</svg>"""

        with open(cover_path, "w", encoding="utf-8") as f:
            f.write(svg_content)

        checksum = AssetBundleEngine._compute_sha256(cover_path)
        return {
            "cover_path": cover_path,
            "cover_checksum": checksum,
            "cover_format": "image/svg+xml",
            "cover_size_bytes": os.path.getsize(cover_path)
        }

    @staticmethod
    def create_release_bundle(blueprint: Dict[str, Any], package_bundle: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates a unified ZIP release bundle containing PDF, EPUB, Cover, and SHA-256 Manifest.
        """
        job_id = package_bundle.get("package_job_id", f"pkg-{uuid.uuid4().hex[:8]}")
        opp_id = blueprint.get("opportunity_id")
        zip_path = os.path.join(OUTPUT_DIR, f"{job_id}_release_bundle.zip")

        cover_meta = AssetBundleEngine.generate_cover(blueprint, job_id)
        pdf_path = package_bundle["pdf_artifact"]["pdf_path"]
        epub_path = package_bundle["epub_artifact"]["epub_path"]
        pdf_checksum = package_bundle["pdf_artifact"]["pdf_checksum"]
        epub_checksum = package_bundle["epub_artifact"]["epub_checksum"]
        cover_checksum = cover_meta["cover_checksum"]

        manifest_data = {
            "package_job_id": job_id,
            "opportunity_id": opp_id,
            "topic": blueprint.get("topic"),
            "governance_status": "READY_FOR_CATALOG",
            "created_at": time.time(),
            "artifacts": {
                "pdf": {"filename": os.path.basename(pdf_path), "sha256": pdf_checksum},
                "epub": {"filename": os.path.basename(epub_path), "sha256": epub_checksum},
                "cover": {"filename": os.path.basename(cover_meta["cover_path"]), "sha256": cover_checksum}
            }
        }

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(pdf_path, arcname=os.path.basename(pdf_path))
            z.write(epub_path, arcname=os.path.basename(epub_path))
            z.write(cover_meta["cover_path"], arcname=os.path.basename(cover_meta["cover_path"]))
            z.writestr("manifest.json", json.dumps(manifest_data, indent=2))

        zip_checksum = AssetBundleEngine._compute_sha256(zip_path)

        # Store bundle record in isolated DB table
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS release_bundles (
                    bundle_id TEXT PRIMARY KEY,
                    opportunity_id TEXT NOT NULL,
                    zip_path TEXT NOT NULL,
                    zip_checksum TEXT NOT NULL,
                    cover_path TEXT NOT NULL,
                    cover_checksum TEXT NOT NULL,
                    governance_status TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            cur.execute("""
                INSERT OR REPLACE INTO release_bundles
                (bundle_id, opportunity_id, zip_path, zip_checksum, cover_path, cover_checksum, governance_status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (job_id, opp_id, zip_path, zip_checksum, cover_meta["cover_path"], cover_checksum, "READY_FOR_CATALOG", time.time()))
            conn.commit()
            conn.close()
        except Exception:
            pass

        return {
            "bundle_id": job_id,
            "opportunity_id": opp_id,
            "topic": blueprint.get("topic"),
            "zip_path": zip_path,
            "zip_checksum": zip_checksum,
            "zip_size_bytes": os.path.getsize(zip_path),
            "cover_artifact": cover_meta,
            "pdf_artifact": package_bundle["pdf_artifact"],
            "epub_artifact": package_bundle["epub_artifact"],
            "governance_status": "READY_FOR_CATALOG",
            "search_volume_monthly": None,
            "cpc_value_usd": None,
            "competition_density": None
        }

bundle_engine = AssetBundleEngine()