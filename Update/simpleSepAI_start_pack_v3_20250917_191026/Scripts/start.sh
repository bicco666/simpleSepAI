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
mkdir -p "$LOG_DIR" "$REPORT_DIR"

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

# Export PYTHONPATH safely (avoid unbound var)
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
  exit 1
fi

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
check "GET /api/systemtest" bash -c 'curl -fsS http://127.0.0.1:'"$PORT_BACKEND"'/api/systemtest | python - <<PY
import sys,json; d=json.load(sys.stdin); 
assert d.get("ok") is True and "report" in d
PY'

# 2) idea
check "GET /api/idea" bash -c 'curl -fsS http://127.0.0.1:'"$PORT_BACKEND"'/api/idea | python - <<PY
import sys,json; d=json.load(sys.stdin); 
assert d.get("ok") is True and "idea" in d and "Kaufe 0,1 SOL" in d["idea"]
PY'

# 3) analysis
check "GET /api/analysis" bash -c 'curl -fsS http://127.0.0.1:'"$PORT_BACKEND"'/api/analysis | python - <<PY
import sys,json; d=json.load(sys.stdin); 
assert d.get("ok") is True and "analysis" in d and "Kaufe 0,1 SOL" in d["analysis"]
PY'

# 4) execute
check "POST /api/execute" bash -c 'curl -fsS -X POST http://127.0.0.1:'"$PORT_BACKEND"'/api/execute -H "Content-Type: application/json" -d "{\"sol\":0.01}" | python - <<PY
import sys,json; d=json.load(sys.stdin); 
assert d.get("ok") is True and isinstance(d.get("log"), list)
PY'

# 5) run_tests
check "POST /api/run_tests" bash -c 'curl -fsS -X POST http://127.0.0.1:'"$PORT_BACKEND"'/api/run_tests | python - <<PY
import sys,json; d=json.load(sys.stdin); assert d.get("ok") is True
print(d.get("summary_file","")); 
PY' | tee "$LOG_DIR/summary_path.txt" >/dev/null

SUMMARY_PATH_REL="$(cat "$LOG_DIR/summary_path.txt" || true)"
SUMMARY_PATH_ABS="$APP_DIR/${SUMMARY_PATH_REL}"
if [ -n "$SUMMARY_PATH_REL" ] && [ -f "$SUMMARY_PATH_ABS" ]; then
  echo "==> Summary file created: $SUMMARY_PATH_REL"
else
  echo "ERROR: No summary file detected"
  log_tail "$BACKEND_LOG" 200
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