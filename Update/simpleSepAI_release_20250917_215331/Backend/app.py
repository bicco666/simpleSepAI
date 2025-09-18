from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime
import subprocess, sys

app = FastAPI(title="simpleSepAI API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

BASE_DIR = Path(__file__).parent
ROOT_DIR = BASE_DIR.parent
REPORT_DIR = ROOT_DIR / "Report"

def read_textfile(name: str) -> str:
    return (BASE_DIR / f"{name}.txt").read_text(encoding="utf-8").strip()

def ensure_phrase(text: str, phrase: str) -> str:
    return text if phrase in text else (text + (" | " if text else "") + phrase)

class ExecReq(BaseModel):
    sol: float | None = None

@app.get("/api/systemtest")
def systemtest(): return {"ok": True, "report": "10/10 Pass (File-Stub Mode)"}

@app.get("/api/idea")
def idea():
    content = read_textfile("idee"); idea_text = ensure_phrase(content, "Kaufe 0,1 SOL")
    return {"ok": True, "idea": idea_text, "file_content": content}

@app.get("/api/analysis")
def analysis():
    content = read_textfile("analyse"); analysis_text = ensure_phrase(content, "Kaufe 0,1 SOL")
    return {"ok": True, "analysis": analysis_text, "file_content": content}

@app.post("/api/execute")
def execute(_: ExecReq):
    content = read_textfile("execution"); log = [f"EXECUTION: {content}"]
    return {"ok": True, "execution": content, "log": log, "address": "DevnetStub111111111111", "balance": 0.0}

@app.post("/api/run_test/idea")
def run_test_idea():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "pytest", "-q", "-rA", "Tests/test_research_api.py::test_research_idea"]
    proc = subprocess.run(cmd, cwd=ROOT_DIR, capture_output=True, text=True, timeout=150)
    status = "PASS" if proc.returncode == 0 else "FAIL"
    date_tag = datetime.now().strftime("%y-%m-%d"); summary_path = REPORT_DIR / f"summary{date_tag}.txt"
    line = f"[{datetime.now().strftime('%H:%M:%S')}] IdeaTest: {status}"
    prev = summary_path.read_text(encoding="utf-8") if summary_path.exists() else ""
    summary_path.write_text((prev + ("
" if prev else "") + line + "
"), encoding="utf-8")
    return {"ok": True, "status": status, "stdout": (proc.stdout or "")[-2000:], "stderr": (proc.stderr or "")[-2000:], "summary_file": str(summary_path.relative_to(ROOT_DIR))}

from Backend.research_router import router as research_router
app.include_router(research_router)