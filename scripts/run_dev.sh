#!/bin/bash

# Resolve the project root directory relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." &>/dev/null && pwd)"

echo "=== AOI System Developer Server ==="
echo "Project Root: $PROJECT_ROOT"
cd "$PROJECT_ROOT"

# Ensure Conda env and frontend node_modules exist
CONDA_ENV_NAME="aoi-app"
if ! conda env list | grep -q -E "^${CONDA_ENV_NAME}[[:space:]]" || [ ! -d "frontend/node_modules" ]; then
    echo "Dependencies not installed. Running setup.sh first..."
    bash scripts/install/setup.sh
fi

# Function to stop background processes when Ctrl+C is pressed
cleanup() {
    echo ""
    echo "Stopping servers..."
    # Kill the process group to ensure all background tasks are stopped
    kill $(jobs -p) 2>/dev/null || true
    echo "Servers stopped."
    exit 0
}

# Trap Ctrl+C (SIGINT) and SIGTERM
trap cleanup SIGINT SIGTERM

# Start backend server
echo "Starting Backend API (FastAPI) on http://127.0.0.1:8000..."
cd "$PROJECT_ROOT/backend"
# Run uvicorn inside Conda environment
conda run --no-capture-output -n "$CONDA_ENV_NAME" uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# Start frontend dev server
echo "Starting Frontend Development Server (Vite)..."
cd "$PROJECT_ROOT/frontend"
npm run dev &
FRONTEND_PID=$!

echo "========================================="
echo "AOI Development environment running!"
echo "Press Ctrl+C to stop both servers."
echo "========================================="

# Keep script running and monitor background jobs
wait