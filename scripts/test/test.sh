#!/bin/bash

# Resolve the project root directory relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." &>/dev/null && pwd)"

echo "=== AOI System Test Runner ==="
echo "Project Root: $PROJECT_ROOT"
cd "$PROJECT_ROOT"

# Ensure Conda env exists
CONDA_ENV_NAME="aoi-app"
if ! conda env list | grep -q -E "^${CONDA_ENV_NAME}[[:space:]]"; then
    echo "Error: Conda environment '$CONDA_ENV_NAME' not found. Please run setup.sh first." >&2
    exit 1
fi

# Check if pytest is installed, install it if not (just in case)
if ! conda run -n "$CONDA_ENV_NAME" pip show pytest &>/dev/null; then
    echo "pytest not found inside Conda environment. Installing pytest..."
    conda run -n "$CONDA_ENV_NAME" pip install pytest
fi

# Run Backend unit tests
echo "----------------------------------------"
echo "Running Backend Tests..."
echo "----------------------------------------"
if [ -d "tests/backend" ]; then
    conda run -n "$CONDA_ENV_NAME" pytest tests/backend/ || exit_code=1
else
    echo "No backend unit tests found in tests/backend"
fi

# Run Core unit tests
echo "----------------------------------------"
echo "Running Core Logic Tests..."
echo "----------------------------------------"
if [ -d "tests/core" ]; then
    conda run -n "$CONDA_ENV_NAME" pytest tests/core/ || exit_code=1
else
    echo "No core logic tests found in tests/core"
fi

# Run Integration tests
echo "----------------------------------------"
echo "Running Integration Tests..."
echo "----------------------------------------"
if [ -d "tests/integration" ]; then
    conda run -n "$CONDA_ENV_NAME" pytest tests/integration/ || exit_code=1
else
    echo "No integration tests found in tests/integration"
fi

# Check Frontend package.json for test script
echo "----------------------------------------"
echo "Running Frontend Lint & Type Checks..."
echo "----------------------------------------"
cd frontend
if npm run | grep -q "test"; then
    npm run test || exit_code=1
else
    echo "No frontend test script found. Running Type Checking..."
    npx tsc --noEmit || exit_code=1
fi
cd "$PROJECT_ROOT"

if [ "$exit_code" = "1" ]; then
    echo "=== Some Tests Failed! ==="
    exit 1
else
    echo "=== All Tests Passed Successfully ==="
    exit 0
fi