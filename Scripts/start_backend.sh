#!/usr/bin/env bash
set -euo pipefail
source Backend/.venv/bin/activate
uvicorn Backend.app:app --reload