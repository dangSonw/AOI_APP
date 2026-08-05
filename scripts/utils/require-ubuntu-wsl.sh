#!/bin/bash

require_ubuntu_runtime() {
    case "${OSTYPE:-}" in
        msys*|cygwin*|win32*)
            echo "Error: this script is running in Git Bash/Cygwin instead of Ubuntu WSL." >&2
            echo "Run it from PowerShell with: powershell -ExecutionPolicy Bypass -File scripts/run-dev-wsl.ps1" >&2
            echo "Or open an Ubuntu terminal and run the script there." >&2
            return 1
            ;;
    esac

    if [ "$(uname -s 2>/dev/null)" != "Linux" ] || [ ! -r /etc/os-release ]; then
        echo "Error: this script must run inside Ubuntu or Ubuntu WSL." >&2
        return 1
    fi

    if ! grep -qi '^ID=ubuntu' /etc/os-release; then
        echo "Error: this script requires Ubuntu." >&2
        return 1
    fi

    if [[ "${PATH:-}" == *"/cygdrive/"* ]]; then
        echo "Error: Windows Git Bash tools were detected in PATH." >&2
        echo "Start Ubuntu WSL first, then run this script again." >&2
        return 1
    fi
}

configure_linux_toolchain() {
    if [ -x "$HOME/miniconda3/bin/conda" ]; then
        export PATH="$HOME/miniconda3/bin:$PATH"
    fi

    hash -r

    local node_path
    local npm_path
    local conda_path
    node_path="$(command -v node 2>/dev/null || true)"
    npm_path="$(command -v npm 2>/dev/null || true)"
    conda_path="$(command -v conda 2>/dev/null || true)"

    if [[ "$node_path" == /mnt/* ]] || [[ "$npm_path" == /mnt/* ]] || [[ "$conda_path" == /mnt/* ]]; then
        echo "Error: a Windows Node.js, npm, or Conda executable was selected inside WSL." >&2
        echo "Ensure Linux tools are installed and precede /mnt/c entries in PATH." >&2
        return 1
    fi
}