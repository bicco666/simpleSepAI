#!/usr/bin/env bash
set -euo pipefail

# --- Config ---
PORT_BACKEND=${PORT_BACKEND:-8000}
PORT_FRONTEND=${PORT_FRONTEND:-8080}
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$APP_DIR/.venv"
REQ_FILE="$APP_DIR/requirements.txt"
BACKEND_DIR="$APP_DIR/Backend"
FRONTEND_DIR="$APP_DIR/Frontend"
REPORT_DIR="$APP_DIR/Report"
LOG_DIR="$APP_DIR/.logs"
mkdir -p "$LOG_DIR" "$REPORT_DIR" "$FRONTEND_DIR"

# Ensure a minimal index if none exists
if [ ! -f "$FRONTEND_DIR/index_with_test_button.html" ] && [ ! -f "$FRONTEND_DIR/index_with_groups_robust.html" ] && [ ! -f "$FRONTEND_DIR/index.html" ]; then
  cat > "$FRONTEND_DIR/index.html" <<'HTML'
<!doctype html><meta charset="utf-8"><title>simpleSepAI</title>
<h1>simpleSepAI Frontend</h1><p>Platzhalter. Backend: <a href="http://127.0.0.1:8000/docs">/docs</a></p>
HTML
fi

echo "==> Project root: $APP_DIR"

# --- Helpers ---
have_cmd() { command -v "$1" >/dev/null 2>&1; }
wait_for_http() {
  local url="$1"; local tries="${2:-60}"; local delay="${3:-0.5}"
  for ((i=1; i<=tries; i++)); do
    if curl -fsS "$url" >/dev/null; then return 0; fi
    sleep "$delay"
  done
  return 1
}
log_tail() {
  local file="$1"; local n="${2:-200}"
  if [ -f "$file" ]; then
    echo "---- tail -n $n $file ----"
    tail -n "$n" "$file" || true
    echo "---------------------------"
  else
    echo "(no log file at $file)"
  fi
}

# --- Preflight: ensure backend files exist ---
mkdir -p "$BACKEND_DIR"
[ -f "$BACKEND_DIR/__init__.py" ] || : > "$BACKEND_DIR/__init__.py"
[ -f "$BACKEND_DIR/idee.txt" ] || echo "Kauf 0,01 Solana" > "$BACKEND_DIR/idee.txt"
[ -f "$BACKEND_DIR/analyse.txt" ] || echo "kaufe 0,1 solana um 13:47 und verkaufe um 13:48" > "$BACKEND_DIR/analyse.txt"
[ -f "$BACKEND_DIR/execution.txt" ] || echo "testtransaction send 0,01 sol" > "$BACKEND_DIR/execution.txt"

if [ ! -f "$BACKEND_DIR/app.py" ]; then
  echo "ERROR: $BACKEND_DIR/app.py fehlt. Bitte Backend/app.py einfügen und erneut starten."
  exit 1
fi

# --- Python & venv ---
if ! have_cmd python3; then
  echo "ERROR: python3 not found"; exit 1
fi
python3 -V

if [ ! -d "$VENV_DIR" ]; then
  echo "==> Creating venv at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

echo "==> Installing dependencies"
if [ -f "$REQ_FILE" ]; then
  python -m pip install -r "$REQ_FILE"
else
  python -m pip install fastapi uvicorn pydantic pytest httpx
fi

# Export PYTHONPATH safely
export PYTHONPATH="${APP_DIR}${PYTHONPATH:+:$PYTHONPATH}"

# --- Kill previous servers on ports (best-effort) ---
if have_cmd lsof; then
  lsof -ti tcp:$PORT_BACKEND | xargs -r kill -9 || true
  lsof -ti tcp:$PORT_FRONTEND | xargs -r kill -9 || true
fi

# --- Start Backend ---
echo "==> Starting Backend (uvicorn) on :$PORT_BACKEND"
BACKEND_LOG="$LOG_DIR/backend.log"
set +e
uvicorn Backend.app:app --host 127.0.0.1 --port $PORT_BACKEND --log-level info >"$BACKEND_LOG" 2>&1 &
BEPID=$!
sleep 1
if ! ps -p $BEPID >/dev/null 2>&1; then
  echo "==> Fallback: start via --app-dir Backend"
  uvicorn app:app --host 127.0.0.1 --port $PORT_BACKEND --app-dir "$BACKEND_DIR" --log-level info >"$BACKEND_LOG" 2>&1 &
  BEPID=$!
  sleep 1
fi
set -e

# --- Start Frontend static server ---
echo "==> Starting Frontend (http.server) on :$PORT_FRONTEND"
FRONTEND_LOG="$LOG_DIR/frontend.log"
pushd "$FRONTEND_DIR" >/dev/null
python -m http.server $PORT_FRONTEND >"$FRONTEND_LOG" 2>&1 &
FRPID=$!
popd >/dev/null

# --- Wait for services ---
echo "==> Waiting for Backend ..."
if ! wait_for_http "http://127.0.0.1:$PORT_BACKEND/api/systemtest" 60 0.5; then
  echo "ERROR: Backend did not become ready on :$PORT_BACKEND"
  log_tail "$BACKEND_LOG" 200
  exit 1
fi

echo "==> Waiting for Frontend ..."
MAIN_HTML="index_with_test_button.html"
[ -f "$FRONTEND_DIR/$MAIN_HTML" ] || MAIN_HTML="index_with_groups_robust.html"
[ -f "$FRONTEND_DIR/$MAIN_HTML" ] || MAIN_HTML="index.html"
if ! wait_for_http "http://127.0.0.1:$PORT_FRONTEND/$MAIN_HTML" 60 0.5; then
  echo "ERROR: Frontend did not become ready on :$PORT_FRONTEND"
  log_tail "$FRONTEND_LOG" 200
  # Frontend ist optional: weiterlaufen, aber Hinweis ausgeben
  echo "WARN: continue without Frontend"
fi

# --- Selfcheck helpers (fixed JSON path) ---
json_assert() {
  local json="$1"; local py_expr="$2"; local name="$3"
  python - "$json" "$name" <<'PY'
import sys,json
data = sys.argv[1]
name = sys.argv[2]
try:
    d = json.loads(data)
except Exception as e:
    print(f"{name}: JSON parse failed: {e}")
    sys.exit(1)
ok = False
try:
    # py_expr can refer to 'd'
    ok = eval(sys.stdin.read() or "True")
except Exception as e:
    print(f"{name}: eval failed: {e}")
    sys.exit(1)
if not ok:
    print(f"{name}: assertion failed")
    sys.exit(1)
PY
}

# --- Selfcheck ---
PASS=0; FAIL=0
check() {
  local name="$1"; shift
  echo "--> $name"
  if "$@"; then
    echo "OK: $name"; PASS=$((PASS+1))
  else
    echo "FAIL: $name"; FAIL=$((FAIL+1))
  fi
}

# 1) systemtest
resp=$(curl -fsS "http://127.0.0.1:$PORT_BACKEND/api/systemtest" || echo "")
echo "$resp" > "$LOG_DIR/systemtest.json"
check "GET /api/systemtest" bash -c 'json=$(cat "'"$LOG_DIR/systemtest.json"'"); python - "$json" <<PY
import sys,json
d=json.loads(sys.argv[1])
assert d.get("ok") is True and "report" in d
PY'

# 2) idea
resp=$(curl -fsS "http://127.0.0.1:$PORT_BACKEND/api/idea" || echo "")
echo "$resp" > "$LOG_DIR/idea.json"
check "GET /api/idea" bash -c 'json=$(cat "'"$LOG_DIR/idea.json"'"); python - "$json" <<PY
import sys,json
d=json.loads(sys.argv[1])
assert d.get("ok") is True and "idea" in d and "Kaufe 0,1 SOL" in d["idea"]
PY'

# 3) analysis
resp=$(curl -fsS "http://127.0.0.1:$PORT_BACKEND/api/analysis" || echo "")
echo "$resp" > "$LOG_DIR/analysis.json"
check "GET /api/analysis" bash -c 'json=$(cat "'"$LOG_DIR/analysis.json"'"); python - "$json" <<PY
import sys,json
d=json.loads(sys.argv[1])
assert d.get("ok") is True and "analysis" in d and "Kaufe 0,1 SOL" in d["analysis"]
PY'

# 4) execute
resp=$(curl -fsS -X POST "http://127.0.0.1:$PORT_BACKEND/api/execute" -H "Content-Type: application/json" -d '{"sol":0.01}' || echo "")
echo "$resp" > "$LOG_DIR/execute.json"
check "POST /api/execute" bash -c 'json=$(cat "'"$LOG_DIR/execute.json"'"); python - "$json" <<PY
import sys,json
d=json.loads(sys.argv[1])
assert d.get("ok") is True and isinstance(d.get("log"), list)
PY'

# 5) run_tests
resp=$(curl -fsS -X POST "http://127.0.0.1:$PORT_BACKEND/api/run_tests" || echo "")
echo "$resp" > "$LOG_DIR/run_tests.json"
check "POST /api/run_tests" bash -c 'json=$(cat "'"$LOG_DIR/run_tests.json"'"); python - "$json" <<PY
import sys,json,os
d=json.loads(sys.argv[1])
assert d.get("ok") is True and "summary_file" in d
PY'

summary_rel=$(python - "$resp" <<PY
import sys,json
d=json.loads(sys.stdin.read())
print(d.get("summary_file",""))
PY
)
if [ -n "$summary_rel" ] && [ -f "$APP_DIR/$summary_rel" ]; then
  echo "==> Summary file created: $summary_rel"
else
  echo "ERROR: No summary file detected"
  log_tail "$BACKEND_LOG" 200
  echo "---- run_tests.json ----"; cat "$LOG_DIR/run_tests.json" || true; echo "------------------------"
  FAIL=$((FAIL+1))
fi

echo "==> Selfcheck done: $PASS passed, $FAIL failed."
if [ $FAIL -gt 0 ]; then
  echo "Some checks failed. See logs in $LOG_DIR"
  exit 1
fi

echo ""
echo "Backend:  http://127.0.0.1:$PORT_BACKEND/docs"
echo "Frontend: http://127.0.0.1:$PORT_FRONTEND/$MAIN_HTML"
echo "Logs:     $LOG_DIR"