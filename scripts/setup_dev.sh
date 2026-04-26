#!/usr/bin/env bash
# EduBoost SA — local development bootstrap (see README.md Quick Start).
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "🦁 EduBoost SA — Setting up development environment..."

if [[ ! -f .env ]]; then
  if [[ -f .env.example ]]; then
    cp .env.example .env
    echo "✅ .env created from .env.example — add your API keys."
  else
    echo "⚠️  No .env.example found; create .env manually."
  fi
fi

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "✅ Python dependencies installed"

pushd app/frontend >/dev/null
npm install --silent
echo "✅ Node dependencies installed"
popd >/dev/null

echo ""
echo "🚀 Setup complete. Start the stack:"
echo "   docker compose up --build"
echo "   API (no PYTHONPATH):  ./scripts/run_api.sh"
echo "   Tests:                ./scripts/run_tests.sh   # or:  source .venv/bin/activate && pytest"
echo "   Frontend:             cd app/frontend && npm run dev"
