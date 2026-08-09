#!/bin/bash

# Resolve the project root directory relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." &>/dev/null && pwd)"

echo "=== AOI System Test Runner ==="
echo "Project Root: $PROJECT_ROOT"
cd "$PROJECT_ROOT"
exit_code=0

if ! command -v conda &>/dev/null && [ -x "$HOME/miniconda3/bin/conda" ]; then
    export PATH="$HOME/miniconda3/bin:$PATH"
fi

# Ensure Conda env exists
CONDA_ENV_NAME="aoi-app"
if ! conda env list | grep -q -E "^${CONDA_ENV_NAME}[[:space:]]"; then
    echo "Error: Conda environment '$CONDA_ENV_NAME' not found. Please run setup.sh first." >&2
    exit 1
fi

# Check if pytest is installed, install it if not (just in case)
if ! conda run -n "$CONDA_ENV_NAME" python -m pip show pytest &>/dev/null; then
    echo "pytest not found inside Conda environment. Installing pytest..."
    conda run -n "$CONDA_ENV_NAME" python -m pip install pytest
fi

# Run Backend unit tests
echo "----------------------------------------"
echo "Running Backend Tests..."
echo "----------------------------------------"
if find tests/backend -maxdepth 1 -name 'test_*.py' | grep -q .; then
    PYTHONPATH=backend conda run -n "$CONDA_ENV_NAME" python -m pytest tests/backend/ || exit_code=1
else
    echo "No backend unit tests found in tests/backend"
fi

# Run Core unit tests
echo "----------------------------------------"
echo "Running Core Logic Tests..."
echo "----------------------------------------"
if find tests/core -maxdepth 1 -name 'test_*.py' | grep -q .; then
    conda run -n "$CONDA_ENV_NAME" python -m pytest tests/core/ || exit_code=1
else
    echo "No core logic tests found in tests/core"
fi

# Run Integration tests
echo "----------------------------------------"
echo "Running Integration Tests..."
echo "----------------------------------------"
if find tests/integration -maxdepth 1 -name 'test_*.py' | grep -q .; then
    PYTHONPATH=backend conda run -n "$CONDA_ENV_NAME" python -m pytest tests/integration/ || exit_code=1
else
    echo "No integration tests found in tests/integration"
fi

# Run adapter contract tests
echo "----------------------------------------"
echo "Running Device Contract Tests..."
echo "----------------------------------------"
if find tests/contract -maxdepth 1 -name 'test_*.py' 2>/dev/null | grep -q .; then
    conda run -n "$CONDA_ENV_NAME" python -m pytest tests/contract/ || exit_code=1
else
    echo "No device contract tests found in tests/contract"
fi

# Run hardware-independent simulator tests
echo "----------------------------------------"
echo "Running Simulator Tests..."
echo "----------------------------------------"
if find tests/simulator -maxdepth 1 -name 'test_*.py' 2>/dev/null | grep -q .; then
    conda run -n "$CONDA_ENV_NAME" python -m pytest tests/simulator/ || exit_code=1
else
    echo "No simulator tests found in tests/simulator"
fi

# Run hardware boundary tests without requiring physical devices
echo "----------------------------------------"
echo "Running Hardware Boundary Tests..."
echo "----------------------------------------"
if find tests/hardware -maxdepth 1 -name 'test_*.py' 2>/dev/null | grep -q .; then
    PYTHONPATH=.:backend conda run -n "$CONDA_ENV_NAME" python -m pytest tests/hardware/ || exit_code=1
else
    echo "No hardware boundary tests found in tests/hardware"
fi

echo "----------------------------------------"
echo "Running Frontend Tests & Type Checks..."
echo "----------------------------------------"
cd frontend
npm run test || exit_code=1
npm run typecheck || exit_code=1
cd "$PROJECT_ROOT"

if [ "$exit_code" = "1" ]; then
    echo "=== Some Tests Failed! ==="
    exit 1
else
    echo "=== All Tests Passed Successfully ==="
    exit 0
fi