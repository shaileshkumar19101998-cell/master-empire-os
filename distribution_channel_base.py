from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseDistributionConnector(ABC):
    def __init__(self, channel_name: str):
        self.channel_name = channel_name

    @abstractmethod
    def validate_credentials(self) -> Dict[str, Any]:
        """Verifies presence of API credentials. Must NEVER return actual secret values."""
        pass

    @abstractmethod
    def format_payload(self, product_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Formats channel-compliant copy, UTM tracking links, and media paths."""
        pass

    @abstractmethod
    def stage_proposal(self, product_id: str, product_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Stages distribution copy without external HTTP publish call."""
        pass

    @abstractmethod
    def dispatch_publish(self, proposal: Dict[str, Any], dry_run: bool = True) -> Dict[str, Any]:
        """Executes publish request only with valid operator authorization."""
        pass

    @abstractmethod
    def verify_external_publication(self, provider_post_id: str) -> Dict[str, Any]:
        """Performs read-back verification before confirming PUBLISHED status."""
        pass