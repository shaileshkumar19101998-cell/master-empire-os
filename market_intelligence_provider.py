import os, datetime, requests
from typing import Dict, Any, Optional

class BaseMarketDataProvider:
    provider_name: str = "BASE_PROVIDER"
    def get_status(self) -> Dict[str, Any]:
        return {"provider": self.provider_name, "status": "CONNECTOR_REQUIRED", "confidence_score": 0.0, "data_status": "DATA_UNAVAILABLE"}
    def fetch_market_signals(self, niche: str, country: str = "GLOBAL") -> Dict[str, Any]:
        return {"provider": self.provider_name, "niche": niche, "country": country, "demand_signal": None, "competition_signal": None, "monetization_signal": None, "seo_gap_signal": None, "velocity_signal": None, "source_type": "DATA_UNAVAILABLE", "provider_status": "CONNECTOR_REQUIRED", "confidence_score": 0.0, "evidence_freshness": "DATA_UNAVAILABLE", "last_evaluated_at": datetime.datetime.utcnow().isoformat()}

class DataForSEOProvider(BaseMarketDataProvider):
    provider_name: str = "DATAFORSEO_PROVIDER"
    def __init__(self):
        self.login = os.getenv("DATAFORSEO_LOGIN")
        self.password = os.getenv("DATAFORSEO_PASSWORD")
    def get_status(self) -> Dict[str, Any]:
        if not self.login or not self.password:
            return {"provider": self.provider_name, "status": "CONNECTOR_REQUIRED", "confidence_score": 0.0, "data_status": "DATA_UNAVAILABLE", "auth_configured": False}
        return {"provider": self.provider_name, "status": "CONNECTED", "confidence_score": 95.0, "data_status": "LIVE_EXTERNAL", "auth_configured": True}

class ProviderRegistry:
    def __init__(self):
        self._providers = {}
    def register(self, name: str, provider: BaseMarketDataProvider):
        self._providers[name] = provider
    def get_active_provider(self) -> BaseMarketDataProvider:
        return self._providers.get("primary", BaseMarketDataProvider())

registry = ProviderRegistry()
registry.register("primary", DataForSEOProvider())
