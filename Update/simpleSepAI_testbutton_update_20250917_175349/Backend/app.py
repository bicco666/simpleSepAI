from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import subprocess, json, os, sys

app = FastAPI(title="simpleSepAI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent                  # .../Backend
ROOT_DIR = BASE_DIR.parent                        # project root (contains Tests/, Report/)

def read_textfile(name: str) -> str:
    p = BASE_DIR / f"{name}.txt"
    return p.read_text(encoding="utf-8").strip()

class ExecReq(BaseModel):
    sol: float | None = None

@app.get("/api/systemtest")
def systemtest():
    return {"ok": True, "report": "10/10 Pass (File-Stub Mode)"}

@app.get("/api/idea")
def idea():
    try:
        content = read_textfile("idee")
        return {"ok": True, "idea": content, "source": "Backend/idee.txt"}
    except Exception as e:
        return {"ok": False, "error": f"Idee-Fehler: {e}", "source": "Backend/idee.txt"}

@app.get("/api/analysis")
def analysis():
    try:
        content = read_textfile("analyse")
        return {"ok": True, "analysis": content, "source": "Backend/analyse.txt"}
    except Exception as e:
        return {"ok": False, "error": f"Analyse-Fehler: {e}", "source": "Backend/analyse.txt"}

@app.post("/api/execute")
def execute(_: ExecReq):
    try:
        content = read_textfile("execution")
        return {"ok": True, "execution": content, "address": "DevnetStub111111111111", "balance": None, "source": "Backend/execution.txt"}
    except Exception as e:
        return {"ok": False, "error": f"Execution-Fehler: {e}", "source": "Backend/execution.txt"}

@app.post("/api/run_tests")
def run_tests():
    """Executes pytest to run the suite in Tests/, writing reports into Report/.
    Returns aggregated summary + raw pytest output."""
    # Ensure Report dir exists
    (ROOT_DIR / "Report").mkdir(parents=True, exist_ok=True)
    # Run pytest quietly, but capture output
    cmd = [sys.executable, "-m", "pytest", "-q", "Tests"]
    try:
        proc = subprocess.run(
            cmd, cwd=ROOT_DIR, capture_output=True, text=True, timeout=120
        )
        exit_code = proc.returncode
        out = proc.stdout
        err = proc.stderr
    except Exception as e:
        return {"ok": False, "error": f"Pytest-Aufruf fehlgeschlagen: {e}"}

    # Aggregate reports
    reports = []
    passed = failed = 0
    for p in sorted((ROOT_DIR / "Report").glob("*.txt")):
        text = p.read_text(encoding="utf-8")
        # naive status parse
        status_line = next((line for line in text.splitlines() if line.startswith("Status: ")), "Status: UNKNOWN")
        status = status_line.split("Status: ",1)[1].strip()
        if status.upper() == "PASS":
            passed += 1
        elif status.upper() == "FAIL":
            failed += 1
        reports.append({"file": str(p.relative_to(ROOT_DIR)), "status": status})

    return {
        "ok": True,
        "exit_code": exit_code,
        "summary": {"passed": passed, "failed": failed, "total": passed + failed},
        "pytest_out": out,
        "pytest_err": err,
        "reports": reports,
    }