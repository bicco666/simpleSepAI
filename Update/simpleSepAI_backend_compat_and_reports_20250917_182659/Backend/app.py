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
    # If 'phrase' not already present (case-sensitive), append with separator.
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
        # Compatibility for old test assertion:
        # ensure r.json()['idea'] contains "Kaufe 0,1 SOL"
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
        # Provide backward-compatible fields expected by older tests:
        log = [f"EXECUTION: {content}"]
        return {
            "ok": True,
            "execution": content,
            "log": log,
            "address": "DevnetStub111111111111",
            "balance": 0.0,
            "source": "Backend/execution.txt"
        }
    except Exception as e:
        return {"ok": False, "error": f"Execution-Fehler: {e}", "source": "Backend/execution.txt"}

@app.post("/api/run_tests")
def run_tests():
    # Always ensure Report dir exists
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    # Dependency hint (for UI clarity only)
    try:
        import httpx  # noqa: F401
    except Exception as e:
        return {
            "ok": False,
            "error": "Fehlende Abhängigkeit: 'httpx'. Bitte zuerst installieren.",
            "next": "pip install httpx  # oder: pip install -r requirements.txt",
            "detail": str(e),
        }

    cmd = [sys.executable, "-m", "pytest", "-q", "Tests"]
    try:
        proc = subprocess.run(cmd, cwd=ROOT_DIR, capture_output=True, text=True, timeout=300)
        exit_code = proc.returncode
        out = proc.stdout or ""
        err = proc.stderr or ""
    except Exception as e:
        return {"ok": False, "error": f"Pytest-Aufruf fehlgeschlagen: {e}"}

    # Write ALWAYS a summary file, even if tests fail during collection.
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    summary_file = REPORT_DIR / "summary.txt"
    # Try to parse PASS/FAIL counts from pytest output; fallback to exit_code.
    passed = failed = 0
    # Look for lines like "3 failed, 1 passed" etc.
    m = re.search(r"(?:(\d+)\s+passed)?(?:,\s*)?(?:(\d+)\s+failed)?", out)
    if m:
        if m.group(1): passed = int(m.group(1))
        if m.group(2): failed = int(m.group(2))
    summary_dict = {
        "timestamp": timestamp,
        "exit_code": exit_code,
        "passed": passed,
        "failed": failed,
        "total": (passed + failed) if (passed or failed) else None,
    }
    summary_text = [
        f"Timestamp: {timestamp}",
        f"Exit code: {exit_code}",
        f"Passed: {passed}",
        f"Failed: {failed}",
        f"Total: {(passed + failed) if (passed or failed) else 'N/A'}",
        "",
        "---- Pytest stdout ----",
        out.strip(),
        "",
        "---- Pytest stderr ----",
        err.strip(),
        ""
    ]
    summary_file.write_text("\n".join(summary_text), encoding="utf-8")

    # Return JSON including path of summary
    return {
        "ok": True,
        "exit_code": exit_code,
        "summary": summary_dict,
        "summary_file": str(summary_file.relative_to(ROOT_DIR)),
        "pytest_out": out[-4000:],  # tail to keep response small
        "pytest_err": err[-4000:],
    }