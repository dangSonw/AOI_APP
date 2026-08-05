#!/bin/bash

# Exit on error
set -e

# Resolve the project root directory relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." &>/dev/null && pwd)"

echo "=== AOI System Deployment Script ==="
echo "Project Root: $PROJECT_ROOT"
cd "$PROJECT_ROOT"

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

echo "AOI System is ready for deployment."
echo "Production Launch Commands:"
echo "1. Run backend server:"
echo "   nohup conda run --no-capture-output -n $CONDA_ENV_NAME python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --workers 4 > backend.log 2>&1 &"
echo "2. Serve frontend:"
echo "   Serve 'frontend/dist' directory using Nginx, Apache, or Caddy."
echo "=== Deployment Check Passed ==="