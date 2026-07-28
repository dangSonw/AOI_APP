#!/bin/bash

set -e

# Resolve the project root directory relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." &>/dev/null && pwd)"

echo "=== AOI System Build ==="
echo "Project Root: $PROJECT_ROOT"
cd "$PROJECT_ROOT"

# Ensure Conda env and frontend node_modules exist, if not, run setup.sh
CONDA_ENV_NAME="aoi-app"
if ! conda env list | grep -q -E "^${CONDA_ENV_NAME}[[:space:]]" || [ ! -d "frontend/node_modules" ]; then
    echo "Dependencies or environment not installed. Running setup.sh first..."
    bash scripts/install/setup.sh
fi

# Build Frontend
echo "Building Frontend..."
cd frontend
npm run build
cd "$PROJECT_ROOT"

# Build Core Native Library
if [ -f "core/native/CMakeLists.txt" ]; then
    echo "Building Core Native C++ Library..."
    mkdir -p core/native/build
    cd core/native/build
    if command -v cmake &>/dev/null; then
        cmake ..
        cmake --build .
    else
        echo "Warning: cmake command not found. Skipping native compilation."
    fi
    cd "$PROJECT_ROOT"
fi

echo "=== Build Completed Successfully ==="