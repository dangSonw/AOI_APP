#!/bin/bash

set -euo pipefail

# Resolve the project root directory relative to this script.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." &>/dev/null && pwd)"
source "$SCRIPT_DIR/utils/require-ubuntu-wsl.sh"

require_ubuntu_runtime

ACTION="${1:-start}"
RUNTIME_MODE="hardware"
DEBUG_MODE=false
if [ "$ACTION" = "simulation" ]; then
    ACTION="start"
    RUNTIME_MODE="simulation"
    if [ "${2:-}" = "debug" ] || [ "${VITE_AOI_SIMULATOR_NO_BROWSER:-0}" = "1" ]; then
        DEBUG_MODE=true
    elif [ -n "${2:-}" ]; then
        echo "Error: simulation accepts only the optional 'debug' argument." >&2
        exit 2
    fi
elif [ "$ACTION" = "start" ] && [ "${2:-}" = "--mode" ]; then
    RUNTIME_MODE="${3:-}"
    if [ "${4:-}" = "debug" ]; then
        DEBUG_MODE=true
    elif [ -n "${4:-}" ]; then
        echo "Error: start --mode accepts only the optional 'debug' argument." >&2
        exit 2
    fi
fi
CONDA_ENV_NAME="aoi-app"
RUNTIME_BASE="${XDG_RUNTIME_DIR:-${TMPDIR:-/tmp}}"
RUNTIME_KEY="$(printf '%s' "$PROJECT_ROOT" | cksum | awk '{print $1}')"
PID_FILE="$RUNTIME_BASE/aoi-studio-${UID}-${RUNTIME_KEY}.pids"
MANAGES_SERVERS=false
CLEANUP_STARTED=false

print_header() {
    echo "=== AOI System Developer Server ==="
    echo "Project Root: $PROJECT_ROOT"
}

print_usage() {
    cat <<'EOF'
Usage: bash scripts/run_dev.sh [start|stop|status|simulation]

  start   Start hardware adapters, backend, and frontend (default).
  start --mode simulation [debug]
          Start simulator adapters, backend, and frontend.
  simulation [debug]
          Alias for start --mode simulation.
  simulation debug
           Open the local development workspace with a server-issued debug session.
  stop    Stop AOI Studio processes started for this repository.
  status  Show whether this repository's development servers are running.
EOF
}

open_windows_browser() {
    local url="$1"
    if command -v powershell.exe >/dev/null 2>&1; then
        powershell.exe -NoProfile -NonInteractive -Command "Start-Process '$url'" >/dev/null 2>&1 || true
    elif command -v wslview >/dev/null 2>&1; then
        wslview "$url" >/dev/null 2>&1 || true
    fi
}

read_runtime_mode() {
    local stored_mode
    [ -f "$PID_FILE" ] || return 0
    stored_mode="$(awk -F= '$1 == "RUNTIME_MODE" {print $2; exit}' "$PID_FILE")"
    if [ "$stored_mode" = "hardware" ] || [ "$stored_mode" = "simulation" ]; then
        RUNTIME_MODE="$stored_mode"
    fi
}

# Return process groups containing an AOI backend or frontend whose working
# directory belongs to this repository. Checking both command and cwd prevents
# the stop command from terminating an unrelated Vite or Uvicorn project.
find_project_server_groups() {
    local process_dir
    local process_id
    local process_group
    local process_cwd
    local process_command

    for process_dir in /proc/[0-9]*; do
        process_id="${process_dir##*/}"
        process_cwd="$(readlink "$process_dir/cwd" 2>/dev/null || true)"

        case "$process_cwd" in
            "$PROJECT_ROOT"|"$PROJECT_ROOT/backend"|"$PROJECT_ROOT/frontend"|"$PROJECT_ROOT/simulator/console") ;;
            *) continue ;;
        esac

        process_command="$(cat "$process_dir/cmdline" 2>/dev/null | tr '\0' ' ' || true)"
        case "$process_cwd:$process_command" in
            "$PROJECT_ROOT/backend:"*"python -m uvicorn app.main:app"*"--port 8000"*|\
            "$PROJECT_ROOT/frontend:"*"npm run dev"*"--strictPort"*|\
            "$PROJECT_ROOT/frontend:"*"vite"*"--strictPort"*|\
            "$PROJECT_ROOT:"*"python -m uvicorn hardware.camera.app:app"*"--port 9101"*|\
            "$PROJECT_ROOT:"*"python -m uvicorn hardware.mcu.app:app"*"--port 9102"*|\
            "$PROJECT_ROOT:"*"python -m uvicorn simulator.camera.app:app"*"--port 9101"*|\
            "$PROJECT_ROOT:"*"python -m uvicorn simulator.mcu.app:app"*"--port 9102"*|\
            "$PROJECT_ROOT/simulator/console:"*"python -m http.server 9200"*) ;;
            *) continue ;;
        esac

        process_group="$(ps -o pgid= -p "$process_id" 2>/dev/null | tr -d '[:space:]' || true)"
        if [[ "$process_group" =~ ^[0-9]+$ ]]; then
            printf '%s\n' "$process_group"
        fi
    done | sort -un
}

is_process_group_running() {
    local process_group="$1"
    kill -0 -- "-$process_group" 2>/dev/null
}

stop_process_groups() {
    local -a process_groups=("$@")
    local process_group
    local attempt
    local has_running_group

    for process_group in "${process_groups[@]}"; do
        if is_process_group_running "$process_group"; then
            kill -TERM -- "-$process_group" 2>/dev/null || true
        fi
    done

    for attempt in {1..50}; do
        has_running_group=false
        for process_group in "${process_groups[@]}"; do
            if is_process_group_running "$process_group"; then
                has_running_group=true
                break
            fi
        done

        if [ "$has_running_group" = false ]; then
            return 0
        fi
        sleep 0.1
    done

    for process_group in "${process_groups[@]}"; do
        if is_process_group_running "$process_group"; then
            echo "Process group $process_group did not stop gracefully; forcing shutdown."
            kill -KILL -- "-$process_group" 2>/dev/null || true
        fi
    done
}

stop_project_servers() {
    local -a process_groups
    mapfile -t process_groups < <(find_project_server_groups)

    if [ "${#process_groups[@]}" -eq 0 ]; then
        rm -f "$PID_FILE"
        return 1
    fi

    stop_process_groups "${process_groups[@]}"
    rm -f "$PID_FILE"
    return 0
}

adapter_is_healthy() {
    local url="$1"
    local response
    response="$(curl --fail --silent --max-time 2 "$url")" || return 1
    printf '%s' "$response" | grep -q '"protocolVersion":"1.0"' || return 1
    if [ "$RUNTIME_MODE" = "simulation" ]; then
        printf '%s' "$response" | grep -q '"status":"ready"'
    else
        printf '%s' "$response" | grep -Eq '"status":"(ready|degraded|unavailable)"'
    fi
}

is_stack_healthy() {
    local is_base_healthy=false
    if ss -ltn "sport = :9101" 2>/dev/null | grep -q LISTEN && \
        ss -ltn "sport = :9102" 2>/dev/null | grep -q LISTEN && \
        ss -ltn "sport = :8000" 2>/dev/null | grep -q LISTEN && \
        ss -ltn "sport = :5173" 2>/dev/null | grep -q LISTEN && \
        command -v curl &>/dev/null && \
        adapter_is_healthy http://127.0.0.1:9101/health && \
        adapter_is_healthy http://127.0.0.1:9102/health && \
        curl --fail --silent --max-time 2 http://127.0.0.1:8000/health | grep -q '"status":"ok"' && \
        curl --fail --silent --max-time 2 --output /dev/null http://127.0.0.1:5173/; then
        is_base_healthy=true
    fi
    $is_base_healthy || return 1
    if [ "$RUNTIME_MODE" = "simulation" ]; then
        ss -ltn "sport = :9200" 2>/dev/null | grep -q LISTEN && \
            curl --fail --silent --max-time 2 --output /dev/null http://127.0.0.1:9200/
    fi
}

wait_for_stack() {
    local camera_group="$1"
    local motion_group="$2"
    local backend_group="$3"
    local frontend_group="$4"
    local console_group="${5:-}"
    local attempt

    for attempt in {1..60}; do
        if ! is_process_group_running "$camera_group" || \
           ! is_process_group_running "$motion_group" || \
           ! is_process_group_running "$backend_group" || \
           ! is_process_group_running "$frontend_group"; then
            return 1
        fi
        if [ "$RUNTIME_MODE" = "simulation" ] && ! is_process_group_running "$console_group"; then
            return 1
        fi

        if is_stack_healthy; then
            return 0
        fi
        sleep 0.5
    done

    return 1
}

show_status() {
    local -a process_groups
    mapfile -t process_groups < <(find_project_server_groups)

    if [ "${#process_groups[@]}" -eq 0 ]; then
        echo "AOI Studio is not running for this repository."
        return 1
    fi

    echo "AOI Studio process groups: ${process_groups[*]}"
    if is_stack_healthy; then
        echo "Status: healthy"
        echo "Frontend: http://127.0.0.1:5173/"
        echo "Backend health: http://127.0.0.1:8000/health"
        echo "Camera health: http://127.0.0.1:9101/health"
        echo "Motion health: http://127.0.0.1:9102/health"
        if [ "$RUNTIME_MODE" = "simulation" ]; then
            echo "Simulator console: http://127.0.0.1:9200/"
        fi
        return 0
    fi

    echo "Status: starting or unhealthy"
    return 1
}

ensure_port_is_available() {
    local port="$1"
    if ss -ltn "sport = :$port" 2>/dev/null | grep -q LISTEN; then
        echo "Error: port $port is already in use." >&2
        ss -ltnp "sport = :$port" 2>/dev/null >&2 || true
        echo "Stop the existing AOI process or close the application using that port, then try again." >&2
        return 1
    fi
}

write_pid_file() {
    local camera_group="$1"
    local motion_group="$2"
    local backend_group="$3"
    local frontend_group="$4"
    local console_group="${5:-}"
    local temporary_file="${PID_FILE}.$$"

    umask 077
    {
        printf 'SCRIPT_PID=%s\n' "$$"
        printf 'RUNTIME_MODE=%s\n' "$RUNTIME_MODE"
        printf 'CAMERA_PROCESS_GROUP=%s\n' "$camera_group"
        printf 'MOTION_PROCESS_GROUP=%s\n' "$motion_group"
        printf 'BACKEND_PROCESS_GROUP=%s\n' "$backend_group"
        printf 'FRONTEND_PROCESS_GROUP=%s\n' "$frontend_group"
        if [ -n "$console_group" ]; then
            printf 'CONSOLE_PROCESS_GROUP=%s\n' "$console_group"
        fi
        printf 'PROJECT_ROOT=%s\n' "$PROJECT_ROOT"
    } > "$temporary_file"
    mv -f "$temporary_file" "$PID_FILE"
}

cleanup() {
    local exit_code="${1:-0}"

    if [ "$CLEANUP_STARTED" = true ]; then
        return
    fi
    CLEANUP_STARTED=true
    trap - EXIT SIGINT SIGTERM SIGHUP

    if [ "$MANAGES_SERVERS" = true ]; then
        echo ""
        echo "Stopping servers..."
        stop_project_servers || true
        echo "Servers stopped."
    fi

    return "$exit_code"
}

print_header
cd "$PROJECT_ROOT"

case "$ACTION" in
    stop)
        if stop_project_servers; then
            echo "AOI Studio stopped."
        else
            echo "AOI Studio is not running for this repository."
        fi
        exit 0
        ;;
    status)
        read_runtime_mode
        show_status
        exit $?
        ;;
    start)
        ;;
    -h|--help|help)
        print_usage
        exit 0
        ;;
    *)
        echo "Error: unknown command '$ACTION'." >&2
        print_usage >&2
        exit 2
        ;;
esac

if [ "$RUNTIME_MODE" != "hardware" ] && [ "$RUNTIME_MODE" != "simulation" ]; then
    echo "Error: runtime mode must be 'hardware' or 'simulation'." >&2
    print_usage >&2
    exit 2
fi

read_runtime_mode
mapfile -t EXISTING_GROUPS < <(find_project_server_groups)
if [ "${#EXISTING_GROUPS[@]}" -gt 0 ] && is_stack_healthy; then
    echo "AOI Studio is already running."
    echo "Frontend: http://127.0.0.1:5173/"
    echo "Backend health: http://127.0.0.1:8000/health"
    if [ "$RUNTIME_MODE" = "simulation" ]; then
        echo "Simulator console: http://127.0.0.1:9200/"
    fi
    echo "Stop command: bash scripts/run_dev.sh stop"
    echo "No duplicate development servers were started."
    exit 0
fi

configure_linux_toolchain

# Ensure the Conda environment and frontend dependencies exist.
if ! command -v conda &>/dev/null || \
   ! conda env list | grep -q -E "^${CONDA_ENV_NAME}[[:space:]]" || \
   [ ! -d "frontend/node_modules" ]; then
    echo "Dependencies not installed. Running setup.sh first..."
    bash scripts/install/setup.sh
fi

ensure_port_is_available 8000
ensure_port_is_available 5173
ensure_port_is_available 9101
ensure_port_is_available 9102
if [ "$RUNTIME_MODE" = "simulation" ]; then
    ensure_port_is_available 9200
fi

# EXIT also covers startup failures and a terminal closing unexpectedly. Each
# service runs in its own session/process group so cleanup reaches reload workers.
trap 'exit 130' SIGINT
trap 'exit 143' SIGTERM
trap 'exit 129' SIGHUP
trap 'cleanup $?' EXIT

if [ "$RUNTIME_MODE" = "simulation" ]; then
    CAMERA_APP="simulator.camera.app:app"
    MOTION_APP="simulator.mcu.app:app"
else
    CAMERA_APP="hardware.camera.app:app"
    MOTION_APP="hardware.mcu.app:app"
fi

echo "Starting $RUNTIME_MODE camera adapter on http://127.0.0.1:9101..."
cd "$PROJECT_ROOT"
setsid env PYTHONPATH="$PROJECT_ROOT" conda run --no-capture-output -n "$CONDA_ENV_NAME" \
    python -m uvicorn "$CAMERA_APP" --host 127.0.0.1 --port 9101 &
CAMERA_PROCESS_GROUP=$!

echo "Starting $RUNTIME_MODE motion adapter on http://127.0.0.1:9102..."
setsid env PYTHONPATH="$PROJECT_ROOT" conda run --no-capture-output -n "$CONDA_ENV_NAME" \
    python -m uvicorn "$MOTION_APP" --host 127.0.0.1 --port 9102 &
MOTION_PROCESS_GROUP=$!

echo "Starting Backend API (FastAPI) on http://127.0.0.1:8000..."
cd "$PROJECT_ROOT/backend"
setsid env PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/backend" DEBUG_AUTO_LOGIN="$DEBUG_MODE" conda run --no-capture-output -n "$CONDA_ENV_NAME" \
    python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 &
BACKEND_PROCESS_GROUP=$!

echo "Starting Frontend Development Server (Vite)..."
cd "$PROJECT_ROOT/frontend"
if [ "$DEBUG_MODE" = true ]; then
    setsid env VITE_AOI_DEBUG_AUTO_LOGIN=1 npm run dev -- --strictPort &
else
    setsid npm run dev -- --strictPort &
fi
FRONTEND_PROCESS_GROUP=$!

CONSOLE_PROCESS_GROUP=""
if [ "$RUNTIME_MODE" = "simulation" ]; then
    echo "Starting Simulator Console on http://127.0.0.1:9200..."
    cd "$PROJECT_ROOT/simulator/console"
    setsid conda run --no-capture-output -n "$CONDA_ENV_NAME" python -m http.server 9200 --bind 127.0.0.1 &
    CONSOLE_PROCESS_GROUP=$!
fi

MANAGES_SERVERS=true
write_pid_file "$CAMERA_PROCESS_GROUP" "$MOTION_PROCESS_GROUP" "$BACKEND_PROCESS_GROUP" "$FRONTEND_PROCESS_GROUP" "$CONSOLE_PROCESS_GROUP"

if ! wait_for_stack "$CAMERA_PROCESS_GROUP" "$MOTION_PROCESS_GROUP" "$BACKEND_PROCESS_GROUP" "$FRONTEND_PROCESS_GROUP" "$CONSOLE_PROCESS_GROUP"; then
    echo "Error: one or more development servers failed to start." >&2
    exit 1
fi

echo "========================================="
echo "AOI Development environment running!"
echo "Runtime mode: $RUNTIME_MODE"
if [ "$DEBUG_MODE" = true ]; then
    echo "Debug auto-login: enabled"
fi
echo "Press Ctrl+C to stop all services."
echo "You can also run: bash scripts/run_dev.sh stop"
if [ "${AOI_SIMULATOR_NO_BROWSER:-0}" != "1" ]; then
    open_windows_browser "http://127.0.0.1:5173/"
    if [ "$RUNTIME_MODE" = "simulation" ]; then
        open_windows_browser "http://127.0.0.1:9200/"
    fi
fi
echo "========================================="

# Exit when either service terminates; the EXIT trap stops the remaining group.
set +e
if [ "$RUNTIME_MODE" = "simulation" ]; then
    wait -n "$CAMERA_PROCESS_GROUP" "$MOTION_PROCESS_GROUP" "$BACKEND_PROCESS_GROUP" "$FRONTEND_PROCESS_GROUP" "$CONSOLE_PROCESS_GROUP"
else
    wait -n "$CAMERA_PROCESS_GROUP" "$MOTION_PROCESS_GROUP" "$BACKEND_PROCESS_GROUP" "$FRONTEND_PROCESS_GROUP"
fi
SERVER_EXIT_CODE=$?
set -e

echo "A development server exited unexpectedly." >&2
if [ "$SERVER_EXIT_CODE" -eq 0 ]; then
    exit 1
fi
exit "$SERVER_EXIT_CODE"