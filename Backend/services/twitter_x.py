from __future__ import annotations
from typing import Any, Mapping, List, Dict, Tuple
import datetime
try:
    import requests
except Exception:
    requests = None  # type: ignore

def recent_search(cfg: Mapping[str, Any]) -> Tuple[List[Dict[str, Any]], str]:
    """Return tweets and error message if any."""
    prov = (cfg.get("providers") or {}).get("twitter") or {}
    if not prov.get("enabled", False):
        return [], "Twitter provider is not enabled"
    token = cfg.get("env", {}).get("X_BEARER_TOKEN")
    if not token:
        return [], "Twitter bearer token not found in environment variables"
    if requests is None:
        return [], "Requests library not available"
    base = prov.get("base_url", "https://api.twitter.com/2").rstrip("/")
    ep = prov.get("recent_search_endpoint", "/tweets/search/recent")
    url = base + ep
    params = {
        "query": prov.get("query", "(SOL OR Solana) (DEX OR DeFi) -is:retweet lang:en"),
        "max_results": min(int(prov.get("max_results", 25)), 100)
    }
    # Add start_time if lookback_minutes is specified
    lookback_minutes = prov.get("lookback_minutes")
    if lookback_minutes:
        start_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=lookback_minutes)
        params["start_time"] = start_time.isoformat() + "Z"
    try:
        r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, params=params, timeout=10)
        if r.status_code != 200:
            try:
                error_data = r.json()
                error_msg = error_data.get("title", f"HTTP {r.status_code}")
            except:
                error_msg = f"HTTP {r.status_code}: {r.text[:100]}"
            return [], f"Twitter API error: {error_msg}"
        data = r.json()
        tweets = [{"id": t.get("id"), "text": t.get("text"), "created_at": t.get("created_at")} for t in data.get("data", [])]
        return tweets, ""
    except Exception as e:
        return [], f"Request failed: {str(e)}"