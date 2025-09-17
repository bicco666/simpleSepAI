from __future__ import annotations
from typing import Any, Mapping, Optional
import os, json, datetime

try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # type: ignore

SYSTEM_PROMPT = (
    "Du bist der Research-Agent einer Solana-Trading-Org. Antworte ausschließlich als VALIDES JSON "
    "gemäß dem Schema: {idea_id, asset, thesis, entry_rule, exit_rule, risk, budget_sol, ttl_minutes, expected_catalyst}. "
    "Rahmenbedingungen: nur Solana-Ökosystem (Spot/DEX), keine Derivate, keine Leverage. "
    "Gib keine Prosa außerhalb des JSON zurück."
)

def call_openai_generate(req: Mapping[str, Any], cfg: Mapping[str, Any]) -> Optional[Mapping[str, Any]]:
    prov = (cfg.get("providers") or {}).get("openai") or {}
    if not prov.get("enabled", False):
        return None
    if OpenAI is None or not os.getenv("OPENAI_API_KEY"):
        return None

    client = OpenAI()
    model = prov.get("model", "gpt-5.1-mini")
    temperature = float(prov.get("temperature", 0.2))
    max_output_tokens = int(prov.get("max_output_tokens", 600))

    user_prompt = json.dumps(req, ensure_ascii=False)
    resp = client.responses.create(
        model=model,
        input=(SYSTEM_PROMPT + "\nUser:\n" + user_prompt),
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )

    text = getattr(resp, "output_text", None) or str(resp)
    try:
        data = json.loads(text)
    except Exception:
        return None

    data.setdefault("idea_id", datetime.datetime.utcnow().strftime("IDEA%Y%m%d%H%M%S"))
    data.setdefault("asset", "SOL")
    data.setdefault("thesis", "No thesis")
    data.setdefault("entry_rule", "Market BUY")
    data.setdefault("exit_rule", "Zeit-Exit 60min")
    data.setdefault("ttl_minutes", int((cfg.get("research_policy") or {}).get("ttl_minutes_default", 90)))
    return data