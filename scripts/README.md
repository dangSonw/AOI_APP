# AOI System Scripts Directory

This directory contains automation scripts to set up, build, test, deploy, and release the AOI System application.

## Prerequisites

The application scripts are designed to run inside Ubuntu or Ubuntu WSL. Windows Git Bash and Cygwin are not supported because they can mix Windows and Linux Node.js, npm, and Conda executables.
Make sure you have the following installed on your system:
- **Conda** (Miniconda or Anaconda)
- **NodeJS** and **npm**
- **CMake** (optional, required to build C++ native modules)

On Ubuntu WSL, install and verify all required tools with:

```bash
bash scripts/install/bootstrap-ubuntu.sh
```

## Script Catalog

All scripts are written using relative paths, allowing them to work correctly regardless of where the repository is cloned.

### 1. Installation Setup (`scripts/install/setup.sh`)
Sets up the development environment by creating the `aoi-app` Python environment from conda-forge, installing packages, generating secure local configuration, initializing PostgreSQL, and verifying physical I/O JSON.

**Usage:**
```bash
bash scripts/install/setup.sh
```

Supporting installation scripts:

- `scripts/install/bootstrap-ubuntu.sh`: installs Ubuntu system dependencies, Node.js 20, Miniconda, PostgreSQL, and Linux-native CodeGraph.
- `scripts/install/create-local-env.sh`: creates an untracked `.env` with random local credentials and permission `600`.
- `scripts/install/setup-postgresql.sh`: creates or updates the application role, database, and schema.
- `scripts/install/verify-environment.sh`: verifies the service, schema, configuration permissions, and JSON files.

### 2. Development Run (`scripts/run_dev.sh`)
Launches camera and motion adapters, the FastAPI backend, and the Vite frontend concurrently. Explicit simulation mode also starts the commissioning console on port `9200` and opens both browser tabs. Pressing `Ctrl+C` or closing the controlling terminal cleans up all owned process groups, including Uvicorn reload workers, the Vite child process, and the console.
If the complete mode-specific stack is already healthy, the script reports the existing stack and exits successfully instead of starting duplicate servers. Hardware adapters may report `unavailable` while disconnected without preventing the HMI from starting in diagnostic mode; no simulator fallback occurs. Partial or unrelated port conflicts remain errors and include listener details.

**Ubuntu WSL terminal:**
```bash
bash scripts/run_dev.sh
bash scripts/run_dev.sh simulation
```

Set `AOI_SIMULATOR_NO_BROWSER=1` when simulation mode is used by automation and must not open browser tabs.

Stop a stack that is already running, including one left behind by an older terminal session:

```bash
bash scripts/run_dev.sh stop
```

Check its state without starting new processes:

```bash
bash scripts/run_dev.sh status
```

The stop command verifies both the command line and repository working directory before signaling a process group, so it does not intentionally terminate an unrelated Vite or Uvicorn project.

**PowerShell from the repository directory:**
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-dev-wsl.ps1
```

Do not use `bash scripts/run_dev.sh` directly in PowerShell. The Windows `bash` executable is not the Ubuntu WSL runtime.
- Backend will run at: [http://127.0.0.1:8000](http://127.0.0.1:8000) (with automatic reloading)
- Frontend dev server will start (check terminal output for the Vite port)
- Frontend runs at: [http://127.0.0.1:5173](http://127.0.0.1:5173)

### 3. Standalone Simulator Console (`scripts/run_simulator.sh`)

Starts only the virtual camera, virtual motion controller, and a local commissioning console. It does not require AOI Studio login or PostgreSQL. The default start command opens the Windows browser at [http://127.0.0.1:9200](http://127.0.0.1:9200).

```bash
bash scripts/run_simulator.sh
bash scripts/run_simulator.sh status
bash scripts/run_simulator.sh stop
```

The camera panel supports a deterministic test pattern, browser-selected image folders, and a Windows webcam captured through browser permission. Folder and webcam frames are converted to PNG in the browser and copied into simulator-managed storage; Windows absolute paths are never persisted. The motion panel supports homing, XYZ jogging, stop/reset, door and communication interlocks, emergency stop, and deterministic fault injection.

For automated checks that must not open a browser tab:

```bash
AOI_SIMULATOR_NO_BROWSER=1 bash scripts/run_simulator.sh
```

Uploaded source images are limited to 16 MiB each. The browser may read JPEG, PNG, WebP, or BMP sources, but normalizes simulator input to lossless PNG. Webcam access requires granting camera permission to the loopback page in Chrome or Edge.

### 4. Project Build (`scripts/build/build.sh`)
Builds the production-ready assets for the frontend (compiled to `frontend/dist`) and compiles C++ native core libraries (if CMake is installed) under `core/native/build`.

**Usage:**
```bash
bash scripts/build/build.sh
```

### 5. Test Runner (`scripts/test/test.sh`)
Runs tests sequentially for different layers:
- Backend tests under `tests/backend/` using `pytest`.
- Core logic tests under `tests/core/` using `pytest`.
- Integration tests under `tests/integration/` using `pytest`.
- Shared adapter contract tests under `tests/contract/` using `pytest`.
- Camera, motion, and console tests under `tests/simulator/` using `pytest`.
- Frontend linting, type-checking, or tests inside `frontend/`.

**Usage:**
```bash
bash scripts/test/test.sh
```

### 6. Production Readiness Check (`scripts/deploy/deploy.sh`)
Validates that production build assets exist and provides information for running the servers in a production environment behind a reverse proxy.

**Usage:**
```bash
bash scripts/deploy/deploy.sh
```

### 7. Release Packager (`scripts/release/release.sh`)
Runs a clean build and bundles the production assets into a `.tar.gz` package located in the `release/` directory. Unnecessary development folders (such as `.venv` or `__pycache__`) are excluded from the archive.

**Usage:**
```bash
bash scripts/release/release.sh
```

### 8. Pilot Operations (`scripts/operations/`)

Create a PostgreSQL custom-format dump, artifact archive, and checksum manifest:

```bash
PYTHONPATH=.:backend conda run -n aoi-app python scripts/operations/pilot-backup.py --output data/backups/pilot-001
```

Verify all checksums and inspect the PostgreSQL restore catalog without writing a database:

```bash
PYTHONPATH=.:backend conda run -n aoi-app python scripts/operations/pilot-restore-dry-run.py data/backups/pilot-001
```

`scripts/deploy/deploy.sh` now fails closed unless `AOI_PILOT_ACCEPTANCE_REPORT` points to a typed,
measured target-hardware report with every safety/recovery gate passed. Simulator evidence cannot satisfy it.

---

## Important Rules for Writing Scripts
1. **Always Use Relative Paths**: Never hardcode absolute paths (e.g. `/home/user/...` or `C:\Users\...`). Resolve directories using relative paths dynamically (e.g. `$(dirname "${BASH_SOURCE[0]}")`).
2. **Handle Dependencies Safely**: Make scripts self-contained. If a script depends on another state (like `setup.sh`), it should check for the state or prompt the user.
3. **Protect Secrets**: Never print or commit values from `.env`. Commit `.env.example` only.
4. **Execute Permissions**: Make sure scripts have executable permissions:
   ```bash
   chmod +x scripts/run_dev.sh scripts/run_simulator.sh scripts/install/*.sh scripts/utils/*.sh scripts/build/build.sh scripts/test/test.sh scripts/deploy/deploy.sh scripts/release/release.sh
   ```
