# AOI System Scripts Directory

This directory contains automation scripts to set up, build, test, deploy, and release the AOI System application.

## Prerequisites

The scripts are designed to run in a POSIX-compliant environment (Linux, macOS, or Windows Subsystem for Linux - WSL).
Make sure you have the following installed on your system:
- **Conda** (Miniconda or Anaconda)
- **NodeJS** and **npm**
- **CMake** (optional, required to build C++ native modules)

## Script Catalog

All scripts are written using relative paths, allowing them to work correctly regardless of where the repository is cloned.

### 1. Installation Setup (`scripts/install/setup.sh`)
Sets up the development environment by verifying dependencies, creating a Python environment under Conda named `aoi-app`, installing backend packages, running `npm install` in the frontend, and creating required directories in `data/`.

**Usage:**
```bash
bash scripts/install/setup.sh
```

### 2. Development Run (`scripts/run_dev.sh`)
Launches both the FastAPI backend and Vite frontend development servers concurrently. Pressing `Ctrl+C` will clean up and terminate both processes.

**Usage:**
```bash
bash scripts/run_dev.sh
```
- Backend will run at: [http://127.0.0.1:8000](http://127.0.0.1:8000) (with automatic reloading)
- Frontend dev server will start (check terminal output for the Vite port)

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
3. **Execute Permissions**: Make sure scripts have executable permissions:
   ```bash
   chmod +x scripts/run_dev.sh scripts/install/setup.sh scripts/build/build.sh scripts/test/test.sh scripts/deploy/deploy.sh scripts/release/release.sh
   ```
