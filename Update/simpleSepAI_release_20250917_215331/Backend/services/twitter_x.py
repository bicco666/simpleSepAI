from __future__ import annotations
from typing import Any, Mapping, List, Dict
import os
try:
    import requests
except Exception:
    requests = None  # type: ignore

def recent_search(cfg: Mapping[str, Any]) -> List[Dict[str, Any]]:
    prov = (cfg.get("providers") or {}).get("twitter") or {}
    if not prov.get("enabled", False):
        return []
    token = os.getenv("X_BEARER_TOKEN") or os.getenv("TWITTER_BEARER_TOKEN")
    if not token or requests is None:
        return []
    base = prov.get("base_url", "https://api.twitter.com/2").rstrip("/")
    ep = prov.get("recent_search_endpoint", "/tweets/search/recent")
    url = base + ep
    params = {"query": prov.get("query", "(SOL OR Solana) (DEX OR DeFi) -is:retweet lang:en"),
              "max_results": min(int(prov.get("max_results", 25)), 100)}
    try:
        r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, params=params, timeout=10)
        if r.status_code != 200:
            return []
        data = r.json()
        return [{"id":t.get("id"),"text":t.get("text"),"created_at":t.get("created_at")} for t in data.get("data", [])]
    except Exception:
        return []