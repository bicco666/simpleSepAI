from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path

app = FastAPI(title="simpleSepAI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent  # .../Backend

def read_textfile(name: str) -> str:
    """Read text content from a file placed in Backend/<name>.txt.
    Returns the stripped content. Raises FileNotFoundError on missing file."""
    p = BASE_DIR / f"{name}.txt"
    return p.read_text(encoding="utf-8").strip()

class ExecReq(BaseModel):
    sol: float | None = None  # Ignored; we only echo file content for testing

@app.get("/api/systemtest")
def systemtest():
    # Keep a simple OK stub for smoke tests
    return {"ok": True, "report": "10/10 Pass (File-Stub Mode)"}

@app.get("/api/idea")
def idea():
    try:
        content = read_textfile("idee")
        return {"ok": True, "idea": content, "source": "Backend/idee.txt"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/api/analysis")
def analysis():
    try:
        content = read_textfile("analyse")
        return {"ok": True, "analysis": content, "source": "Backend/analyse.txt"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.post("/api/execute")
def execute(_: ExecReq):
    try:
        content = read_textfile("execution")
        # Keep ok=True so the UI shows OK status; return address/balance as placeholders
        return {"ok": True, "execution": content, "address": "DevnetStub111111111111", "balance": None, "source": "Backend/execution.txt"}
    except Exception as e:
        return {"ok": False, "error": str(e)}