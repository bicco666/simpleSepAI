from __future__ import annotations
from pathlib import Path
from typing import Any, Mapping
import os, re

try:
    import yaml
except Exception:
    yaml = None

def _default_path() -> Path:
    env_path = os.getenv("RESEARCH_CONFIG", "").strip()
    if env_path:
        return Path(env_path)
    return Path(__file__).resolve().parents[1] / "Config" / "research.yaml"

_env_pattern = re.compile(r"\$\{([A-Z0-9_]+)\}")

def _expand_env_value(value: Any) -> Any:
    if isinstance(value, str):
        def repl(m):
            var = m.group(1)
            return os.getenv(var, f"${{{var}}}")
        return _env_pattern.sub(repl, value)
    if isinstance(value, list):
        return [_expand_env_value(v) for v in value]
    if isinstance(value, dict):
        return {k: _expand_env_value(v) for k, v in value.items()}
    return value

def load_config(path: Path | None = None) -> Mapping[str, Any]:
    path = Path(path) if path else _default_path()
    if yaml is None or not path.exists():
        return {
            "providers": {"openai": {"enabled": True, "model": "gpt-5.1-mini", "temperature": 0.2, "max_output_tokens": 600, "timeout_seconds": 12},
                          "twitter": {"enabled": False}},
            "investment_profile": {"objective":"fallback","horizon_minutes":90,"max_positions":1,
                                   "risk":3,"budget_sol":0.1,"constraints":"Spot only",
                                   "include_keywords":["SOL"],"exclude_keywords":[]},
            "research_policy": {"universe":["SOL"],"constraints":"Spot only","risk_bounds":[1,5],
                                "ttl_minutes_default":90,"stop_loss_pct":1.5,"take_profit_pct":2.0},
            "routing": {"prefer_openai": True, "use_twitter_signals": False},
            "logging": {"level":"INFO","write_idea_reports":True,"report_dir":"Report"},
            "env": {}
        }
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return _expand_env_value(data)