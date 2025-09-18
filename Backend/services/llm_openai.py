from __future__ import annotations
from typing import Any, Mapping, Optional, Tuple
import os, json, datetime, time

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

def call_openai_generate(req: Mapping[str, Any], cfg: Mapping[str, Any]) -> Tuple[Optional[Mapping[str, Any]], Optional[str]]:
    prov = (cfg.get("providers") or {}).get("openai") or {}
    if not prov.get("enabled", False):
        return None, "OpenAI provider disabled"
    if OpenAI is None:
        return None, "openai package not available"

    # Get API key from config or environment
    api_key = prov.get("api_key") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None, "Missing OpenAI API key"

    timeout_seconds = int(prov.get("timeout_seconds", 30))
    client = OpenAI(api_key=api_key, timeout=timeout_seconds)

    model = prov.get("model", "gpt-4o-mini")
    temperature = float(prov.get("temperature", 0.2))
    max_tokens = int(prov.get("max_output_tokens", 600))

    profile = cfg.get("investment_profile", {})
    payload = {"request": req, "profile": profile, "policy": cfg.get("research_policy", {})}

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}
    ]

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        text = resp.choices[0].message.content
    except Exception as e:
        err = f"OpenAI API Error: {e}"
        print(err)
        return None, err

    try:
        data = json.loads(text)
    except Exception as e:
        err = f"JSON Parse Error: {e}, Raw response: {text}"
        print(err)
        return None, err

    data.setdefault("idea_id", datetime.datetime.utcnow().strftime("IDEA%Y%m%d%H%M%S"))
    data.setdefault("asset", "SOL")
    data.setdefault("thesis", "No thesis")
    data.setdefault("entry_rule", "Market BUY")
    data.setdefault("exit_rule", "Zeit-Exit 60min")
    data.setdefault("ttl_minutes", int((cfg.get("research_policy") or {}).get("ttl_minutes_default", 90)))
    return data, None

def call_openai_generate_with_meta(req: Mapping[str, Any], cfg: Mapping[str, Any]) -> Tuple[Optional[Mapping[str, Any]], str, Optional[str], int]:
    """
    Enhanced OpenAI call with retry/backoff and metadata.
    Returns: (data, source, error, retries_used)
    """
    prov = (cfg.get("providers") or {}).get("openai") or {}
    retries = int(prov.get("retries", 1))
    backoff_ms = int(prov.get("backoff_ms", 500))
    enable_fallback = prov.get("enable_fallback_on_error", True)

    # Try OpenAI with retries
    for attempt in range(retries + 1):
        data, error = call_openai_generate(req, cfg)

        if data is not None:
            return data, "openai", None, attempt

        # Check if it's a quota/429 error that we should retry
        if error and ("429" in error or "insufficient_quota" in error or "quota" in error.lower()):
            if attempt < retries:
                print(f"OpenAI quota error, retrying in {backoff_ms}ms (attempt {attempt + 1}/{retries + 1})")
                time.sleep(backoff_ms / 1000.0)
                continue
            else:
                print(f"OpenAI quota error after {retries + 1} attempts, falling back")
                break
        else:
            # Non-quota error, don't retry
            break

    # If we get here, OpenAI failed and we should use fallback
    if enable_fallback:
        return None, "fallback", error, retries
    else:
        return None, "error", error, retries
