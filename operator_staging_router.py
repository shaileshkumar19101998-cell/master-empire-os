import os
import time
import json
import sqlite3
import hashlib
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

router = APIRouter(prefix="/operator", tags=["operator_staging"])
DB_PATH = "autonomous_local.db"

class PromotionRequest(BaseModel):
    opportunity_id: str
    bundle_id: str
    operator: str = "OPERATOR_ADMIN"
    price_usd: float = 29.00
    currency: str = "USD"

def compute_sha256(file_path: str) -> str:
    if not os.path.exists(file_path):
        return ""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

@router.get("/staging/list")
def list_staging_products():
    """
    Returns all packaged bundles ready for operator review with full provenance & null metrics.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Ensure tables exist
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
    conn.commit()

    rows = cur.execute("SELECT * FROM release_bundles ORDER BY created_at DESC").fetchall()
    
    staging_items = []
    for r in rows:
        bp_row = cur.execute("SELECT * FROM product_blueprints WHERE opportunity_id = ?", (r["opportunity_id"],)).fetchone()
        
        topic = "Executive Blueprint"
        target_country = "US"
        target_lang = "en"
        target_aud = "Practitioners"
        prov = {}

        if bp_row:
            try:
                # Try reading blueprint_json first
                bp_dict = json.loads(bp_row["blueprint_json"]) if "blueprint_json" in bp_row.keys() and bp_row["blueprint_json"] else {}
                topic = bp_dict.get("topic", topic)
                target_country = bp_dict.get("target_country", target_country)
                target_lang = bp_dict.get("target_language", target_lang)
                target_aud = bp_dict.get("target_audience", target_aud)
                prov = bp_dict.get("provenance", {})
            except Exception:
                pass

        staging_items.append({
            "bundle_id": r["bundle_id"],
            "opportunity_id": r["opportunity_id"],
            "title": f"{topic} Strategy & Execution Manual",
            "target_country": target_country,
            "target_language": target_lang,
            "target_audience": target_aud,
            "zip_path": r["zip_path"],
            "zip_checksum": r["zip_checksum"],
            "zip_exists": os.path.exists(r["zip_path"]) if r["zip_path"] else False,
            "governance_status": r["governance_status"],
            "provenance": prov,
            "search_volume_monthly": None,
            "cpc_value_usd": None,
            "competition_density": None,
            "created_at": r["created_at"]
        })
    conn.close()
    return {"status": "success", "staging_count": len(staging_items), "items": staging_items}

@router.post("/promote")
def promote_to_catalog(req: PromotionRequest):
    """
    Strictly revalidates all conditions on the backend and promotes bundle to products table idempotently.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. Fetch Bundle Record
    bundle = cur.execute("SELECT * FROM release_bundles WHERE bundle_id = ?", (req.bundle_id,)).fetchone()
    if not bundle:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Promotion Blocked: Release bundle '{req.bundle_id}' not found.")

    # 2. Fetch Blueprint Record
    bp_row = cur.execute("SELECT * FROM product_blueprints WHERE opportunity_id = ?", (bundle["opportunity_id"],)).fetchone()
    if not bp_row:
        conn.close()
        raise HTTPException(status_code=400, detail="Promotion Blocked: Missing product blueprint.")

    topic = "Executive Blueprint"
    try:
        bp_dict = json.loads(bp_row["blueprint_json"]) if "blueprint_json" in bp_row.keys() and bp_row["blueprint_json"] else {}
        topic = bp_dict.get("topic", topic)
    except Exception:
        pass

    # 3. Governance State Check
    if bundle["governance_status"] != "READY_FOR_CATALOG":
        conn.close()
        raise HTTPException(status_code=403, detail=f"Promotion Blocked: Bundle in state '{bundle['governance_status']}' is not qualified for catalog promotion.")

    # 4. Physical Bundle & Checksum Revalidation
    if not os.path.exists(bundle["zip_path"]):
        conn.close()
        raise HTTPException(status_code=400, detail="Promotion Blocked: Physical release bundle file missing from disk.")
    
    actual_hash = compute_sha256(bundle["zip_path"])
    if actual_hash != bundle["zip_checksum"]:
        conn.close()
        raise HTTPException(status_code=400, detail="Promotion Blocked: Bundle SHA-256 checksum mismatch or tampering detected.")

    # 5. Idempotency Check
    prod_id = f"prod-{req.opportunity_id.replace('live-opp-', '')}"
    existing_product = cur.execute("SELECT * FROM products WHERE id = ?", (prod_id,)).fetchone()

    if existing_product:
        conn.close()
        return {
            "status": "already_active",
            "message": "Product is already active in catalog. Idempotency preserved.",
            "product_id": prod_id,
            "governance_status": "CATALOG_ACTIVE"
        }

    # 6. Atomic Catalog Promotion & Governance Audit Entry
    now = time.time()
    title = f"{topic} Strategy & Execution Manual"
    slug = f"{topic.lower().replace(' ', '-')}-strategy"

    cur.execute("""
        INSERT INTO products (id, title, slug, price, currency, file_path, is_active)
        VALUES (?, ?, ?, ?, ?, ?, 1)
    """, (prod_id, title, slug, int(req.price_usd * 100), req.currency, bundle["zip_path"]))

    cur.execute("UPDATE release_bundles SET governance_status = 'CATALOG_ACTIVE' WHERE bundle_id = ?", (req.bundle_id,))

    action = "PROMOTE_TO_CATALOG"
    prev_state = "READY_FOR_CATALOG"
    new_state = "CATALOG_ACTIVE"
    reason = f"Human operator '{req.operator}' confirmed catalog activation."
    cur.execute("""
        INSERT INTO governance_audit_log
        (opportunity_id, action, actor, previous_state, new_state, timestamp, previous_status, new_status, reason, decided_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (req.opportunity_id, action, req.operator, prev_state, new_state, now, prev_state, new_state, reason, now))

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "message": "Product successfully promoted to catalog.",
        "product_id": prod_id,
        "title": title,
        "price_usd": req.price_usd,
        "governance_status": "CATALOG_ACTIVE",
        "promoted_at": now
    }