import datetime
from typing import Dict, Any, Optional

class BaseMarketDataProvider:
    provider_name: str = "BASE_PROVIDER"
    
    def get_status(self) -> Dict[str, Any]:
        return {"provider": self.provider_name, "status": "CONNECTOR_REQUIRED", "confidence_score": 0.0, "data_status": "DATA_UNAVAILABLE"}
        
    def fetch_market_signals(self, niche: str, country: str = "GLOBAL") -> Dict[str, Any]:
        return {"provider": self.provider_name, "niche": niche, "country": country, "demand_signal": None, "competition_signal": None, "monetization_signal": None, "seo_gap_signal": None, "velocity_signal": None, "source_type": "EXTERNAL_PROVIDER", "provider_status": "CONNECTOR_REQUIRED", "confidence_score": 0.0, "evidence_freshness": "DATA_UNAVAILABLE", "last_evaluated_at": datetime.datetime.utcnow().isoformat()}

class PublicTrendMockAdapter(BaseMarketDataProvider):
    provider_name: str = "PUBLIC_TREND_ADAPTER"

class ProviderRegistry:
    def __init__(self):
        self._providers = {}
        
    def register(self, name: str, provider: BaseMarketDataProvider):
        self._providers[name] = provider
        
    def get(self, name: str) -> Optional[BaseMarketDataProvider]:
        return self._providers.get(name)
        
    def get_all_statuses(self) -> Dict[str, Any]:
        return {k: v.get_status() for k, v in self._providers.items()}

registry = ProviderRegistry()
registry.register("default", PublicTrendMockAdapter())
