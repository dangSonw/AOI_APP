#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." &>/dev/null && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

if [ -f "$ENV_FILE" ]; then
    echo "Local .env already exists; no credentials were changed."
    exit 0
fi

DATABASE_PASSWORD="$(openssl rand -hex 24)"
JWT_SECRET_KEY="$(openssl rand -hex 32)"
OPERATOR_PASSWORD="$(openssl rand -hex 12)"

cat > "$ENV_FILE" <<EOF
APP_NAME="AOI System API"
APP_ENVIRONMENT=development
API_HOST=127.0.0.1
API_PORT=8000
FRONTEND_ORIGIN=http://127.0.0.1:5173
VITE_API_BASE_URL=http://127.0.0.1:8000
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DB=aoi_app
POSTGRES_USER=aoi_app
POSTGRES_PASSWORD=${DATABASE_PASSWORD}
DATABASE_URL=postgresql+psycopg://aoi_app:${DATABASE_PASSWORD}@127.0.0.1:5432/aoi_app
JWT_SECRET_KEY=${JWT_SECRET_KEY}
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
SEED_ADMIN_EMAIL=operator@aoi.local
SEED_ADMIN_PASSWORD=${OPERATOR_PASSWORD}
SEED_ADMIN_FULL_NAME="AOI Operator"
PHYSICAL_IO_DIRECTORY=io
EOF

chmod 600 "$ENV_FILE"
echo "Created .env with random local credentials and permission 600."
echo "Read SEED_ADMIN_PASSWORD from .env before your first sign in."