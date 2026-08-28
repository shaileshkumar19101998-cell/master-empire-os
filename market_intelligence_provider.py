import os
import json
import time
import hashlib
import sqlite3
import requests
from typing import Dict, Any, Optional
DB_PATH = "autonomous_local.db"

CACHE_TTL = int(os.getenv("MARKET_DATA_CACHE_TTL", "86400"))

class MarketSignalCache:
    @staticmethod
    def _generate_key(provider: str, keyword: str, country_code: str, language_code: str, metric_type: str) -> str:
        raw_key = f"{provider}:{keyword.strip().lower()}:{country_code.strip().upper()}:{language_code.strip().lower()}:{metric_type}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @staticmethod
    def get(provider: str, keyword: str, country_code: str, language_code: str, metric_type: str) -> Optional[Dict[str, Any]]:
        key = MarketSignalCache._generate_key(provider, keyword, country_code, language_code, metric_type)
        now = time.time()
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT normalized_payload, expires_at FROM market_signal_cache WHERE cache_key = ?", (key,))
            row = cur.fetchone()
            conn.close()
            if row:
                payload_str, expires_at = row
                if now < expires_at:
                    data = json.loads(payload_str)
                    data["cache_hit"] = True
                    return data
        except Exception:
            pass
        return None

    @staticmethod
    def set(provider: str, keyword: str, country_code: str, language_code: str, metric_type: str, payload: Dict[str, Any], source_evidence: str = ""):
        key = MarketSignalCache._generate_key(provider, keyword, country_code, language_code, metric_type)
        now = time.time()
        expires_at = now + CACHE_TTL
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO market_signal_cache 
                (cache_key, provider, keyword, country_code, language_code, metric_type, normalized_payload, source_evidence, fetched_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (key, provider, keyword.strip().lower(), country_code.strip().upper(), language_code.strip().lower(), metric_type, json.dumps(payload), source_evidence, now, expires_at))
            conn.commit()
            conn.close()
        except Exception:
            pass

class BaseMarketDataProvider:
    def get_status(self) -> Dict[str, Any]:
        raise NotImplementedError
    def fetch_market_signals(self, keyword: str, country_code: str = "US", language_code: str = "en") -> Dict[str, Any]:
        raise NotImplementedError

class ZeroStateProvider(BaseMarketDataProvider):
    def get_status(self) -> Dict[str, Any]:
        return {
            "provider": "ZERO_STATE_PROVIDER",
            "status": "CONNECTOR_REQUIRED",
            "confidence_score": 0.0,
            "data_status": "DATA_UNAVAILABLE",
            "auth_configured": False
        }

    def fetch_market_signals(self, keyword: str, country_code: str = "US", language_code: str = "en") -> Dict[str, Any]:
        return {
            "country_code": country_code,
            "language_code": language_code,
            "category": "general",
            "keyword": keyword,
            "search_intent": "informational",
            "search_volume_monthly": None,
            "trend_velocity_pct": None,
            "competition_density": None,
            "cpc_value_usd": None,
            "seo_difficulty_score": None,
            "evidence_source": "NONE",
            "evidence_freshness": "DATA_UNAVAILABLE",
            "confidence_score": 0.0,
            "provider": "ZERO_STATE_PROVIDER",
            "provider_status": "CONNECTOR_REQUIRED",
            "data_status": "DATA_UNAVAILABLE",
            "source_type": "EXTERNAL_DATA_UNAVAILABLE"
        }

class SerpApiProvider(BaseMarketDataProvider):
    def __init__(self):
        self.api_key = os.getenv("SERPAPI_API_KEY", "").strip()

    def get_status(self) -> Dict[str, Any]:
        is_auth = bool(self.api_key)
        return {
            "provider": "SERPAPI_PROVIDER",
            "status": "CONFIGURED" if is_auth else "CONNECTOR_REQUIRED",
            "confidence_score": 90.0 if is_auth else 0.0,
            "data_status": "LIVE_EXTERNAL" if is_auth else "DATA_UNAVAILABLE",
            "auth_configured": is_auth
        }

    def fetch_market_signals(self, keyword: str, country_code: str = "US", language_code: str = "en") -> Dict[str, Any]:
        cached = MarketSignalCache.get("SERPAPI", keyword, country_code, language_code, "SERP_TRENDS")
        if cached:
            return cached

        if not self.api_key:
            return {
                "country_code": country_code,
                "language_code": language_code,
                "category": "general",
                "keyword": keyword,
                "search_intent": "informational",
                "search_volume_monthly": None,
                "trend_velocity_pct": None,
                "competition_density": None,
                "cpc_value_usd": None,
                "seo_difficulty_score": None,
                "evidence_source": "NONE",
                "evidence_freshness": "DATA_UNAVAILABLE",
                "confidence_score": 0.0,
                "provider": "SERPAPI_PROVIDER",
                "provider_status": "CONNECTOR_REQUIRED",
                "data_status": "DATA_UNAVAILABLE",
                "source_type": "EXTERNAL_DATA_UNAVAILABLE"
            }

        try:
            params = {
                "engine": "google",
                "q": keyword,
                "gl": country_code.lower(),
                "hl": language_code.lower(),
                "api_key": self.api_key
            }
            res = requests.get("https://serpapi.com/search.json", params=params, timeout=10)
            if res.status_code == 200:
                data = res.json()
                paa = [item.get("question") for item in data.get("related_questions", []) if "question" in item]
                related = [item.get("query") for item in data.get("related_searches", []) if "query" in item]
                organic_count = len(data.get("organic_results", []))
                
                payload = {
                    "country_code": country_code,
                    "language_code": language_code,
                    "category": "general",
                    "keyword": keyword,
                    "search_intent": "commercial" if "shopping_results" in data or "ads" in data else "informational",
                    "search_volume_monthly": None, # Strict zero-fabrication: SerpApi does not return exact volume
                    "trend_velocity_pct": None,
                    "competition_density": None, # Reserved for Keywords Everywhere
                    "cpc_value_usd": None,       # Reserved for Keywords Everywhere
                    "seo_difficulty_score": None,
                    "evidence_source": f"Google SERP (Organic: {organic_count}, PAA: {len(paa)}, Related: {len(related)})",
                    "evidence_freshness": "REALTIME_LIVE",
                    "confidence_score": 90.0,
                    "provider": "SERPAPI_PROVIDER",
                    "provider_status": "CONFIGURED",
                    "data_status": "LIVE_EXTERNAL",
                    "source_type": "LIVE_EXTERNAL_SIGNAL"
                }
                MarketSignalCache.set("SERPAPI", keyword, country_code, language_code, "SERP_TRENDS", payload, payload["evidence_source"])
                return payload
            else:
                return {
                    "country_code": country_code,
                    "language_code": language_code,
                    "category": "general",
                    "keyword": keyword,
                    "search_intent": "informational",
                    "search_volume_monthly": None,
                    "trend_velocity_pct": None,
                    "competition_density": None,
                    "cpc_value_usd": None,
                    "seo_difficulty_score": None,
                    "evidence_source": f"HTTP_{res.status_code}",
                    "evidence_freshness": "DATA_UNAVAILABLE",
                    "confidence_score": 0.0,
                    "provider": "SERPAPI_PROVIDER",
                    "provider_status": "DATA_UNAVAILABLE",
                    "data_status": "DATA_UNAVAILABLE",
                    "source_type": "EXTERNAL_DATA_UNAVAILABLE"
                }
        except Exception as e:
            return {
                "country_code": country_code,
                "language_code": language_code,
                "category": "general",
                "keyword": keyword,
                "search_intent": "informational",
                "search_volume_monthly": None,
                "trend_velocity_pct": None,
                "competition_density": None,
                "cpc_value_usd": None,
                "seo_difficulty_score": None,
                "evidence_source": f"EXCEPTION: {str(e)[:60]}",
                "evidence_freshness": "DATA_UNAVAILABLE",
                "confidence_score": 0.0,
                "provider": "SERPAPI_PROVIDER",
                "provider_status": "DATA_UNAVAILABLE",
                "data_status": "DATA_UNAVAILABLE",
                "source_type": "EXTERNAL_DATA_UNAVAILABLE"
            }

class KeywordsEverywhereProvider(BaseMarketDataProvider):
    def __init__(self):
        self.api_key = os.getenv("KEYWORDS_EVERYWHERE_API_KEY", "").strip()

    def get_status(self) -> Dict[str, Any]:
        is_auth = bool(self.api_key)
        return {
            "provider": "KEYWORDS_EVERYWHERE_PROVIDER",
            "status": "CONFIGURED" if is_auth else "CONNECTOR_REQUIRED",
            "confidence_score": 95.0 if is_auth else 0.0,
            "data_status": "LIVE_EXTERNAL" if is_auth else "DATA_UNAVAILABLE",
            "auth_configured": is_auth
        }

    def fetch_market_signals(self, keyword: str, country_code: str = "US", language_code: str = "en") -> Dict[str, Any]:
        cached = MarketSignalCache.get("KEYWORDS_EVERYWHERE", keyword, country_code, language_code, "METRICS")
        if cached:
            return cached

        if not self.api_key:
            return {
                "country_code": country_code,
                "language_code": language_code,
                "category": "general",
                "keyword": keyword,
                "search_intent": "informational",
                "search_volume_monthly": None,
                "trend_velocity_pct": None,
                "competition_density": None,
                "cpc_value_usd": None,
                "seo_difficulty_score": None,
                "evidence_source": "NONE",
                "evidence_freshness": "DATA_UNAVAILABLE",
                "confidence_score": 0.0,
                "provider": "KEYWORDS_EVERYWHERE_PROVIDER",
                "provider_status": "CONNECTOR_REQUIRED",
                "data_status": "DATA_UNAVAILABLE",
                "source_type": "EXTERNAL_DATA_UNAVAILABLE"
            }

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json"
            }
            data_payload = {
                "country": country_code.lower(),
                "currency": "usd",
                "dataSource": "gkp",
                "kw[]": [keyword]
            }
            res = requests.post("https://api.keywordseverywhere.com/v1/get_keyword_data", headers=headers, data=data_payload, timeout=10)
            if res.status_code == 200:
                res_data = res.json()
                items = res_data.get("data", [])
                item = items[0] if items else {}
                
                payload = {
                    "country_code": country_code,
                    "language_code": language_code,
                    "category": "general",
                    "keyword": keyword,
                    "search_intent": "commercial" if item.get("cpc", {}).get("value", 0) > 1.0 else "informational",
                    "search_volume_monthly": item.get("vol"),
                    "trend_velocity_pct": None,
                    "competition_density": item.get("competition"),
                    "cpc_value_usd": item.get("cpc", {}).get("value") if isinstance(item.get("cpc"), dict) else item.get("cpc"),
                    "seo_difficulty_score": None,
                    "evidence_source": f"Keywords Everywhere API (Vol: {item.get('vol')}, CPC: {item.get('cpc')})",
                    "evidence_freshness": "30_DAYS_ROLLING",
                    "confidence_score": 95.0,
                    "provider": "KEYWORDS_EVERYWHERE_PROVIDER",
                    "provider_status": "CONFIGURED",
                    "data_status": "LIVE_EXTERNAL",
                    "source_type": "LIVE_EXTERNAL_SIGNAL"
                }
                MarketSignalCache.set("KEYWORDS_EVERYWHERE", keyword, country_code, language_code, "METRICS", payload, payload["evidence_source"])
                return payload
            else:
                return {
                    "country_code": country_code,
                    "language_code": language_code,
                    "category": "general",
                    "keyword": keyword,
                    "search_intent": "informational",
                    "search_volume_monthly": None,
                    "trend_velocity_pct": None,
                    "competition_density": None,
                    "cpc_value_usd": None,
                    "seo_difficulty_score": None,
                    "evidence_source": f"HTTP_{res.status_code}",
                    "evidence_freshness": "DATA_UNAVAILABLE",
                    "confidence_score": 0.0,
                    "provider": "KEYWORDS_EVERYWHERE_PROVIDER",
                    "provider_status": "DATA_UNAVAILABLE",
                    "data_status": "DATA_UNAVAILABLE",
                    "source_type": "EXTERNAL_DATA_UNAVAILABLE"
                }
        except Exception as e:
            return {
                "country_code": country_code,
                "language_code": language_code,
                "category": "general",
                "keyword": keyword,
                "search_intent": "informational",
                "search_volume_monthly": None,
                "trend_velocity_pct": None,
                "competition_density": None,
                "cpc_value_usd": None,
                "seo_difficulty_score": None,
                "evidence_source": f"EXCEPTION: {str(e)[:60]}",
                "evidence_freshness": "DATA_UNAVAILABLE",
                "confidence_score": 0.0,
                "provider": "KEYWORDS_EVERYWHERE_PROVIDER",
                "provider_status": "DATA_UNAVAILABLE",
                "data_status": "DATA_UNAVAILABLE",
                "source_type": "EXTERNAL_DATA_UNAVAILABLE"
            }

class ProviderRegistry:
    def __init__(self):
        self.serpapi = SerpApiProvider()
        self.ke = KeywordsEverywhereProvider()
        self.zero_state = ZeroStateProvider()

    def get_active_provider(self) -> BaseMarketDataProvider:
        if self.serpapi.get_status()["auth_configured"]:
            return self.serpapi
        if self.ke.get_status()["auth_configured"]:
            return self.ke
        return self.zero_state

    def fetch_unified_signals(self, keyword: str, country_code: str = "US", language_code: str = "en") -> Dict[str, Any]:
        serp_data = self.serpapi.fetch_market_signals(keyword, country_code, language_code)
        ke_data = self.ke.fetch_market_signals(keyword, country_code, language_code)
        
        # Zero-state fallback
        if serp_data["source_type"] == "EXTERNAL_DATA_UNAVAILABLE" and ke_data["source_type"] == "EXTERNAL_DATA_UNAVAILABLE":
            return self.zero_state.fetch_market_signals(keyword, country_code, language_code)

        # Merge actual returned data without fabrication
        unified = {
            "country_code": country_code,
            "language_code": language_code,
            "category": "general",
            "keyword": keyword,
            "search_intent": ke_data.get("search_intent") or serp_data.get("search_intent") or "informational",
            "search_volume_monthly": ke_data.get("search_volume_monthly"),
            "trend_velocity_pct": None,
            "competition_density": ke_data.get("competition_density"),
            "cpc_value_usd": ke_data.get("cpc_value_usd"),
            "seo_difficulty_score": None,
            "evidence_source": f"Merged [SerpApi: {serp_data['evidence_source']} | KE: {ke_data['evidence_source']}]",
            "evidence_freshness": "REALTIME_LIVE" if serp_data.get("evidence_freshness") == "REALTIME_LIVE" else "30_DAYS_ROLLING",
            "confidence_score": max(serp_data.get("confidence_score", 0.0), ke_data.get("confidence_score", 0.0)),
            "provider": "UNIFIED_MULTI_PROVIDER",
            "provider_status": "CONFIGURED",
            "data_status": "LIVE_EXTERNAL",
            "source_type": "LIVE_EXTERNAL_SIGNAL"
        }
        return unified

registry = ProviderRegistry()