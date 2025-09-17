#!/usr/bin/env bash
set -euo pipefail
uvicorn Backend.app:app --reload