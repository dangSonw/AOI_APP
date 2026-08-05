#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." &>/dev/null && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: .env is missing. Copy .env.example and replace all placeholder values first." >&2
    exit 1
fi

set -a
source "$ENV_FILE"
set +a

: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"

if [[ ! "$POSTGRES_DB" =~ ^[a-z_][a-z0-9_]*$ ]]; then
    echo "Error: POSTGRES_DB must be a lowercase PostgreSQL identifier." >&2
    exit 1
fi

if [[ ! "$POSTGRES_USER" =~ ^[a-z_][a-z0-9_]*$ ]]; then
    echo "Error: POSTGRES_USER must be a lowercase PostgreSQL identifier." >&2
    exit 1
fi

if [[ ! "$POSTGRES_PASSWORD" =~ ^[A-Za-z0-9_-]+$ ]]; then
    echo "Error: POSTGRES_PASSWORD may contain only letters, numbers, underscores, and hyphens." >&2
    exit 1
fi

if ! command -v psql &>/dev/null; then
    echo "Installing PostgreSQL server and client..."
    sudo apt-get update
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y postgresql postgresql-contrib
fi

sudo systemctl enable --now postgresql

if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='${POSTGRES_USER}'" | grep -q 1; then
    sudo -u postgres psql -v ON_ERROR_STOP=1 -c \
        "CREATE ROLE \"${POSTGRES_USER}\" LOGIN PASSWORD '${POSTGRES_PASSWORD}';"
else
    sudo -u postgres psql -v ON_ERROR_STOP=1 -c \
        "ALTER ROLE \"${POSTGRES_USER}\" WITH LOGIN PASSWORD '${POSTGRES_PASSWORD}';"
fi

if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${POSTGRES_DB}'" | grep -q 1; then
    sudo -u postgres createdb --owner="$POSTGRES_USER" "$POSTGRES_DB"
fi

PGPASSWORD="$POSTGRES_PASSWORD" psql \
    --host="${POSTGRES_HOST:-127.0.0.1}" \
    --port="${POSTGRES_PORT:-5432}" \
    --username="$POSTGRES_USER" \
    --dbname="$POSTGRES_DB" \
    --set=ON_ERROR_STOP=1 \
    --file="$PROJECT_ROOT/database/schema/001_create_users.sql"

echo "PostgreSQL is ready for AOI Studio."