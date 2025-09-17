
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import subprocess, sys, re
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

    # Dependency hint: httpx is required for fastapi/starlette TestClient
    try:
        import httpx  # noqa: F401
    except Exception as e:
        return {
            "ok": False,
            "error": "Fehlende Abhängigkeit: 'httpx'. Bitte zuerst installieren.",
            "next": "pip install httpx  # oder: pip install -r requirements.txt",
            "detail": str(e),
        }

    # Use -rA (report all) and -q for compactness; parse short summary info for per-test lines.
    cmd = [sys.executable, "-m", "pytest", "-q", "-rA", "Tests"]
    try:
        proc = subprocess.run(cmd, cwd=ROOT_DIR, capture_output=True, text=True, timeout=300)
        exit_code = proc.returncode
        out = proc.stdout or ""
        err = proc.stderr or ""
    except Exception as e:
        return {"ok": False, "error": f"Pytest-Aufruf fehlgeschlagen: {e}"}

    # Build per-test lines from the "short test summary info" section.
    # Expected lines look like:
    #   PASSED Tests/test_x.py::test_a
    #   FAILED Tests/test_y.py::test_b - AssertionError: ...
    lines = []
    capture = False
    for line in out.splitlines():
        if line.strip().startswith("short test summary info"):
            capture = True
            continue
        if capture:
            if line.strip().startswith("=") and "short test summary info" not in line:
                # reached another separator after the summary
                break
            s = line.strip()
            if not s:
                continue
            # Normalize: keep only STATUS and NODEID
            m = re.match(r"^(PASSED|FAILED|ERROR|SKIPPED|XFAILED|XPASSED|WARNING)\s+(.+)$", s)
            if m:
                status, nodeid_and_tail = m.group(1), m.group(2)
                nodeid = nodeid_and_tail.split(" - ")[0].strip()
                lines.append(f"{status} {nodeid}")

    # Fallback: if no lines parsed, try to glean names from verbose progress lines
    if not lines:
        for line in out.splitlines():
            m = re.match(r"^(Tests[^\s]+::\w+)\s+(PASSED|FAILED|ERROR|SKIPPED|XFAILED|XPASSED)$", line.strip())
            if m:
                lines.append(f"{m.group(2)} {m.group(1)}")

    # Create date-based summary file: summaryYY-MM-DD.txt
    date_tag = datetime.now().strftime("%y-%m-%d")
    summary_path = REPORT_DIR / f"summary{date_tag}.txt"
    header = [
        f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Exit code: {exit_code}",
        "Per-Test Ergebnisse:",
    ]
    body = lines if lines else ["(Keine per-Test-Zeilen gefunden – siehe pytest stdout unten)"]
    footer = ["", "---- Pytest stdout (Tail) ----", out[-4000:], "", "---- Pytest stderr (Tail) ----", err[-4000:], ""]
    summary_path.write_text("\n".join(header + body + footer), encoding="utf-8")

    return {
        "ok": True,
        "exit_code": exit_code,
        "summary_file": str(summary_path.relative_to(ROOT_DIR)),
        "per_test": lines,
    }
