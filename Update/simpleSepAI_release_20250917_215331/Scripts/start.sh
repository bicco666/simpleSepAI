#!/usr/bin/env bash
set -euo pipefail
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"
PORT_BACKEND=${PORT_BACKEND:-8000}
PORT_FRONTEND=${PORT_FRONTEND:-8080}
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install fastapi uvicorn pydantic httpx pytest pyyaml openai requests
export PYTHONPATH="${APP_DIR}:${PYTHONPATH:-}"
mkdir -p .logs
uvicorn Backend.app:app --host 127.0.0.1 --port $PORT_BACKEND --log-level info > .logs/backend.log 2>&1 &
BEPID=$!
sleep 1
pushd Frontend >/dev/null
python -m http.server $PORT_FRONTEND > ../.logs/frontend.log 2>&1 &
FRPID=$!
popd >/dev/null
echo "Backend:  http://127.0.0.1:$PORT_BACKEND/docs"
echo "Frontend: http://127.0.0.1:$PORT_FRONTEND/index_protocol.html"
echo "Logs in:  $(realpath .logs)"
echo "Stop with: kill $BEPID $FRPID"