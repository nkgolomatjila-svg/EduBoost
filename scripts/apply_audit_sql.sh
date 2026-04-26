#!/usr/bin/env bash
# Apply scripts/db_audit_migration.sql to a running Postgres (e.g. after docker compose up postgres).
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
: "${DATABASE_URL:?Set DATABASE_URL, e.g. postgresql://eduboost_user:devpassword@localhost:5432/eduboost}"
# Strip SQLAlchemy driver prefix for psql if present
URL="${DATABASE_URL#postgresql+asyncpg://}"
URL="${URL#postgresql://}"
psql "$URL" -v ON_ERROR_STOP=1 -f "$REPO_ROOT/scripts/db_audit_migration.sql"
echo "✅ Audit migration applied."
