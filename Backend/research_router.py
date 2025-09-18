from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional, List, Mapping, Any
import datetime, time
from pathlib import Path
from .config_loader import load_config
from .services.llm_openai import call_openai_generate_with_meta, call_openai_analyze
from .services.llm_grok import call_grok_generate_with_meta, call_grok_analyze
from .services.twitter_x import recent_search

router = APIRouter(prefix="/api/research", tags=["research"])

class IdeaRequest(BaseModel):
    risk: int = Field(..., ge=1, le=5)
    budget_sol: float = Field(..., gt=0)
    universe: Optional[List[str]] = None
    constraints: Optional[str] = None
    provider: Optional[str] = Field("auto", description="LLM provider: 'openai', 'grok', or 'auto'")

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
    source: str = "openai"
    ts: str
    payload: IdeaPayload
    twitter_signals: Optional[list] = None
    error: Optional[str] = None
    retries: Optional[int] = None
    duration_ms: Optional[float] = None

class ReportInfo(BaseModel):
    filename: str
    timestamp: str
    preview: str

class AnalyzeReportRequest(BaseModel):
    filename: str
    instructions: str = Field(..., description="Analysis instructions")
    provider: Optional[str] = Field("auto", description="LLM provider: 'openai', 'grok', or 'auto'")

class AnalyzeReportResponse(BaseModel):
    ok: bool
    source: str = "openai"
    ts: str
    analysis_result: str
    saved_filename: Optional[str] = None
    error: Optional[str] = None
    retries: Optional[int] = None
    duration_ms: Optional[float] = None

def _fallback_from_file(budget_sol: float, risk: int) -> Mapping[str, Any]:
    try:
        txt = Path(__file__).resolve().parent / "idee.txt"
        content = txt.read_text(encoding="utf-8").strip()
    except Exception:
        content = "Kaufe 0,1 SOL innerhalb der nächsten 10 Minuten; Zeit-Exit 60 Minuten."
    idea = {"idea_id": datetime.datetime.utcnow().strftime("IDEA%Y%m%d%H%M%S"),
            "asset":"SOL","thesis":content,"entry_rule":"Market BUY, Size abhängig von budget_sol",
            "exit_rule":"Zeit-Exit 60min oder +2% Profit; Stop -1.5%","risk":risk,"budget_sol":budget_sol,
            "ttl_minutes":90,"expected_catalyst":"Fallback/Manuell"}
    return idea

def _generate_idea_with_provider(req: IdeaRequest, cfg: Mapping[str, Any]) -> Tuple[Optional[Mapping[str, Any]], str, Optional[str], int]:
    """Generate idea using specified provider with fallback logic."""
    provider = req.provider or "auto"

    # Determine which provider to use
    if provider == "grok":
        # Try Grok first
        data, source, error, retries = call_grok_generate_with_meta(
            {"risk": req.risk, "budget_sol": req.budget_sol,
             "universe": req.universe or (cfg.get("research_policy", {}).get("universe") or ["SOL"]),
             "constraints": req.constraints or (cfg.get("research_policy", {}).get("constraints") or "Spot only")},
            cfg
        )
        if data:
            return data, source, error, retries

        # If Grok fails and fallback is enabled, try OpenAI
        if source == "fallback" and (cfg.get("providers", {}).get("openai", {}).get("enabled", False)):
            print("Grok failed, trying OpenAI as fallback...")
            data, source, error, retries = call_openai_generate_with_meta(
                {"risk": req.risk, "budget_sol": req.budget_sol,
                 "universe": req.universe or (cfg.get("research_policy", {}).get("universe") or ["SOL"]),
                 "constraints": req.constraints or (cfg.get("research_policy", {}).get("constraints") or "Spot only")},
                cfg
            )
            if data:
                return data, f"openai-{source}", error, retries

    elif provider == "openai":
        # Try OpenAI first
        data, source, error, retries = call_openai_generate_with_meta(
            {"risk": req.risk, "budget_sol": req.budget_sol,
             "universe": req.universe or (cfg.get("research_policy", {}).get("universe") or ["SOL"]),
             "constraints": req.constraints or (cfg.get("research_policy", {}).get("constraints") or "Spot only")},
            cfg
        )
        if data:
            return data, source, error, retries

        # If OpenAI fails and fallback is enabled, try Grok
        if source == "fallback" and (cfg.get("providers", {}).get("grok", {}).get("enabled", False)):
            print("OpenAI failed, trying Grok as fallback...")
            data, source, error, retries = call_grok_generate_with_meta(
                {"risk": req.risk, "budget_sol": req.budget_sol,
                 "universe": req.universe or (cfg.get("research_policy", {}).get("universe") or ["SOL"]),
                 "constraints": req.constraints or (cfg.get("research_policy", {}).get("constraints") or "Spot only")},
                cfg
            )
            if data:
                return data, f"grok-{source}", error, retries

    else:  # provider == "auto" - try both in order
        # Try OpenAI first (default)
        if cfg.get("providers", {}).get("openai", {}).get("enabled", False):
            data, source, error, retries = call_openai_generate_with_meta(
                {"risk": req.risk, "budget_sol": req.budget_sol,
                 "universe": req.universe or (cfg.get("research_policy", {}).get("universe") or ["SOL"]),
                 "constraints": req.constraints or (cfg.get("research_policy", {}).get("constraints") or "Spot only")},
                cfg
            )
            if data:
                return data, source, error, retries

        # Try Grok as fallback
        if cfg.get("providers", {}).get("grok", {}).get("enabled", False):
            data, source, error, retries = call_grok_generate_with_meta(
                {"risk": req.risk, "budget_sol": req.budget_sol,
                 "universe": req.universe or (cfg.get("research_policy", {}).get("universe") or ["SOL"]),
                 "constraints": req.constraints or (cfg.get("research_policy", {}).get("constraints") or "Spot only")},
                cfg
            )
            if data:
                return data, source, error, retries

    # If we get here, both providers failed - this should not happen due to fallback logic
    # But if it does, we'll handle it in the main function
    return None, "error", "All providers failed", 0

def _analyze_report_with_provider(report_content: str, instructions: str, req: AnalyzeReportRequest, cfg: Mapping[str, Any]) -> Tuple[Optional[str], str, Optional[str], int]:
    """Analyze report using specified provider with fallback logic."""
    provider = req.provider or "auto"

    # Determine which provider to use
    if provider == "grok":
        # Try Grok first
        analysis, error = call_grok_analyze(report_content, instructions, cfg)
        if analysis:
            return analysis, "grok", None, 0

        # If Grok fails and fallback is enabled, try OpenAI
        if cfg.get("providers", {}).get("openai", {}).get("enabled", False):
            print("Grok failed, trying OpenAI as fallback...")
            analysis, error = call_openai_analyze(report_content, instructions, cfg)
            if analysis:
                return analysis, "openai-fallback", None, 0

    elif provider == "openai":
        # Try OpenAI first
        analysis, error = call_openai_analyze(report_content, instructions, cfg)
        if analysis:
            return analysis, "openai", None, 0

        # If OpenAI fails and fallback is enabled, try Grok
        if cfg.get("providers", {}).get("grok", {}).get("enabled", False):
            print("OpenAI failed, trying Grok as fallback...")
            analysis, error = call_grok_analyze(report_content, instructions, cfg)
            if analysis:
                return analysis, "grok-fallback", None, 0

    else:  # provider == "auto" - try both in order
        # Try OpenAI first (default)
        if cfg.get("providers", {}).get("openai", {}).get("enabled", False):
            analysis, error = call_openai_analyze(report_content, instructions, cfg)
            if analysis:
                return analysis, "openai", None, 0

        # Try Grok as fallback
        if cfg.get("providers", {}).get("grok", {}).get("enabled", False):
            analysis, error = call_grok_analyze(report_content, instructions, cfg)
            if analysis:
                return analysis, "grok", None, 0

    # If we get here, both providers failed
    return None, "error", "All providers failed", 0

@router.get("/health")
def health():
    cfg = load_config()
    return {"ok": True,
            "providers":{"openai_enabled":bool((cfg.get("providers") or {}).get("openai",{}).get("enabled",False)),
                          "grok_enabled":bool((cfg.get("providers") or {}).get("grok",{}).get("enabled",False)),
                          "twitter_enabled":bool((cfg.get("providers") or {}).get("twitter",{}).get("enabled",False))},
            "timeout_s": int((cfg.get("providers") or {}).get("openai",{}).get("timeout_seconds",12))}

@router.get("/test/grok")
def test_grok():
    """Simple test endpoint for Grok API connectivity."""
    cfg = load_config()
    from Backend.services.llm_grok import call_grok_generate

    # Simple test payload
    test_req = {"test": "Hello Grok", "message": "Respond with a simple greeting"}
    test_cfg = {"providers": cfg.get("providers", {}), "research_policy": cfg.get("research_policy", {})}

    try:
        result, error = call_grok_generate(test_req, test_cfg)
        if result:
            return {"ok": True, "status": "success", "response": result, "source": "grok"}
        else:
            return {"ok": False, "status": "error", "error": error, "source": "grok"}
    except Exception as e:
        return {"ok": False, "status": "exception", "error": str(e), "source": "grok"}

@router.get("/reports", response_model=List[ReportInfo])
def get_reports():
    """Get list of available research reports."""
    try:
        report_dir = Path(__file__).resolve().parent.parent / "Report"
        if not report_dir.exists():
            return []

        reports = []
        for file_path in report_dir.iterdir():
            if file_path.is_file() and file_path.name != ".gitkeep":
                try:
                    stat = file_path.stat()
                    timestamp = datetime.datetime.fromtimestamp(stat.st_mtime, tz=datetime.timezone.utc).isoformat()
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    preview = content[:200] + ("..." if len(content) > 200 else "")
                    reports.append(ReportInfo(
                        filename=file_path.name,
                        timestamp=timestamp,
                        preview=preview
                    ))
                except Exception as e:
                    print(f"Error reading file {file_path}: {e}")
                    continue

        # Sort by timestamp descending (newest first)
        reports.sort(key=lambda x: x.timestamp, reverse=True)
        return reports
    except Exception as e:
        print(f"Error listing reports: {e}")
        return []

@router.post("/analyze_report", response_model=AnalyzeReportResponse)
def analyze_report(req: AnalyzeReportRequest):
    cfg = load_config()
    start = time.perf_counter()

    try:
        # Read the report file
        report_path = Path(__file__).resolve().parent.parent / "Report" / req.filename
        if not report_path.exists() or not report_path.is_file():
            return AnalyzeReportResponse(
                ok=False,
                source="error",
                ts=datetime.datetime.utcnow().isoformat(),
                analysis_result="",
                error=f"Report file '{req.filename}' not found",
                retries=0,
                duration_ms=0.0
            )

        report_content = report_path.read_text(encoding="utf-8", errors="ignore")

        # Analyze with LLM
        analysis_result, source, error, retries = _analyze_report_with_provider(report_content, req.instructions, req, cfg)

        duration = (time.perf_counter() - start) * 1000.0

        if not analysis_result:
            return AnalyzeReportResponse(
                ok=False,
                source=source,
                ts=datetime.datetime.utcnow().isoformat(),
                analysis_result="",
                error=error,
                retries=retries,
                duration_ms=round(duration, 2)
            )

        # Save the analysis result to a new file
        log_cfg = cfg.get("logging", {})
        report_dir = Path(__file__).resolve().parent.parent / log_cfg.get("report_dir", "Report")
        report_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        saved_filename = f"analysis_{ts}.txt"
        (report_dir / saved_filename).write_text(analysis_result, encoding="utf-8")

        # Determine final source
        final_source = source
        if source == "openai-fallback":
            final_source = "openai"
        elif source == "grok-fallback":
            final_source = "grok"

        return AnalyzeReportResponse(
            ok=True,
            source=final_source,
            ts=datetime.datetime.utcnow().isoformat(),
            analysis_result=analysis_result,
            saved_filename=saved_filename,
            error=None,
            retries=retries,
            duration_ms=round(duration, 2)
        )

    except Exception as e:
        duration = (time.perf_counter() - start) * 1000.0
        print(f"Error analyzing report: {e}")
        return AnalyzeReportResponse(
            ok=False,
            source="error",
            ts=datetime.datetime.utcnow().isoformat(),
            analysis_result="",
            error=str(e),
            retries=0,
            duration_ms=round(duration, 2)
        )

@router.post("/idea", response_model=IdeaResponse)
def generate_idea(req: IdeaRequest):
    cfg = load_config()
    tw_signals = recent_search(cfg) if (cfg.get("routing",{}).get("use_twitter_signals",False)) else []
    start = time.perf_counter()

    # Use the provider-aware function
    idea_data, source, error, retries = _generate_idea_with_provider(req, cfg)

    duration = (time.perf_counter() - start) * 1000.0

    # If all providers failed, use static fallback
    if not idea_data:
        idea_data = _fallback_from_file(req.budget_sol, req.risk)

    payload = IdeaPayload(**idea_data)
    log_cfg = cfg.get("logging", {})
    if log_cfg.get("write_idea_reports", True):
        report_dir = Path(log_cfg.get("report_dir", "Report")); report_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        (report_dir / f"research_{ts}.txt").write_text(str(payload.model_dump()), encoding="utf-8")

    # Determine final source for response
    final_source = source
    if source.startswith("openai-"):
        final_source = "openai"
    elif source.startswith("grok-"):
        final_source = "grok"

    return {"ok": True, "source": final_source, "ts": datetime.datetime.utcnow().isoformat(),
            "payload": payload, "twitter_signals": tw_signals or None,
            "error": error, "retries": retries,
            "duration_ms": round(duration, 2)}
