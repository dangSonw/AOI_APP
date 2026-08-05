#!/bin/bash

# Exit immediately on errors, unset variables, or failed pipelines.
set -euo pipefail

# Resolve the project root directory relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." &>/dev/null && pwd)"
source "$PROJECT_ROOT/scripts/utils/require-ubuntu-wsl.sh"

require_ubuntu_runtime
configure_linux_toolchain

echo "=== AOI System Setup ==="
echo "Project Root: $PROJECT_ROOT"
cd "$PROJECT_ROOT"

# Check dependencies
echo "Checking dependencies..."
if ! command -v conda &>/dev/null; then
    echo "Error: conda is not installed. Please install Miniconda or Anaconda first." >&2
    exit 1
fi

if ! command -v npm &>/dev/null; then
    echo "Error: npm/node is not installed." >&2
    exit 1
fi

NODE_MAJOR_VERSION="$(node --version | sed -E 's/^v([0-9]+).*/\1/')"
if [ "$NODE_MAJOR_VERSION" -lt 20 ]; then
    echo "Error: Node.js 20 or newer is required. Run bootstrap-ubuntu.sh first." >&2
    exit 1
fi

# Set up Python environment using Conda
CONDA_ENV_NAME="aoi-app"
REQUIRED_PYTHON_MINOR="3.12"
echo "Setting up Python environment using Conda (env name: $CONDA_ENV_NAME)..."

if conda env list | grep -q -E "^${CONDA_ENV_NAME}[[:space:]]"; then
    echo "Conda environment '$CONDA_ENV_NAME' already exists."

    INSTALLED_PYTHON_MINOR="$(
        conda run -n "$CONDA_ENV_NAME" python -c \
            'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' \
            2>/dev/null || true
    )"
    if [ "$INSTALLED_PYTHON_MINOR" != "$REQUIRED_PYTHON_MINOR" ]; then
        echo "Repairing Conda environment '$CONDA_ENV_NAME' to Python $REQUIRED_PYTHON_MINOR..."
        conda install -y -n "$CONDA_ENV_NAME" \
            --override-channels \
            --channel conda-forge \
            "python=$REQUIRED_PYTHON_MINOR" \
            pip
    elif ! conda run -n "$CONDA_ENV_NAME" python -m pip --version &>/dev/null; then
        echo "Installing pip inside Conda environment '$CONDA_ENV_NAME'..."
        conda install -y -n "$CONDA_ENV_NAME" \
            --override-channels \
            --channel conda-forge \
            pip
    fi
else
    echo "Creating Conda environment '$CONDA_ENV_NAME' with Python 3.12 from conda-forge..."
    conda create -y -n "$CONDA_ENV_NAME" \
        --override-channels \
        --channel conda-forge \
        "python=$REQUIRED_PYTHON_MINOR" \
        pip
fi

# Bind pip to the environment interpreter instead of resolving a standalone pip executable.
echo "Installing backend Python packages inside Conda environment..."
conda run -n "$CONDA_ENV_NAME" python -m pip install --upgrade pip || \
    echo "Warning: Could not upgrade pip."
conda run -n "$CONDA_ENV_NAME" python -m pip install -r backend/requirements.txt

# Set up Frontend
echo "Installing frontend Node packages..."
cd frontend
npm install
cd "$PROJECT_ROOT"

# Create secure local configuration and initialize PostgreSQL.
echo "Preparing local environment configuration..."
bash scripts/install/create-local-env.sh
bash scripts/install/setup-postgresql.sh

# Ensure data directories exist
echo "Ensuring required data folders exist..."
mkdir -p data/cache
mkdir -p data/calibration
mkdir -p data/images
mkdir -p data/logs
mkdir -p data/models
mkdir -p data/projects
mkdir -p data/reports
mkdir -p data/temp
mkdir -p io

echo "Verifying the installed environment..."
bash scripts/install/verify-environment.sh

echo "=== Setup Completed Successfully ==="