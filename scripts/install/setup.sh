#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Resolve the project root directory relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." &>/dev/null && pwd)"

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

# Set up Python environment using Conda
CONDA_ENV_NAME="aoi-app"
echo "Setting up Python environment using Conda (env name: $CONDA_ENV_NAME)..."

if conda env list | grep -q -E "^${CONDA_ENV_NAME}[[:space:]]"; then
    echo "Conda environment '$CONDA_ENV_NAME' already exists."
else
    echo "Creating Conda environment '$CONDA_ENV_NAME' with Python 3.12..."
    conda create -y -n "$CONDA_ENV_NAME" python=3.12
fi

# Install packages using Conda run
echo "Installing backend Python packages inside Conda environment..."
conda run -n "$CONDA_ENV_NAME" pip install --upgrade pip || echo "Warning: Could not upgrade pip."
conda run -n "$CONDA_ENV_NAME" pip install -r backend/requirements.txt

# Set up Frontend
echo "Installing frontend Node packages..."
cd frontend
npm install
cd "$PROJECT_ROOT"

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

echo "=== Setup Completed Successfully ==="