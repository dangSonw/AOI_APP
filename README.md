# AOI Studio

AOI Studio is an industrial automated optical inspection web application. Current milestone provides persisted inspection orchestration plus industrial-pilot software foundations: commissioning/calibration lineage, durable integration outbox, bounded CSI/UART transport boundaries, and fail-closed backup/deployment acceptance. Real pilot acceptance remains blocked until factory contracts and target-hardware measurements are supplied.

## Implemented milestone

- Pixel-aligned sign-in UI from the connected Figma `AOI Studio` page, with single-Administrator sign-in and a password-reset demo state. Public account registration is disabled by default.
- Figma-aligned industrial workstation shell with Dashboard, Settings, Camera Manager, and Inspection Database views.
- Responsive desktop and mobile layouts with keyboard focus, validation, loading, success, error, and empty states.
- FastAPI authentication API with Argon2 password hashing and JWT bearer tokens.
- PostgreSQL 16 user storage and an idempotent schema setup.
- Protected physical I/O API backed by `io/input.json` and `io/output.json`.
- React mission-control dashboard that reads inputs and atomically writes output signals through the service layer.
- Interactive camera calibration, workstation preferences, inspection search, evidence selection, and CSV export demonstrations.
- Unit and integration tests for authentication, validation, record filtering, and physical I/O.
- Versioned camera and three-axis motion contracts shared by hardware and simulator adapters.
- Standalone virtual camera and MCU console with image-folder/webcam input, XYZ controls, interlocks, emergency stop, and fault injection.
- Authenticated backend device gateway with protocol validation, bounded timeouts, typed responses, normalized errors, and inspection-image SHA-256 verification.
- Inspection detail responses include persisted defect and image evidence instead of empty placeholder arrays.
- Camera and motion snapshots load independently, so one unavailable adapter does not hide the other adapter's usable state.
- Workstation preferences persist language, region, timezone, measurement system, and clock format; station profiles load explicitly before editing.
- Dataset service and API safety coverage includes validation, upload limits, magic bytes, traversal rejection, rename, move, delete, capture import, and ZIP export.
- PostgreSQL-backed audit events record authenticated and failed mutations without storing request bodies, credentials, bearer tokens, secrets, or image bytes.
- Persisted inspection runs pin workflow, node versions, verified artifacts, commissioning profile, calibration, station, work order, and immutable evidence.
- Industrial-pilot commissioning requires valid calibration; PLC/MES policies are typed and completed results enter an idempotent durable outbox.
- Deployment preflight refuses production-ready claims without measured target-hardware cycle time, false-call, escape, uptime, recovery, safety, integration, and restore evidence.

## Architecture

```text
React HMI :5173
        |
        | JSON / Bearer JWT
        v
FastAPI control plane :8000
   |          |                 |
   |          | HTTP loopback   `-- HTTP loopback --> Motion adapter :9102
   |          `--------------------> Camera adapter :9101
   |
   |-- PostgreSQL: users, inspections, audit events, versioned settings
   |-- data/projects: workflow recipes
   |-- data/preferences: legacy workstation preference migration input only
   `-- io/*.json: legacy physical I/O simulation

Hardware mode:   camera adapter -> Jetson CSI boundary
                 motion adapter -> MCU UART boundary
Simulation mode: camera adapter -> deterministic/uploaded PNG replay
                 motion adapter -> virtual XYZ state and safety interlocks
```

Frontend components render UI and call only the FastAPI control plane. The browser never needs direct access to ports `9101` or `9102`. FastAPI authenticates requests, validates device contracts, checks adapter protocol `1.0`, normalizes upstream errors, and proxies verified artifacts. Shared device contracts live under `core/devices`; hardware and simulator implementations remain interchangeable behind the same adapter boundary.

## Verified Ubuntu WSL environment

The implementation has been verified on Ubuntu 24.04.3 LTS under WSL with:

- Node.js 20.20.2 and npm 10.8.2
- Miniconda 26.5.3 with the `aoi-app` Python 3.12 environment
- PostgreSQL 16.14
- CodeGraph 1.5.0 running Linux-native inside WSL

### One-command system bootstrap

Do not invoke the shell scripts with the Windows `bash` command from PowerShell. That command may start Git Bash/Cygwin and select Windows Node.js or Conda. Enter Ubuntu WSL first:

```powershell
wsl.exe -d Ubuntu
```

Then, from the Ubuntu terminal, change to the repository and run this once on a new machine:

```bash
bash scripts/install/bootstrap-ubuntu.sh
```

The script installs system dependencies, Node.js 20, Miniconda, PostgreSQL, and CodeGraph, then runs the project setup. It requires `sudo` for operating-system packages.

### Project setup when prerequisites already exist

```bash
bash scripts/install/setup.sh
```

The setup script:

1. Creates the `aoi-app` Conda environment from conda-forge.
2. Installs backend and frontend dependencies.
3. Creates `.env` with random local credentials when it is missing.
4. Initializes the PostgreSQL role, database, and schema.
5. Verifies PostgreSQL, `.env` permissions, and physical I/O JSON.

Never commit `.env`. Commit only `.env.example` when configuration keys change.

## Run the application

From an Ubuntu WSL terminal:

```bash
bash scripts/run_dev.sh
```

The default mode starts hardware adapter boundaries and does not fall back to simulation. Until CSI and UART hardware implementations are available, run the complete stack explicitly in simulation mode:

```bash
bash scripts/run_dev.sh simulation
# Equivalent: bash scripts/run_dev.sh start --mode simulation
```

Simulation mode starts five managed processes: camera adapter, motion adapter, backend, frontend, and Simulator Console. It opens AOI Studio at `http://127.0.0.1:5173` and the commissioning console at `http://127.0.0.1:9200` in the Windows browser. Use `AOI_SIMULATOR_NO_BROWSER=1` for automation. `status` and `stop` include the console process.

For local simulation debugging, start the stack with a server-issued debug session:

```bash
bash scripts/run_dev.sh simulation debug
```

This development-only mode opens the dashboard without displaying the sign-in form. The backend resolves the configured seed operator from the untracked `.env`; no password is embedded in the frontend bundle, command line, README, or logs. The legacy command below is also accepted for compatibility and enables the same debug auto-login behavior:

```bash
VITE_AOI_SIMULATOR_NO_BROWSER=1 bash scripts/run_dev.sh simulation
```

To stop browsers from opening without enabling auto-login, use `AOI_SIMULATOR_NO_BROWSER=1` instead. Debug auto-login is unavailable outside the development environment and normal `simulation` or hardware startup continues to require sign-in.

Hardware mode starts the four production-boundary services without port `9200`. Disconnected CSI/UART adapters report `unavailable`; the launcher still starts the HMI in a diagnostic-safe state and never falls back to simulation.

From PowerShell while the current directory is this repository, use the portable WSL launcher instead:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-dev-wsl.ps1
```

Do not run `bash scripts/run_dev.sh` directly from PowerShell. The development scripts intentionally stop when they detect Git Bash, Cygwin, Windows Node.js, or Windows Conda.

If both AOI services are already healthy on their configured ports, the launcher reports that AOI Studio is already running and exits without starting duplicate processes. If only one port is occupied or a health check fails, inspect the listener printed by the launcher and stop that stale or unrelated process before retrying.

- Frontend: [http://127.0.0.1:5173](http://127.0.0.1:5173)
- Backend health: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- OpenAPI documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Camera adapter health: [http://127.0.0.1:9101/health](http://127.0.0.1:9101/health)
- Motion adapter health: [http://127.0.0.1:9102/health](http://127.0.0.1:9102/health)
- Simulator Console in simulation mode: [http://127.0.0.1:9200](http://127.0.0.1:9200)

Open the UI on port `5173`. Port `8000` is API-only, and its root currently returns `404`; the planned backend root redirect and favicon response are not implemented yet.

The local operator email is `operator@aoi.local`. Read `SEED_ADMIN_PASSWORD` from the untracked `.env` file for the local password. Backend startup creates the seed account only when it does not already exist. It does not update the password of an existing account, so changing `SEED_ADMIN_PASSWORD` alone does not rotate that account's stored password.

### Standalone device simulator

To exercise only the virtual hardware without PostgreSQL, login, or the main HMI:

```bash
bash scripts/run_simulator.sh
bash scripts/run_simulator.sh status
bash scripts/run_simulator.sh stop
```

This opens [http://127.0.0.1:9200](http://127.0.0.1:9200). The camera can replay a deterministic pattern, browser-selected image folders, or a Windows webcam frame. The MCU panel exposes home, XYZ jog, stop/reset, safety-door and communication interlocks, emergency stop, and deterministic fault injection. Simulation-only controls are not exposed through the production backend gateway.

### Hardware workspace and synchronized configuration

Open **Hardware** from AOI Studio's top navigation or Project Explorer. The page reads health, camera preview, camera configuration, motion profile, motion coordinates, interlocks, and faults through authenticated backend port `8000`. The browser never calls adapter ports directly.

Camera ID, sensor mode, exposure, gain, motion velocity, acceleration, and settle time use common `GET/PUT /configuration` resources implemented by both simulator and hardware adapters. The Hardware page and Simulator Console poll the same adapter state, so applied changes and motion positions synchronize in both directions. Unsaved form drafts are protected from polling updates.

Image source selection, webcam access, jog, virtual interlock mutation, reset, and fault injection remain simulator-only. Hardware mode shows actionable CSI/UART diagnostics and disables operational controls until adapters report `ready`; this keeps the HMI stable before physical devices are connected.

### Device adapter configuration

The backend reads trusted loopback adapter origins from `.env`:

```dotenv
CAMERA_ADAPTER_URL=http://127.0.0.1:9101
MOTION_ADAPTER_URL=http://127.0.0.1:9102
```

Only loopback HTTP origins with explicit ports are accepted. Device URLs never come from browser requests, preventing the gateway from becoming an arbitrary network proxy.

### Sign-in troubleshooting

AOI Studio currently operates in single-Administrator mode. The bootstrap account is created from `SEED_ADMIN_EMAIL`, `SEED_ADMIN_FULL_NAME`, and `SEED_ADMIN_PASSWORD`; defaults identify it as `AOI Administrator`. `POST /api/auth/register` returns HTTP `403` unless `ALLOW_PUBLIC_REGISTRATION=true` is set explicitly. Keep registration disabled for the approved baseline.

If the sign-in form displays `The AOI service is unavailable. Check the backend connection.`, the browser could not complete the API request. This is a service-availability, network, CORS, or frontend API configuration issue rather than an invalid-password response.

1. Start the application with one of the supported launchers above.
2. Check the backend directly:

   ```bash
   curl http://127.0.0.1:8000/health
   ```

   A ready backend returns JSON containing `"status":"ok"`.
3. Confirm the frontend is using the expected API base URL. It reads `VITE_API_BASE_URL` from the repository `.env` and defaults to `http://127.0.0.1:8000`.
4. If the backend is reachable but rejects the credentials, it returns HTTP `401` with `The email or password is incorrect.` An inactive account returns HTTP `403`.

The default CORS origin is `http://127.0.0.1:5173`. In development, its matching `http://localhost:5173` loopback alias is also accepted so either local URL can call the API. Other origins remain rejected; keep `FRONTEND_ORIGIN` aligned with the deployed browser origin outside development. Never paste secret values from `.env` into logs, issues, or documentation.

## Test and build

```bash
bash scripts/test/test.sh
bash scripts/build/build.sh
```

The latest complete run passed 134 Python tests across backend, core, integration, adapter contract, and simulator suites; all 31 frontend tests and TypeScript checking also passed.

Direct frontend commands are also available:

```bash
cd frontend
npm run typecheck
npm run test
npm run build
npm audit
```

## Physical I/O simulation

- `io/input.json` represents signals written by equipment or sensors outside the web application. The web application treats it as read-only.
- `io/output.json` represents actuator or control signals written by the web application.
- Every state contains a monotonic `revision` and UTC `updatedAt` timestamp.
- Output writes use a temporary file and atomic replacement to prevent partial JSON state.
- Both I/O endpoints require a valid bearer token.

The current JSON interface is a simulation boundary. A future hardware adapter can replace the file service without moving hardware logic into the frontend.

## API milestone

| Method | Path | Purpose | Authentication |
|---|---|---|---|
| `GET` | `/health` | Service health | No |
| `POST` | `/api/auth/login` | Sign in | No |
| `POST` | `/api/auth/register` | Public registration endpoint; disabled by default | No |
| `POST` | `/api/auth/password-reset` | Return a non-enumerating reset response | No |
| `GET` | `/api/io/inputs` | Read simulated inputs | Bearer token |
| `GET` | `/api/io/outputs` | Read simulated outputs | Bearer token |
| `PUT` | `/api/io/outputs` | Atomically update outputs | Bearer token |
| `GET` | `/api/algorithms` | Read the algorithm catalog and node runtime status | Bearer token |
| `GET` | `/api/recipes/{recipeSlug}/workflow` | Read a persisted or default recipe workflow | Bearer token |
| `PUT` | `/api/recipes/{recipeSlug}/workflow` | Validate and atomically save a complete workflow | Bearer token |
| `GET` | `/api/workstation-preferences/{workstationId}` | Read dashboard and Photometric preferences | Bearer token |
| `PUT` | `/api/workstation-preferences/{workstationId}` | Validate and atomically save workstation preferences | Bearer token |
| `GET` | `/api/devices` | Read camera and motion adapter health together | Bearer token |
| `GET` | `/api/camera/health` | Read camera implementation, mode, readiness, and protocol | Bearer token |
| `GET` | `/api/camera/capabilities` | Read camera IDs, sensor modes, limits, and media types | Bearer token |
| `POST` | `/api/camera/captures` | Create an idempotent capture and verify its artifact | Bearer token |
| `GET` | `/api/camera/captures/{captureId}/inspection-image` | Proxy a bounded inspection image with SHA-256 header | Bearer token |
| `GET` | `/api/motion/health` | Read motion implementation, mode, readiness, and protocol | Bearer token |
| `GET` | `/api/motion/capabilities` | Read axes, workspace, homing, and event support | Bearer token |
| `GET` | `/api/motion/state` | Read homing, XYZ pose, interlocks, and fault state | Bearer token |
| `POST` | `/api/motion/commands/home` | Submit an idempotent home command | Bearer token |
| `POST` | `/api/motion/commands/move-absolute` | Submit a bounded idempotent absolute move | Bearer token |
| `POST` | `/api/motion/commands/stop` | Stop active virtual or hardware motion | Bearer token |
| `POST` | `/api/motion/commands/clear-fault` | Clear a motion fault after interlocks are safe | Bearer token |

Password-reset email delivery is intentionally not implemented in this milestone. The endpoint returns the same safe message whether an account exists or not.

## Device gateway behavior and current limits

- Every typed device operation checks adapter protocol compatibility and readiness before forwarding a request.
- Connection failures become HTTP `503`, timeouts become `504`, invalid upstream contracts become `502`, and safe adapter `4xx` errors retain their status.
- A camera capture is accepted only after the backend downloads the lossless PNG/TIFF artifact, enforces a 64 MiB limit, verifies media type and byte length, and compares SHA-256 with capture metadata.
- Hardware mode never silently falls back to simulation. The current hardware camera and MCU adapters expose health/version/capabilities but intentionally report `unavailable`; Jetson CSI capture and UART transport remain future hardware-commissioning tasks.
- The simulator MCU currently completes home and move commands deterministically rather than reproducing a real acceleration timeline. The next inspection-runtime milestone must add persisted run orchestration and confirm in-position state before capture.
- The 58 workflow nodes remain configuration-only runtime placeholders. This gateway enables device communication but does not yet execute the AOI vision workflow or persist inspection results.

## Foundation repair behavior

- Inspection detail and create responses use the same response builder and return stored defects and image metadata.
- Camera and motion readiness are evaluated independently. An unavailable camera leaves motion state usable, and unavailable motion leaves camera configuration usable.
- Settings locale controls are part of `WorkstationPreferences`; every visible locale value participates in dirty detection and round-trips through persistence.
- Workstation ID entry selects a destination profile. `Load station profile` reads destination state before replacing saved and draft state, and Camera Manager displays the loaded workstation ID as read-only.
- Dataset operations reject unsafe names, traversal, invalid image magic bytes, files over 50 MiB, and batches over 100 files. Backend and authenticated API tests cover lifecycle, capture import, duplicate naming, and ZIP paths.
- `POST`, `PUT`, `PATCH`, and `DELETE` requests receive an `X-Request-ID` and durable audit metadata. A verified bearer JWT supplies actor ID; failed mutations are recorded as failures. Audit persistence errors are logged without replacing the original API response.
- `GET /api/audit-events` requires authentication and provides newest-first pagination with page size limited to 100.

## PostgreSQL settings platform

- Alembic owns schema evolution. Startup verifies migration head and refuses stale or unversioned databases.
- Run `PYTHONPATH=backend conda run -n aoi-app python -m app.database.migrations upgrade` after installing a release. Existing pre-Alembic databases use `baseline-existing` once; it verifies the complete baseline before stamping.
- PostgreSQL is the workstation-preference source of truth. Run `scripts/database/migrate-preferences.py --actor-id 1` as a dry-run, then repeat with `--apply` after reviewing conflicts.
- `/api/v1/settings` provides validation, immutable versions, expected-revision conflicts, history, source-linked rollback, portable interchange, and idempotent metadata activation.
- Activation requires `Idempotency-Key`. Exact replay returns the original activation; changed reuse returns `409` without moving the active pointer.
- Export with `scripts/database/export-settings.py --output data/reports/settings-export.json`; verify with `scripts/database/verify-settings-export.py data/reports/settings-export.json`. Portable JSON has SHA-256 integrity but does not replace PostgreSQL-native backup.
- In WSL, use Linux Node for GitNexus. A Windows npm shim can produce `invalid ELF header`; sanitize `PATH` and set `GITNEXUS_INVOCATION=npx` when needed.

## Workflow editor and storage

- The Workflow editor is available from the Dashboard Inspection flow settings action and the Project explorer Workflow item.
- `core/algorithms` owns the ordered catalog, typed ports, and parameter definitions.
- `core/nodes/<category>/<node-id>/node.py` provides one runtime contract per catalog item, including input keys, output keys, an `execute` entry point, and a `test`, `debug`, or `release` status.
- `core/pipeline` owns workflow validation, stable topological ordering, and typed DAG execution. Connections require exact type equality, and cycles, self-loops, duplicate connections, missing required inputs, and invalid execution order are rejected.
- Recipe workflows are AOI-owned camelCase JSON documents stored under `data/projects/<recipe-slug>/workflow.json`. React Flow presentation objects are never persisted.
- Successful saves require the submitted revision to match storage, increment the revision once, and use a sibling temporary file, flush, `fsync`, and atomic replacement. A stale save returns HTTP `409` without overwriting the newer file.
- The catalog contains 63 node packages. Thirty-three `debug` runtimes execute acquisition handoff, decision handling, 24 OpenCV tools, mask scoring, visualization, bounded delay, and bounded image-set repeat. Thirty `test` runtimes remain explicit placeholders for algorithms requiring calibration artifacts, reference datasets, model weights, training, or inference support.
- Project **Run** captures a verified image, executes the saved workflow snapshot in deterministic DAG order, persists one evidence record per node, stores original and workflow-preview artifacts, and exposes the checksum-verified preview to the authenticated 2D optical view. Workflows containing a placeholder node fault at that node; no silent fallback occurs.
- Every node package contains `README.md` and `README.md.vn` generated from its manifest by `python scripts/generate_node_docs.py`.
- Local recipe workflow files are runtime data and are ignored by Git; `data/projects/.gitkeep` preserves the directory structure.

## Repository documentation convention

- Keep operational documentation in the root `README.md` and `README.md.vn`, script documentation in `scripts/README.md` and `scripts/README.md.vn`, and topic-specific documents under `docs/`.
- Do not create directories named `README.md` or add repeated placeholder README files to reserve future modules.
- Add a functional directory only when it contains source, configuration, tests, or maintained documentation. Runtime directories that must exist in a fresh clone use a scoped `.gitkeep` and matching ignore rules instead.

## Figma and CodeGraph workflow

The connected Figma file is `AOI`, page `AOI Studio`. The implemented references are the authentication frame `41:991`, Dashboard `36:849`, Settings `36:1176`, Camera Manager `36:1569`, and Database `36:1632`. The implementation preserves the industrial hierarchy, proportions, spacing, colors, and typography with responsive Grid and Flexbox flow instead of Figma screen coordinates. All implemented workspaces have been checked at 390, 768, 1280, and 1920 pixel viewport widths without document-level horizontal overflow.

Use Linux-native CodeGraph from the repository root:

```bash
codegraph sync .
codegraph status .
codegraph explore AuthPage WorkspacePage DashboardPage physical_io
```

Do not index this WSL repository with Windows Node over a UNC path because SQLite locking is unreliable in that configuration.
