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
Launches both the FastAPI backend and Vite frontend development servers concurrently. Pressing `Ctrl+C` or closing the controlling terminal will clean up the complete process groups, including Uvicorn reload workers and the Vite child process.
If both services are already healthy, the script reports the existing stack and exits successfully instead of starting duplicate servers. Partial or unrelated port conflicts remain errors and include listener details.

**Ubuntu WSL terminal:**
```bash
bash scripts/run_dev.sh
```

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

### 3. Project Build (`scripts/build/build.sh`)
Builds the production-ready assets for the frontend (compiled to `frontend/dist`) and compiles C++ native core libraries (if CMake is installed) under `core/native/build`.

**Usage:**
```bash
bash scripts/build/build.sh
```

### 4. Test Runner (`scripts/test/test.sh`)
Runs tests sequentially for different layers:
- Backend tests under `tests/backend/` using `pytest`.
- Core logic tests under `tests/core/` using `pytest`.
- Integration tests under `tests/integration/` using `pytest`.
- Frontend linting, type-checking, or tests inside `frontend/`.

**Usage:**
```bash
bash scripts/test/test.sh
```

### 5. Production Readiness Check (`scripts/deploy/deploy.sh`)
Validates that production build assets exist and provides information for running the servers in a production environment behind a reverse proxy.

**Usage:**
```bash
bash scripts/deploy/deploy.sh
```

### 6. Release Packager (`scripts/release/release.sh`)
Runs a clean build and bundles the production assets into a `.tar.gz` package located in the `release/` directory. Unnecessary development folders (such as `.venv` or `__pycache__`) are excluded from the archive.

**Usage:**
```bash
bash scripts/release/release.sh
```

---

## Important Rules for Writing Scripts
1. **Always Use Relative Paths**: Never hardcode absolute paths (e.g. `/home/user/...` or `C:\Users\...`). Resolve directories using relative paths dynamically (e.g. `$(dirname "${BASH_SOURCE[0]}")`).
2. **Handle Dependencies Safely**: Make scripts self-contained. If a script depends on another state (like `setup.sh`), it should check for the state or prompt the user.
3. **Protect Secrets**: Never print or commit values from `.env`. Commit `.env.example` only.
4. **Execute Permissions**: Make sure scripts have executable permissions:
   ```bash
   chmod +x scripts/run_dev.sh scripts/install/*.sh scripts/utils/*.sh scripts/build/build.sh scripts/test/test.sh scripts/deploy/deploy.sh scripts/release/release.sh
   ```
