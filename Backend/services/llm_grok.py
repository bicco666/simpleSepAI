from __future__ import annotations
from typing import Any, Mapping, Optional, Tuple
import os, json, datetime, time

try:
    import requests
except Exception:
    requests = None  # type: ignore

SYSTEM_PROMPT = (
    "Du bist der Research-Agent einer Solana-Trading-Org. Antworte ausschließlich als VALIDES JSON "
    "gemäß dem Schema: {idea_id, asset, thesis, entry_rule, exit_rule, risk, budget_sol, ttl_minutes, expected_catalyst}. "
    "Rahmenbedingungen: nur Solana-Ökosystem (Spot/DEX), keine Derivate, keine Leverage. "
    "Gib keine Prosa außerhalb des JSON zurück."
)

def call_grok_generate(req: Mapping[str, Any], cfg: Mapping[str, Any]) -> Tuple[Optional[Mapping[str, Any]], Optional[str]]:
    prov = (cfg.get("providers") or {}).get("grok") or {}
    if not prov.get("enabled", False):
        return None, "Grok provider disabled"
    if requests is None:
        return None, "requests package not available"

    # Get API key from config or environment
    api_key = prov.get("api_key") or os.getenv("XAI_API_KEY")
    if not api_key:
        return None, "Missing xAI API key"

    base_url = prov.get("base_url", "https://api.x.ai")
    model = prov.get("model", "grok-beta")
    temperature = float(prov.get("temperature", 0.2))
    max_tokens = int(prov.get("max_output_tokens", 600))
    timeout_seconds = int(prov.get("timeout_seconds", 30))

    profile = cfg.get("investment_profile", {})
    payload = {"request": req, "profile": profile, "policy": cfg.get("research_policy", {})}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # xAI Grok API Format - korrigierter Endpoint
    data = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}
        ],
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False
    }

    try:
        # Try different possible endpoints and models for xAI Grok
        models_to_try = ["grok-3", "grok-4", "grok-3-mini", "grok-code-fast-1", "grok-beta"]
        endpoints_to_try = []

        # Generate all combinations of endpoints and models
        base_endpoints = [
            f"{base_url}/v1/chat/completions",
            f"{base_url}/chat/completions",
            f"{base_url}/api/chat/completions",
            "https://api.x.ai/v1/chat/completions",
            "https://api.x.ai/chat/completions"
        ]

        for endpoint in base_endpoints:
            for model in models_to_try:
                endpoints_to_try.append((endpoint, model))

        response = None
        for endpoint, model_name in endpoints_to_try:
            try:
                # Update the data with the current model
                current_data = data.copy()
                current_data["model"] = model_name

                response = requests.post(
                    endpoint,
                    headers=headers,
                    json=current_data,
                    timeout=timeout_seconds
                )
                response.raise_for_status()
                print(f"Grok API success with endpoint: {endpoint} and model: {model_name}")
                break  # Success, stop trying other combinations
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    continue  # Try next combination
                else:
                    print(f"Grok API error with {endpoint} and {model_name}: {e}")
                    continue  # Try next combination
            except Exception as e:
                print(f"Grok API connection error with {endpoint} and {model_name}: {e}")
                continue  # Try next combination

        if response is None:
            raise Exception("All xAI Grok endpoints returned 404")
        response.raise_for_status()

        result = response.json()
        # Handle different possible response formats
        if "choices" in result and result["choices"]:
            text = result["choices"][0]["message"]["content"]
        elif "content" in result:
            text = result["content"]
        elif "response" in result:
            text = result["response"]
        else:
            text = str(result)

    except Exception as e:
        err = f"Grok API Error: {e}"
        print(err)
        return None, err

    try:
        data = json.loads(text)
    except Exception as e:
        err = f"Grok JSON Parse Error: {e}, Raw response: {text}"
        print(err)
        return None, err

    data.setdefault("idea_id", datetime.datetime.utcnow().strftime("GROK%Y%m%d%H%M%S"))
    data.setdefault("asset", "SOL")
    data.setdefault("thesis", "No thesis")
    data.setdefault("entry_rule", "Market BUY")
    data.setdefault("exit_rule", "Zeit-Exit 60min")
    data.setdefault("ttl_minutes", int((cfg.get("research_policy") or {}).get("ttl_minutes_default", 90)))
    return data, None

def call_grok_analyze(report_content: str, instructions: str, cfg: Mapping[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    prov = (cfg.get("providers") or {}).get("grok") or {}
    if not prov.get("enabled", False):
        return None, "Grok provider disabled"
    if requests is None:
        return None, "requests package not available"

    # Get API key from config or environment
    api_key = prov.get("api_key") or os.getenv("XAI_API_KEY")
    if not api_key:
        return None, "Missing xAI API key"

    base_url = prov.get("base_url", "https://api.x.ai")
    model = prov.get("model", "grok-beta")
    temperature = float(prov.get("temperature", 0.2))
    max_tokens = int(prov.get("max_output_tokens", 2000))
    timeout_seconds = int(prov.get("timeout_seconds", 30))

    system_prompt = (
        "You are a research analyst specializing in financial markets and trading. "
        "Analyze the provided research report and improve it based on the given instructions. "
        "Incorporate macro market analysis and trade detailing where relevant. "
        "Provide a comprehensive, improved version of the report with your analysis."
    )

    user_content = f"Report Content:\n{report_content}\n\nInstructions:\n{instructions}"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # xAI Grok API Format
    data = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False
    }

    try:
        # Try different possible endpoints and models for xAI Grok
        models_to_try = ["grok-3", "grok-4", "grok-3-mini", "grok-code-fast-1", "grok-beta"]
        endpoints_to_try = []

        # Generate all combinations of endpoints and models
        base_endpoints = [
            f"{base_url}/v1/chat/completions",
            f"{base_url}/chat/completions",
            f"{base_url}/api/chat/completions",
            "https://api.x.ai/v1/chat/completions",
            "https://api.x.ai/chat/completions"
        ]

        for endpoint in base_endpoints:
            for model in models_to_try:
                endpoints_to_try.append((endpoint, model))

        response = None
        for endpoint, model_name in endpoints_to_try:
            try:
                # Update the data with the current model
                current_data = data.copy()
                current_data["model"] = model_name

                response = requests.post(
                    endpoint,
                    headers=headers,
                    json=current_data,
                    timeout=timeout_seconds
                )
                response.raise_for_status()
                print(f"Grok API success with endpoint: {endpoint} and model: {model_name}")
                break  # Success, stop trying other combinations
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    continue  # Try next combination
                else:
                    print(f"Grok API error with {endpoint} and {model_name}: {e}")
                    continue  # Try next combination
            except Exception as e:
                print(f"Grok API connection error with {endpoint} and {model_name}: {e}")
                continue  # Try next combination

        if response is None:
            raise Exception("All xAI Grok endpoints returned 404")
        response.raise_for_status()

        result = response.json()
        # Handle different possible response formats
        if "choices" in result and result["choices"]:
            text = result["choices"][0]["message"]["content"]
        elif "content" in result:
            text = result["content"]
        elif "response" in result:
            text = result["response"]
        else:
            text = str(result)

        return text, None
    except Exception as e:
        err = f"Grok API Error: {e}"
        print(err)
        return None, err

def call_grok_generate_with_meta(req: Mapping[str, Any], cfg: Mapping[str, Any]) -> Tuple[Optional[Mapping[str, Any]], str, Optional[str], int]:
    """
    Enhanced Grok call with retry/backoff and metadata.
    Returns: (data, source, error, retries_used)
    """
    prov = (cfg.get("providers") or {}).get("grok") or {}
    retries = int(prov.get("retries", 1))
    backoff_ms = int(prov.get("backoff_ms", 500))
    enable_fallback = prov.get("enable_fallback_on_error", True)

    # Try Grok with retries
    for attempt in range(retries + 1):
        data, error = call_grok_generate(req, cfg)

        if data is not None:
            return data, "grok", None, attempt

        # Check if it's a rate limit or quota error
        if error and ("429" in error or "rate" in error.lower() or "quota" in error.lower()):
            if attempt < retries:
                print(f"Grok rate limit error, retrying in {backoff_ms}ms (attempt {attempt + 1}/{retries + 1})")
                time.sleep(backoff_ms / 1000.0)
                continue
            else:
                print(f"Grok rate limit error after {retries + 1} attempts, falling back")
                break
        else:
            # Non-rate-limit error, don't retry
            break

    # If we get here, Grok failed and we should use fallback
    if enable_fallback:
        return None, "fallback", error, retries
    else:
        return None, "error", error, retries