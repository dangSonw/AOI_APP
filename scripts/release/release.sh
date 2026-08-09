#!/bin/bash

# Exit on error
set -e

# Resolve the project root directory relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." &>/dev/null && pwd)"

echo "=== AOI System Release Packager ==="
echo "Project Root: $PROJECT_ROOT"
cd "$PROJECT_ROOT"

# Ensure clean build
echo "Running clean build..."
bash scripts/build/build.sh

# Create release package name with date/timestamp
VERSION=$(node -p "require('./frontend/package.json').version" 2>/dev/null || echo "0.1.0")
RELEASE_NAME="aoi-app-v${VERSION}"
RELEASE_DIR="release/${RELEASE_NAME}"

echo "Preparing release package in $RELEASE_DIR..."
mkdir -p "$RELEASE_DIR"

# Copy directories to release directory
cp -r frontend/dist "$RELEASE_DIR/frontend-dist"
cp -r backend "$RELEASE_DIR/backend"
cp -r core "$RELEASE_DIR/core"
cp -r hardware "$RELEASE_DIR/hardware"
cp -r simulator "$RELEASE_DIR/simulator"
cp -r database "$RELEASE_DIR/database"
cp -r docs "$RELEASE_DIR/docs"
cp -r scripts "$RELEASE_DIR/scripts"
cp README.md "$RELEASE_DIR/"
cp LICENSE "$RELEASE_DIR/" 2>/dev/null || true

# Remove environment-specific/temporary files in release folder
rm -rf "$RELEASE_DIR/backend/.venv"
rm -rf "$RELEASE_DIR/backend/__pycache__"
rm -rf "$RELEASE_DIR/backend/app/__pycache__"
rm -rf "$RELEASE_DIR/core/native/build"
find "$RELEASE_DIR" -type d -name '__pycache__' -prune -exec rm -rf {} +
find "$RELEASE_DIR" -type f -name '*.pyc' -delete

# Archive release directory
echo "Creating archive..."
cd release
tar -czf "${RELEASE_NAME}.tar.gz" "${RELEASE_NAME}"
sha256sum "${RELEASE_NAME}.tar.gz" > "${RELEASE_NAME}.tar.gz.sha256"
rm -rf "${RELEASE_NAME}"

echo "=== Release Packaged Successfully: release/${RELEASE_NAME}.tar.gz ==="