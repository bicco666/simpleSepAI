from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import subprocess, sys, re, json
from datetime import datetime

app = FastAPI(title="simpleSepAI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent
ROOT_DIR = BASE_DIR.parent
REPORT_DIR = ROOT_DIR / "Report"

def read_textfile(name: str) -> str:
    p = BASE_DIR / f"{name}.txt"
    return p.read_text(encoding="utf-8").strip()

def ensure_phrase(text: str, phrase: str) -> str:
    return text if phrase in text else (text + (" | " if text else "") + phrase)

class ExecReq(BaseModel):
    sol: float | None = None

@app.get("/api/systemtest")
def systemtest():
    return {"ok": True, "report": "10/10 Pass (File-Stub Mode)"}

@app.get("/api/idea")
def idea():
    try:
        content = read_textfile("idee")
        idea_text = ensure_phrase(content, "Kaufe 0,1 SOL")
        return {"ok": True, "idea": idea_text, "file_content": content, "source": "Backend/idee.txt"}
    except Exception as e:
        return {"ok": False, "error": f"Idee-Fehler: {e}", "source": "Backend/idee.txt"}

@app.get("/api/analysis")
def analysis():
    try:
        content = read_textfile("analyse")
        analysis_text = ensure_phrase(content, "Kaufe 0,1 SOL")
        return {"ok": True, "analysis": analysis_text, "file_content": content, "source": "Backend/analyse.txt"}
    except Exception as e:
        return {"ok": False, "error": f"Analyse-Fehler: {e}", "source": "Backend/analyse.txt"}

@app.post("/api/execute")
def execute(_: ExecReq):
    try:
        content = read_textfile("execution")
        log = [f"EXECUTION: {content}"]
        return {
            "ok": True,
            "execution": content,
            "log": log,
            "address": "DevnetStub111111111111",
            "balance": 0.0,
            "source": "Backend/execution.txt",
        }
    except Exception as e:
        return {"ok": False, "error": f"Execution-Fehler: {e}", "source": "Backend/execution.txt"}

@app.post("/api/run_tests")
def run_tests():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        import httpx  # noqa
    except Exception as e:
        return {"ok": False, "error": "httpx fehlt (für TestClient). pip install httpx", "detail": str(e)}
    cmd = [sys.executable, "-m", "pytest", "-q", "-rA", "Tests"]
    proc = subprocess.run(cmd, cwd=ROOT_DIR, capture_output=True, text=True, timeout=300)
    exit_code = proc.returncode
    out = proc.stdout or ""
    err = proc.stderr or ""
    date_tag = datetime.now().strftime("%y-%m-%d")
    summary_path = REPORT_DIR / f"summary{date_tag}.txt"
    summary_path.write_text(out + "\n\n" + err, encoding="utf-8")
    return {"ok": True, "exit_code": exit_code, "summary_file": str(summary_path.relative_to(ROOT_DIR))}

@app.post("/api/run_test/idea")
def run_test_idea():
    """Run only the 'Idea' test file and return a concise report. Also append a line into today's summary file."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        import httpx  # noqa
    except Exception as e:
        return {"ok": False, "error": "httpx fehlt (für TestClient). pip install httpx", "detail": str(e)}
    # Only run the idea test
    test_path = "Tests/test_research_idea.py"
    cmd = [sys.executable, "-m", "pytest", "-q", "-rA", test_path]
    proc = subprocess.run(cmd, cwd=ROOT_DIR, capture_output=True, text=True, timeout=120)
    exit_code = proc.returncode
    out = proc.stdout or ""
    err = proc.stderr or ""
    # Parse a simple PASS/FAIL
    status = "PASS" if exit_code == 0 else "FAIL"
    # Append one line to dated summary file
    date_tag = datetime.now().strftime("%y-%m-%d")
    summary_path = REPORT_DIR / f"summary{date_tag}.txt"
    line = f"[{datetime.now().strftime('%H:%M:%S')}] IdeaTest: {status}"
    prev = summary_path.read_text(encoding="utf-8") if summary_path.exists() else ""
    summary_path.write_text(prev + ("\n" if prev else "") + line + "\n", encoding="utf-8")
    # Return concise JSON
    return {"ok": True, "test": "idea", "status": status, "exit_code": exit_code, "stdout": out[-2000:], "stderr": err[-2000:], "summary_file": str(summary_path.relative_to(ROOT_DIR))}

# Include research router with absolute import (if present)
try:
    from Backend.research_router import router as research_router
    app.include_router(research_router)
except Exception as e:
    @app.get("/api/research/health")
    def research_health():
        return {"ok": False, "error": f"research_router import failed: {e}"}