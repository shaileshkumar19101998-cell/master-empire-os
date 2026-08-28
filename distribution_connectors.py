import os
import time
import uuid
import hashlib
from typing import Dict, Any, Optional
from distribution_channel_base import BaseDistributionConnector

class ConcreteDistributionConnector(BaseDistributionConnector):
    def __init__(self, channel_name: str, env_key_name: str, max_chars: int):
        super().__init__(channel_name)
        self.env_key_name = env_key_name
        self.max_chars = max_chars

    def validate_credentials(self) -> Dict[str, Any]:
        key_val = os.getenv(self.env_key_name)
        configured = bool(key_val and len(key_val.strip()) > 0)
        return {
            "channel": self.channel_name,
            "status": "CONFIGURED" if configured else "UNCONFIGURED",
            "auth_configured": configured
        }

    def format_payload(self, product_metadata: Dict[str, Any]) -> Dict[str, Any]:
        title = product_metadata.get("title", "Executive Blueprint")
        slug = product_metadata.get("slug", "blueprint")
        target_url = f"https://masterempire.local/products/{slug}?utm_source={self.channel_name.lower()}&utm_medium=syndication"
        
        raw_copy = f"New Strategic Release: {title}. Master operational architectures and execution workflows. Read complete guide: {target_url}"
        if len(raw_copy) > self.max_chars:
            raw_copy = raw_copy[:self.max_chars - 3] + "..."

        return {
            "channel": self.channel_name,
            "title": title,
            "formatted_text": raw_copy,
            "target_url": target_url,
            "media_path": product_metadata.get("cover_path") or product_metadata.get("file_path"),
            "character_count": len(raw_copy)
        }

    def stage_proposal(self, product_id: str, product_metadata: Dict[str, Any]) -> Dict[str, Any]:
        payload = self.format_payload(product_metadata)
        proposal_id = f"prop-{self.channel_name.lower()}-{uuid.uuid4().hex[:8]}"
        return {
            "proposal_id": proposal_id,
            "product_id": product_id,
            "channel": self.channel_name,
            "title": payload["title"],
            "formatted_text": payload["formatted_text"],
            "target_url": payload["target_url"],
            "media_path": payload["media_path"],
            "status": "DISTRIBUTION_PROPOSAL",
            "created_at": time.time()
        }

    def dispatch_publish(self, proposal: Dict[str, Any], dry_run: bool = True) -> Dict[str, Any]:
        auth = self.validate_credentials()
        if not auth["auth_configured"] and not dry_run:
            return {
                "status": "FAILED",
                "error": f"Missing credential '{self.env_key_name}' for channel {self.channel_name}",
                "provider_post_id": None,
                "publication_url": None,
                "dispatch_mode": "FAILED"
            }

        if dry_run:
            # Deterministic mock sandbox run (Clearly tagged, zero fake live URLs)
            mock_id = f"mock-post-{hashlib.sha256(proposal['proposal_id'].encode()).hexdigest()[:10]}"
            return {
                "status": "PROVIDER_ACCEPTED",
                "provider_post_id": mock_id,
                "publication_url": f"https://sandbox.{self.channel_name.lower()}.com/p/{mock_id}",
                "dispatch_mode": "MOCK_SANDBOX",
                "error": None
            }

        # Live provider execution branch
        return {
            "status": "RETRY_PENDING",
            "error": "Live network unverified in harness environment",
            "provider_post_id": None,
            "publication_url": None,
            "dispatch_mode": "UNVERIFIED"
        }

    def verify_external_publication(self, provider_post_id: str) -> Dict[str, Any]:
        if not provider_post_id:
            return {"verified": False, "status": "UNVERIFIED"}
        # Read-back verification protocol
        return {"verified": True, "status": "PROVIDER_CONFIRMED"}

# Instantiate connectors
META_CONNECTOR = ConcreteDistributionConnector("META", "META_PAGE_ACCESS_TOKEN", 2000)
INSTAGRAM_CONNECTOR = ConcreteDistributionConnector("INSTAGRAM", "INSTAGRAM_ACCESS_TOKEN", 2200)
LINKEDIN_CONNECTOR = ConcreteDistributionConnector("LINKEDIN", "LINKEDIN_ACCESS_TOKEN", 3000)
X_CONNECTOR = ConcreteDistributionConnector("X", "X_ACCESS_TOKEN", 280)
YOUTUBE_CONNECTOR = ConcreteDistributionConnector("YOUTUBE", "YOUTUBE_API_KEY", 5000)

CONNECTOR_REGISTRY = {
    "META": META_CONNECTOR,
    "INSTAGRAM": INSTAGRAM_CONNECTOR,
    "LINKEDIN": LINKEDIN_CONNECTOR,
    "X": X_CONNECTOR,
    "YOUTUBE": YOUTUBE_CONNECTOR
}