# AOI Studio

AOI Studio is an industrial automated optical inspection web application. The current milestone implements the Figma-authored authentication experience and industrial workstation shell, PostgreSQL-backed user accounts, and a file-backed physical I/O simulation workspace.

## Implemented milestone

- Pixel-aligned sign-in UI from the connected Figma `AOI Studio` page, including sign-up and password-reset demo states.
- Figma-aligned industrial workstation shell with Dashboard, Settings, Camera Manager, and Inspection Database views.
- Responsive desktop and mobile layouts with keyboard focus, validation, loading, success, error, and empty states.
- FastAPI authentication API with Argon2 password hashing and JWT bearer tokens.
- PostgreSQL 16 user storage and an idempotent schema setup.
- Protected physical I/O API backed by `io/input.json` and `io/output.json`.
- React mission-control dashboard that reads inputs and atomically writes output signals through the service layer.
- Interactive camera calibration, workstation preferences, inspection search, evidence selection, and CSV export demonstrations.
- Unit and integration tests for authentication, validation, record filtering, and physical I/O.

## Architecture

```text
React + TypeScript + Vite
        |
        | JSON / Bearer JWT
        v
FastAPI API
   |             |
   v             v
PostgreSQL    io/*.json
users         physical state simulation
```

Frontend components render UI and call services only. FastAPI validates requests and coordinates authentication or I/O services. SQLAlchemy owns persistence models, while physical I/O file operations are isolated in a backend service.

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

From PowerShell while the current directory is this repository, use the portable WSL launcher instead:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-dev-wsl.ps1
```

Do not run `bash scripts/run_dev.sh` directly from PowerShell. The development scripts intentionally stop when they detect Git Bash, Cygwin, Windows Node.js, or Windows Conda.

If both AOI services are already healthy on their configured ports, the launcher reports that AOI Studio is already running and exits without starting duplicate processes. If only one port is occupied or a health check fails, inspect the listener printed by the launcher and stop that stale or unrelated process before retrying.

- Frontend: [http://127.0.0.1:5173](http://127.0.0.1:5173)
- Backend health: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- OpenAPI documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Open the UI on port `5173`. Port `8000` is API-only, and its root currently returns `404`; the planned backend root redirect and favicon response are not implemented yet.

The local operator email is `operator@aoi.local`. Read `SEED_ADMIN_PASSWORD` from the untracked `.env` file for the local password. Backend startup creates the seed account only when it does not already exist. It does not update the password of an existing account, so changing `SEED_ADMIN_PASSWORD` alone does not rotate that account's stored password.

### Sign-in troubleshooting

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

The latest complete test run passed 15 backend tests, 14 core tests, 12 integration tests, 11 frontend tests, and TypeScript checking.

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
| `POST` | `/api/auth/register` | Create an account | No |
| `POST` | `/api/auth/password-reset` | Return a non-enumerating reset response | No |
| `GET` | `/api/io/inputs` | Read simulated inputs | Bearer token |
| `GET` | `/api/io/outputs` | Read simulated outputs | Bearer token |
| `PUT` | `/api/io/outputs` | Atomically update outputs | Bearer token |
| `GET` | `/api/algorithms` | Read the algorithm catalog and node runtime status | Bearer token |
| `GET` | `/api/recipes/{recipeSlug}/workflow` | Read a persisted or default recipe workflow | Bearer token |
| `PUT` | `/api/recipes/{recipeSlug}/workflow` | Validate and atomically save a complete workflow | Bearer token |
| `GET` | `/api/workstation-preferences/{workstationId}` | Read dashboard and Photometric preferences | Bearer token |
| `PUT` | `/api/workstation-preferences/{workstationId}` | Validate and atomically save workstation preferences | Bearer token |

Password-reset email delivery is intentionally not implemented in this milestone. The endpoint returns the same safe message whether an account exists or not.

## Workflow editor and storage

- The Workflow editor is available from the Dashboard Inspection flow settings action and the Project explorer Workflow item.
- `core/algorithms` owns the ordered catalog, typed ports, and parameter definitions.
- `core/nodes/<category>/<node-id>/node.py` provides one runtime contract per catalog item, including input keys, output keys, an `execute` entry point, and a `test`, `debug`, or `release` status.
- `core/pipeline` owns workflow validation and stable topological ordering. Connections require exact type equality, and cycles, self-loops, duplicate connections, missing required inputs, and invalid execution order are rejected.
- Recipe workflows are AOI-owned camelCase JSON documents stored under `data/projects/<recipe-slug>/workflow.json`. React Flow presentation objects are never persisted.
- Successful saves require the submitted revision to match storage, increment the revision once, and use a sibling temporary file, flush, `fsync`, and atomic replacement. A stale save returns HTTP `409` without overwriting the newer file.
- The current node modules are explicit runtime placeholders: their contracts are loadable, but their algorithm bodies raise a structured not-implemented error. They do not install or run OpenCV, PyTorch, Anomalib, model weights, training, or inference yet.
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
