#!/bin/bash

set -euo pipefail

# Resolve the project root directory relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." &>/dev/null && pwd)"

echo "=== AOI System Deployment Script ==="
echo "Project Root: $PROJECT_ROOT"
cd "$PROJECT_ROOT"

if ! command -v conda &>/dev/null && [ -x "$HOME/miniconda3/bin/conda" ]; then
    export PATH="$HOME/miniconda3/bin:$PATH"
fi

# Check if project is built
if [ ! -d "frontend/dist" ]; then
    echo "Warning: Frontend build folder (frontend/dist) not found. Running build..."
    bash scripts/build/build.sh
fi

# In a typical production deployment, we might:
# 1. Start backend with uvicorn listening on port 8000
# 2. Run a reverse proxy (like Nginx) serving frontend/dist static files, proxying /api/ to backend.
# Here we will package/verify production-readiness.

echo "Verifying production dependencies..."
CONDA_ENV_NAME="aoi-app"
if ! conda env list | grep -q -E "^${CONDA_ENV_NAME}[[:space:]]"; then
    echo "Error: Conda environment '$CONDA_ENV_NAME' not found. Please run setup.sh first." >&2
    exit 1
fi

echo "Checking migration head and pilot safety gates..."
PYTHONPATH=.:backend conda run -n "$CONDA_ENV_NAME" python -m app.database.migrations check
if [ "${AOI_PILOT_ACCEPTANCE_REPORT:-}" = "" ] || [ ! -f "${AOI_PILOT_ACCEPTANCE_REPORT:-}" ]; then
    echo "BLOCKED: AOI_PILOT_ACCEPTANCE_REPORT must reference a measured target-hardware acceptance report." >&2
    echo "No production-ready claim was made. Simulator tests do not satisfy pilot acceptance." >&2
    exit 2
fi
PYTHONPATH=.:backend conda run -n "$CONDA_ENV_NAME" python \
    scripts/operations/verify-pilot-acceptance.py "$AOI_PILOT_ACCEPTANCE_REPORT" || exit 2
echo "Deployment preflight passed. Use a supervised single-worker station service behind a loopback reverse proxy."