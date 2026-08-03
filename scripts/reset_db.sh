#!/usr/bin/env bash
# Drops and rebuilds the dev database, then reapplies every migration.
#
# Usage:
#   ./scripts/reset_db.sh              # against Docker Compose's postgres
#   ./scripts/reset_db.sh --local      # against the native SQLite default
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ "${1:-}" == "--local" ]]; then
  echo "Resetting local SQLite database..."
  rm -f backend/businessos.db
  (cd backend && .venv/bin/alembic upgrade head)
else
  echo "Resetting postgres database via Docker Compose..."
  docker compose exec postgres psql -U businessos -d businessos \
    -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
  docker compose exec backend alembic upgrade head
fi

echo "Done. Run scripts/seed_dev_data.py next to repopulate demo data."
