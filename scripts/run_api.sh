#!/usr/bin/env bash
# Run the API from the repo root (correct import path for app.api.*).
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
if [[ -f .venv/bin/uvicorn ]]; then
  UV=.venv/bin/uvicorn
else
  UV=uvicorn
fi
exec "$UV" app.api.main:app --reload --host 0.0.0.0 --port 8000
