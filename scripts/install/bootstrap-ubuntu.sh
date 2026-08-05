#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." &>/dev/null && pwd)"
source "$PROJECT_ROOT/scripts/utils/require-ubuntu-wsl.sh"

require_ubuntu_runtime

echo "Installing Ubuntu system dependencies..."
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    openssl \
    postgresql \
    postgresql-contrib

NODE_MAJOR_VERSION="$(node --version 2>/dev/null | sed -E 's/^v([0-9]+).*/\1/' || true)"
if [ -z "$NODE_MAJOR_VERSION" ] || [ "$NODE_MAJOR_VERSION" -lt 20 ]; then
    echo "Installing Node.js 20 LTS..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y nodejs
fi

if [ ! -x "$HOME/miniconda3/bin/conda" ]; then
    echo "Installing Miniconda..."
    MINICONDA_INSTALLER="$(mktemp)"
    curl -fsSL \
        https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
        --output "$MINICONDA_INSTALLER"
    bash "$MINICONDA_INSTALLER" -b -p "$HOME/miniconda3"
    rm -f "$MINICONDA_INSTALLER"
fi

export PATH="$HOME/miniconda3/bin:$PATH"
conda init bash >/dev/null

echo "Installing Linux-native CodeGraph..."
sudo npm install --global @colbymchenry/codegraph

cd "$PROJECT_ROOT"
rm -rf .codegraph
codegraph init .

bash scripts/install/setup.sh

echo "=== Ubuntu Bootstrap Completed Successfully ==="
echo "Node.js: $(node --version)"
echo "npm: $(npm --version)"
echo "Conda: $(conda --version)"
echo "PostgreSQL: $(psql --version)"
echo "CodeGraph: $(codegraph version)"