#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." &>/dev/null && pwd)"
source "$SCRIPT_DIR/utils/require-ubuntu-wsl.sh"
require_ubuntu_runtime
configure_linux_toolchain

ACTION="${1:-start}"
CONDA_ENV_NAME="aoi-app"
RUNTIME_BASE="${XDG_RUNTIME_DIR:-${TMPDIR:-/tmp}}"
RUNTIME_KEY="$(printf '%s' "$PROJECT_ROOT" | cksum | awk '{print $1}')"
PID_FILE="$RUNTIME_BASE/aoi-simulator-${UID}-${RUNTIME_KEY}.pids"
CAMERA_URL="http://127.0.0.1:9101"
MOTION_URL="http://127.0.0.1:9102"
CONSOLE_URL="http://127.0.0.1:9200/"
MANAGES_SERVERS=false

print_usage() {
    echo "Usage: bash scripts/run_simulator.sh [start|stop|status]"
}

read_groups() {
    [ -f "$PID_FILE" ] || return 0
    awk -F= '/^(camera|motion|console)=/ {print $2}' "$PID_FILE" | grep -E '^[0-9]+$' || true
}

group_running() { kill -0 -- "-$1" 2>/dev/null; }

stop_groups() {
    local group
    local attempt
    for group in "$@"; do group_running "$group" && kill -TERM -- "-$group" 2>/dev/null || true; done
    for attempt in {1..30}; do
        local still_running=false
        for group in "$@"; do group_running "$group" && still_running=true; done
        $still_running || return 0
        sleep 0.1
    done
    for group in "$@"; do group_running "$group" && kill -KILL -- "-$group" 2>/dev/null || true; done
}

is_healthy() {
    curl --fail --silent --max-time 1 "$CAMERA_URL/health" | grep -q '"status":"ready"' && \
    curl --fail --silent --max-time 1 "$MOTION_URL/health" | grep -q '"status":"ready"' && \
    curl --fail --silent --max-time 1 --output /dev/null "$CONSOLE_URL"
}

show_status() {
    if is_healthy; then
        echo "AOI Simulator is running."
        echo "Console: $CONSOLE_URL"
        echo "Camera API: $CAMERA_URL"
        echo "Motion API: $MOTION_URL"
        return 0
    fi
    echo "AOI Simulator is stopped or unhealthy."
    return 1
}

open_windows_browser() {
    if [ "${AOI_SIMULATOR_NO_BROWSER:-0}" = "1" ]; then
        return 0
    fi
    if command -v powershell.exe >/dev/null 2>&1; then
        powershell.exe -NoProfile -NonInteractive -Command "Start-Process '$CONSOLE_URL'" >/dev/null 2>&1 || true
    elif command -v wslview >/dev/null 2>&1; then
        wslview "$CONSOLE_URL" >/dev/null 2>&1 || true
    fi
}

cleanup() {
    local exit_code="$1"
    if $MANAGES_SERVERS; then
        mapfile -t groups < <(read_groups)
        stop_groups "${groups[@]}"
        rm -f "$PID_FILE"
    fi
    exit "$exit_code"
}

case "$ACTION" in
    stop)
        mapfile -t groups < <(read_groups)
        if [ "${#groups[@]}" -gt 0 ]; then stop_groups "${groups[@]}"; fi
        rm -f "$PID_FILE"
        echo "AOI Simulator stopped."
        exit 0
        ;;
    status) show_status; exit $? ;;
    start) ;;
    *) print_usage >&2; exit 2 ;;
esac

if is_healthy; then
    show_status
    open_windows_browser
    exit 0
fi

for port in 9101 9102 9200; do
    if ss -ltn "sport = :$port" 2>/dev/null | grep -q LISTEN; then
        echo "Error: port $port is already in use." >&2
        exit 1
    fi
done

if ! command -v conda >/dev/null 2>&1 || ! conda env list | grep -q -E "^${CONDA_ENV_NAME}[[:space:]]"; then
    echo "Error: Conda environment '$CONDA_ENV_NAME' is unavailable. Run scripts/install/setup.sh first." >&2
    exit 1
fi

trap 'exit 130' SIGINT
trap 'exit 143' SIGTERM
trap 'cleanup $?' EXIT

cd "$PROJECT_ROOT"
setsid env PYTHONPATH="$PROJECT_ROOT" conda run --no-capture-output -n "$CONDA_ENV_NAME" \
    python -m uvicorn simulator.camera.app:app --host 127.0.0.1 --port 9101 &
CAMERA_GROUP=$!
setsid env PYTHONPATH="$PROJECT_ROOT" conda run --no-capture-output -n "$CONDA_ENV_NAME" \
    python -m uvicorn simulator.mcu.app:app --host 127.0.0.1 --port 9102 &
MOTION_GROUP=$!
cd "$PROJECT_ROOT/simulator/console"
setsid conda run --no-capture-output -n "$CONDA_ENV_NAME" python -m http.server 9200 --bind 127.0.0.1 &
CONSOLE_GROUP=$!
printf 'camera=%s\nmotion=%s\nconsole=%s\n' "$CAMERA_GROUP" "$MOTION_GROUP" "$CONSOLE_GROUP" > "$PID_FILE"
MANAGES_SERVERS=true

for _ in {1..100}; do
    if is_healthy; then
        echo "AOI Simulator Console is ready: $CONSOLE_URL"
        echo "Press Ctrl+C or run: bash scripts/run_simulator.sh stop"
        open_windows_browser
        set +e
        wait -n "$CAMERA_GROUP" "$MOTION_GROUP" "$CONSOLE_GROUP"
        exit 1
    fi
    sleep 0.1
done

echo "Error: AOI Simulator did not become healthy." >&2
exit 1