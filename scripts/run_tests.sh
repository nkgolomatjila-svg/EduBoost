#!/usr/bin/env bash
# Run pytest from repo root (pythonpath is set in pytest.ini).
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
if [[ -f .venv/bin/pytest ]]; then
  PY=.venv/bin/pytest
else
  PY=pytest
fi
exec "$PY" "$@"
