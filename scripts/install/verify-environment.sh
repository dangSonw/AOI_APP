#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." &>/dev/null && pwd)"

cd "$PROJECT_ROOT"

if [ ! -f .env ]; then
    echo "Error: .env is missing." >&2
    exit 1
fi

set -a
source .env
set +a

systemctl is-active --quiet postgresql
pg_isready --host="${POSTGRES_HOST:-127.0.0.1}" --port="${POSTGRES_PORT:-5432}" >/dev/null

TABLE_NAME="$(PGPASSWORD="$POSTGRES_PASSWORD" psql \
    --host="$POSTGRES_HOST" \
    --port="$POSTGRES_PORT" \
    --username="$POSTGRES_USER" \
    --dbname="$POSTGRES_DB" \
    --tuples-only \
    --no-align \
    --command="SELECT to_regclass('public.users');")"

if [ "$TABLE_NAME" != "users" ]; then
    echo "Error: users table was not found in the application database." >&2
    exit 1
fi

PYTHONPATH="$PROJECT_ROOT/backend" conda run -n aoi-app python -m app.database.migrations check

if [ "$(stat -c %a .env)" != "600" ]; then
    echo "Error: .env permissions must be 600." >&2
    exit 1
fi

python3 -m json.tool io/input.json >/dev/null
python3 -m json.tool io/output.json >/dev/null

echo "Environment verification passed."
echo "PostgreSQL: active"
echo "Database schema: Alembic revision current"
echo "Environment file: permission 600"
echo "Physical I/O JSON: valid"