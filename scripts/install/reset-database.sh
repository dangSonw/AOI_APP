#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." &>/dev/null && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: .env is missing." >&2
    exit 1
fi

set -a
source "$ENV_FILE"
set +a

: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"

echo "WARNING: This will DROP all tables in '${POSTGRES_DB}' and recreate them."
echo "Press Ctrl+C within 5 seconds to cancel..."
sleep 5

echo "Resetting database..."
PGPASSWORD="$POSTGRES_PASSWORD" psql \
    --host="${POSTGRES_HOST:-127.0.0.1}" \
    --port="${POSTGRES_PORT:-5432}" \
    --username="$POSTGRES_USER" \
    --dbname="$POSTGRES_DB" \
    --set=ON_ERROR_STOP=1 \
    --file="$PROJECT_ROOT/database/scripts/reset_database.sql"

SCHEMA_DIR="$PROJECT_ROOT/database/schema"

for schema_file in "$SCHEMA_DIR"/*.sql; do
    echo "Applying schema: $(basename "$schema_file")..."
    PGPASSWORD="$POSTGRES_PASSWORD" psql \
        --host="${POSTGRES_HOST:-127.0.0.1}" \
        --port="${POSTGRES_PORT:-5432}" \
        --username="$POSTGRES_USER" \
        --dbname="$POSTGRES_DB" \
        --set=ON_ERROR_STOP=1 \
        --file="$schema_file"
done

SEED_DIR="$PROJECT_ROOT/database/seed"

if [ -d "$SEED_DIR" ]; then
    for seed_file in "$SEED_DIR"/*.sql; do
        echo "Seeding: $(basename "$seed_file")..."
        PGPASSWORD="$POSTGRES_PASSWORD" psql \
            --host="${POSTGRES_HOST:-127.0.0.1}" \
            --port="${POSTGRES_PORT:-5432}" \
            --username="$POSTGRES_USER" \
            --dbname="$POSTGRES_DB" \
            --set=ON_ERROR_STOP=1 \
            --file="$seed_file"
    done
fi

echo "Database reset complete."
