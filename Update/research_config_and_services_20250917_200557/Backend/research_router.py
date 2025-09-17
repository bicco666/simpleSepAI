from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Mapping, Any
import datetime
from .config_loader import load_config
from .services.llm_openai import call_openai_generate
from .services.twitter_x import recent_search

router = APIRouter(prefix="/api/research", tags=["research"])

class IdeaRequest(BaseModel):
    risk: int = Field(..., ge=1, le=5)
    budget_sol: float = Field(..., gt=0)
    universe: Optional[List[str]] = None
    constraints: Optional[str] = None

class IdeaPayload(BaseModel):
    idea_id: str
    asset: str
    thesis: str
    entry_rule: str
    exit_rule: str
    risk: int
    budget_sol: float
    ttl_minutes: int
    expected_catalyst: Optional[str] = None

class IdeaResponse(BaseModel):
    ok: bool
    source: Literal["openai","fallback"] = "openai"
    ts: str
    payload: IdeaPayload
    twitter_signals: Optional[list] = None

def _fallback_from_file(budget_sol: float, risk: int) -> Mapping[str, Any]:
    try:
        from pathlib import Path
        txt = Path(__file__).resolve().parent / "idee.txt"
        content = txt.read_text(encoding="utf-8").strip()
    except Exception:
        content = "Kaufe 0,1 SOL innerhalb der nächsten 10 Minuten; Zeit-Exit 60 Minuten."
    idea = {
        "idea_id": datetime.datetime.utcnow().strftime("IDEA%Y%m%d%H%M%S"),
        "asset": "SOL",
        "thesis": content,
        "entry_rule": "Market BUY, Size abhängig von budget_sol",
        "exit_rule": "Zeit-Exit 60min oder +2% Profit; Stop -1.5%",
        "risk": risk,
        "budget_sol": budget_sol,
        "ttl_minutes": 90,
        "expected_catalyst": "Fallback/Manuell",
    }
    return idea

@router.post("/idea", response_model=IdeaResponse)
def generate_idea(req: IdeaRequest):
    cfg = load_config()
    tw_signals = []
    if (cfg.get("routing", {}).get("use_twitter_signals", False)):
        tw_signals = recent_search(cfg) or []

    idea_data = None
    if cfg.get("routing", {}).get("prefer_openai", True):
        idea_data = call_openai_generate({
            "risk": req.risk,
            "budget_sol": req.budget_sol,
            "universe": req.universe or (cfg.get("research_policy", {}).get("universe") or ["SOL"]),
            "constraints": req.constraints or (cfg.get("research_policy", {}).get("constraints") or "Spot only"),
        }, cfg)

    source = "openai"
    if not idea_data:
        idea_data = _fallback_from_file(req.budget_sol, req.risk)
        source = "fallback"

    payload = IdeaPayload(**idea_data)
    return IdeaResponse(
        ok=True,
        source=source,
        ts=datetime.datetime.utcnow().isoformat(),
        payload=payload,
        twitter_signals=tw_signals or None
    )