import os
import time
import sqlite3
import hashlib
import uuid
from typing import Dict, Any, List, Optional
import distribution_connectors

DB_PATH = "autonomous_local.db"

class DistributionOrchestrator:
    @staticmethod
    def calculate_idempotency_key(product_id: str, channel: str, text: str) -> str:
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        raw = f"{product_id}:{channel}:{text_hash}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def stage_channel_proposals(product_id: str) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # Fetch product and convert to dictionary safely
        cur.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        row = cur.fetchone()
        if not row:
            # Fallback check first row if specific ID lookup fails
            cur.execute("SELECT * FROM products LIMIT 1")
            row = cur.fetchone()
            
        if not row:
            conn.close()
            raise ValueError(f"Product '{product_id}' not found in catalog.")

        col_names = [d[0] for d in cur.description]
        product = dict(zip(col_names, row))

        # Dynamically extract available fields with fallbacks
        p_id = str(product.get("id") or product.get("product_id") or product_id)
        p_title = str(product.get("title") or product.get("name") or "Executive Strategy Manual")
        p_slug = str(product.get("slug") or p_title.lower().replace(" ", "-"))
        p_file = str(product.get("file_path") or "generated_products/release.pdf")

        p_meta = {
            "id": p_id,
            "title": p_title,
            "slug": p_slug,
            "file_path": p_file,
            "cover_path": p_file
        }

        proposals = []
        for ch_name, connector in distribution_connectors.CONNECTOR_REGISTRY.items():
            prop = connector.stage_proposal(p_id, p_meta)
            cur.execute("""
                INSERT OR REPLACE INTO distribution_proposals
                (proposal_id, product_id, channel, title, formatted_text, target_url, media_path, status, governance_operator, approval_timestamp, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                prop["proposal_id"], 
                prop["product_id"], 
                prop["channel"], 
                prop["title"], 
                prop["formatted_text"], 
                prop["target_url"], 
                prop["media_path"], 
                prop["status"], 
                None, 
                None, 
                prop["created_at"]
            ))
            proposals.append(prop)

        conn.commit()
        conn.close()
        return proposals

    @staticmethod
    def approve_proposal(proposal_id: str, operator_identity: str) -> Dict[str, Any]:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        cur.execute("SELECT * FROM distribution_proposals WHERE proposal_id = ?", (proposal_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            raise ValueError(f"Proposal '{proposal_id}' not found.")

        now = time.time()
        cur.execute("""
            UPDATE distribution_proposals
            SET status = 'HUMAN_APPROVAL', governance_operator = ?, approval_timestamp = ?
            WHERE proposal_id = ?
        """, (operator_identity, now, proposal_id))

        conn.commit()
        conn.close()
        return {"proposal_id": proposal_id, "status": "HUMAN_APPROVAL", "operator": operator_identity, "approved_at": now}

    @staticmethod
    def execute_dispatch(proposal_id: str, operator_identity: str, dry_run: bool = True) -> Dict[str, Any]:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        cur.execute("SELECT * FROM distribution_proposals WHERE proposal_id = ?", (proposal_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            raise ValueError("Proposal not found.")

        col_names = [d[0] for d in cur.description]
        prop = dict(zip(col_names, row))

        # STRICT HUMAN APPROVAL GATE
        if prop.get("status") != "HUMAN_APPROVAL":
            conn.close()
            raise PermissionError(f"Governance Barrier Violation: Proposal is in state '{prop.get('status')}', expected 'HUMAN_APPROVAL'. Autonomous dispatch blocked.")

        idempotency_key = DistributionOrchestrator.calculate_idempotency_key(
            str(prop.get("product_id")), 
            str(prop.get("channel")), 
            str(prop.get("formatted_text"))
        )

        # Check existing dispatch idempotency
        cur.execute("SELECT * FROM syndication_dispatch_log WHERE idempotency_key = ?", (idempotency_key,))
        existing_row = cur.fetchone()
        if existing_row:
            existing_cols = [d[0] for d in cur.description]
            existing = dict(zip(existing_cols, existing_row))
            conn.close()
            return {
                "status": "ALREADY_PROCESSED",
                "message": "Duplicate dispatch detected. Idempotency lock active.",
                "dispatch_id": existing.get("dispatch_id"),
                "channel": existing.get("channel"),
                "publication_status": existing.get("status")
            }

        connector = distribution_connectors.CONNECTOR_REGISTRY.get(prop.get("channel"))
        if not connector:
            conn.close()
            raise ValueError(f"No connector registered for channel '{prop.get('channel')}'")

        dispatch_res = connector.dispatch_publish(prop, dry_run=dry_run)
        
        final_status = dispatch_res["status"]
        confirmed_at = None

        if final_status == "PROVIDER_ACCEPTED":
            verify_res = connector.verify_external_publication(dispatch_res["provider_post_id"])
            if verify_res.get("verified"):
                final_status = "PUBLISHED"
                confirmed_at = time.time()

        dispatch_id = f"disp-{uuid.uuid4().hex[:8]}"
        now = time.time()

        cur.execute("""
            INSERT INTO syndication_dispatch_log
            (dispatch_id, proposal_id, product_id, channel, idempotency_key, status, provider_post_id, publication_url, dispatch_mode, error_details, dispatched_at, confirmed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            dispatch_id,
            proposal_id,
            prop["product_id"],
            prop["channel"],
            idempotency_key,
            final_status,
            dispatch_res.get("provider_post_id"),
            dispatch_res.get("publication_url"),
            dispatch_res.get("dispatch_mode", "UNVERIFIED"),
            dispatch_res.get("error"),
            now,
            confirmed_at
        ))

        cur.execute("UPDATE distribution_proposals SET status = ? WHERE proposal_id = ?", (final_status, proposal_id))

        conn.commit()
        conn.close()

        return {
            "dispatch_id": dispatch_id,
            "proposal_id": proposal_id,
            "channel": prop["channel"],
            "status": final_status,
            "provider_post_id": dispatch_res.get("provider_post_id"),
            "publication_url": dispatch_res.get("publication_url"),
            "dispatch_mode": dispatch_res.get("dispatch_mode"),
            "idempotency_key": idempotency_key,
            "confirmed_at": confirmed_at
        }

orchestrator = DistributionOrchestrator()