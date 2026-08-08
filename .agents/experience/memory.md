# AOI Studio AI Developer Memory

## 1. Context
During the initial setup of the AOI System project, standard Python virtual environments (`venv`) created within WSL mapping caused Windows git client indexing errors during `git add .` due to symlink compatibility issues. In addition, the developer requested environment management using Anaconda/Miniconda to ensure cross-platform compatibility between Windows and Ubuntu.

## 2. Issues Encountered & Resolved
- **Git Indexing Failure:** Sourcing and committing absolute/virtual environments causes file-not-found errors on hosts.
  * *Resolution:* Excluded all `.venv/` and `.conda/` temporary paths in `.gitignore`.
- **Absolute Paths in Build files:** An absolute path `/include` was configured in `core/native/CMakeLists.txt`.
  * *Resolution:* Replaced with `${CMAKE_CURRENT_SOURCE_DIR}/include`.
- **Environment Incompatibility:** Python standard `venv` has symlink differences between WSL and Windows.
  * *Resolution:* Refactored setup, build, test, and run scripts to utilize Conda environment management under a unified environment name `aoi-app` using `conda run -n aoi-app`.

## 3. Key Rules Added
- **Relative Path Constraint:** Absolute paths (e.g. `/home/...`, `C:\...`) are forbidden to maintain project portability.
- **Vietnamese Companion Constraint:** Every `.md` documentation file created or updated must contain a companion `.md.vn` translation in Vietnamese.
- **AI Experience Memory:** Critical notes or bugs must be documented inside `.agents/experience/` as `memory.md` and `memory.md.vn`.

## 4. Ubuntu WSL Authentication Milestone Notes

- **CodeGraph SQLite locking:** Running the Windows CodeGraph executable against the repository through a WSL UNC path repeatedly returned `database is locked`, even after deleting the cache. Install and run CodeGraph with Linux Node from inside Ubuntu, then index the Linux repository path.
- **Conda channel terms:** Miniconda 26 requires explicit Terms of Service acceptance for default Anaconda channels in non-interactive setup. The project creates `aoi-app` with `--override-channels --channel conda-forge` so automation does not accept legal terms on the developer's behalf.
- **Conda executable leakage:** A standalone `pip` resolved through `conda run` can unexpectedly use the base Conda interpreter, which caused Python 3.14 to reject pinned wheels intended for the project's Python 3.12 environment. Invoke Python tooling as `conda run -n aoi-app python -m pip`, `python -m pytest`, or `python -m uvicorn`. Setup validates Python 3.12 and installs `pip` inside the target environment.
- **Vite JSON parsing:** The original frontend JSON files contained a UTF-8 BOM. TypeScript and npm tolerated it, but Vite's PostCSS config discovery failed. Keep `package.json` and `tsconfig.json` UTF-8 without BOM.
- **Internal work email:** Pydantic `EmailStr` rejects the reserved `.local` domain used by the Figma seed account. Authentication uses a bounded structural work-email validator to support industrial local domains while still rejecting malformed addresses.
- **Physical outputs:** Write `io/output.json` through a temporary file followed by atomic replacement. Never write hardware simulation state directly from React.

## 5. PowerShell and Responsive Layout Notes

- **Wrong Bash runtime:** Running `bash scripts/run_dev.sh` from PowerShell on a WSL UNC working directory can invoke Git Bash/Cygwin. This selects Windows npm and Conda, produces `/cygdrive` interpreter errors, and cannot access the Linux Conda environment. Use the PowerShell WSL launcher or enter Ubuntu with `wsl.exe -d Ubuntu` first.
- **Fail-fast startup:** `run_dev.sh` must use strict shell error handling. If automatic setup fails, the script must exit before starting either server.
- **Development process cleanup:** Killing only the `conda run` and `npm` wrapper PIDs can leave Uvicorn reload workers or Vite children listening after `Ctrl+C` or terminal closure. Start each service in its own process group, trap `EXIT`, `SIGINT`, `SIGTERM`, and `SIGHUP`, and use `bash scripts/run_dev.sh stop` to terminate a stack left by an earlier session. Stop discovery must validate both the command and repository working directory to avoid affecting another project.
- **PowerShell provider paths:** `Resolve-Path(...).Path` can include the `Microsoft.PowerShell.Core\\FileSystem::` provider prefix for WSL UNC locations. Use `Get-Item(...).FullName` before converting the UNC path to a Linux path.
- **Responsive Figma implementation:** Figma coordinates are not CSS coordinates. Place application components in normal Grid/Flexbox flow, keep validation messages in flow, and verify horizontal overflow across mobile, tablet, and desktop viewports.

## 6. Verified Local Environment

- **Operating system:** Ubuntu 24.04 LTS under WSL with `systemd` enabled.
- **JavaScript toolchain:** Linux Node.js 20.20.2 and npm 10.8.2. Vite 8 requires Node.js 20 or newer.
- **Python toolchain:** Miniconda 26.5.3 with the `aoi-app` Python 3.12 environment.
- **Database:** PostgreSQL 16 runs as a system service and listens locally on port `5432`.
- **Code intelligence:** CodeGraph 1.5.0 must resolve to the Linux executable before any Windows executable inherited through WSL interop. The latest synchronized index contains 31 source files, 232 nodes, and 467 edges.
- **Frontend security audit:** The synchronized Vite and Vitest toolchain reports zero npm vulnerabilities at this milestone.

## 7. Development Runbook

- **PowerShell entry point:** From the repository directory, run `powershell -ExecutionPolicy Bypass -File .\scripts\run-dev-wsl.ps1`. The launcher derives the WSL distribution and Linux repository path from its own location.
- **Ubuntu entry point:** Enter Ubuntu with `wsl.exe -d Ubuntu`, change to the repository, then run `bash scripts/run_dev.sh`.
- **Unsupported command:** Do not run `bash scripts/run_dev.sh` directly in PowerShell. The runtime guard intentionally exits with code `1` when Git Bash or Cygwin is detected.
- **Linux tool guard:** Application scripts reject Node.js, npm, or Conda executables resolved from `/mnt` and place a user-local Linux Miniconda installation before inherited Windows paths.
- **Deterministic ports:** FastAPI uses `8000`, Vite uses `5173` with strict-port mode, and PostgreSQL uses `5432`. Startup must fail with a clear message when an application port is already occupied; Vite must not silently switch ports.
- **Existing healthy stack:** If both application ports are occupied and the AOI backend health check plus frontend request succeed, `run_dev.sh` reports that AOI Studio is already running and exits successfully without creating duplicate processes. A partial or unrelated listener remains an error and is displayed for diagnosis.
- **UI and API boundary:** Open the application at `http://127.0.0.1:5173/`. Port `8000` serves the API only; use `/health` for readiness and `/docs` for OpenAPI. The backend root currently returns `404` because the planned root redirect and favicon response are not implemented.
- **Startup timing:** A reloading Uvicorn process may announce its listener before Windows localhost forwarding is immediately ready. Confirm application startup from the Uvicorn log or retry the health request after a short delay.
- **Shutdown:** `Ctrl+C` should terminate both application servers. PostgreSQL remains active as a system service.

## 8. Configuration, Database, and Physical I/O

- **Local configuration:** `.env` is untracked, generated with random local credentials, and must retain permission `600`. `.env.example` contains placeholders only.
- **Secrets:** Never print, document, or commit `POSTGRES_PASSWORD`, `JWT_SECRET_KEY`, or `SEED_ADMIN_PASSWORD` values.
- **PostgreSQL setup:** `scripts/install/setup-postgresql.sh` is idempotent and creates or updates the application role, database, and `users` schema.
- **Seed operator:** The local operator email is `operator@aoi.local`; its password is read only from the untracked environment file. Backend startup creates the account only when it is missing. It does not update the password or profile of an existing database user, so changing `SEED_ADMIN_PASSWORD` alone does not rotate an existing account password.
- **Input ownership:** `io/input.json` represents external equipment state and is read-only from the web application.
- **Output ownership:** `io/output.json` represents application control signals. Backend writes must increment `revision`, set a UTC timestamp, and use atomic replacement.

## 9. Login and Service-Availability Diagnosis

- The frontend reads `VITE_API_BASE_URL` from the repository `.env` through Vite's repository-level `envDir`; when unset, it calls `http://127.0.0.1:8000`.
- The message `The AOI service is unavailable. Check the backend connection.` is created only when the browser cannot complete `fetch`. It indicates an unreachable backend, a network failure, or a CORS/configuration problem, not rejected credentials.
- Invalid credentials reach FastAPI and return HTTP `401` with `The email or password is incorrect.` An inactive account returns HTTP `403`.
- Diagnose availability before changing credentials: start both services with a supported launcher, request `http://127.0.0.1:8000/health`, and confirm the JSON response reports `status` as `ok`.
- During the verified login incident, PostgreSQL was healthy, the seed operator existed and was active, and the configured seed password matched the stored hash. Starting the missing FastAPI service restored frontend login requests; no source or database change was required.
- CORS permits the configured `FRONTEND_ORIGIN`, which defaults to `http://127.0.0.1:5173`. In development only, add the same-scheme, same-port loopback alias between `127.0.0.1` and `localhost`; browsers treat those as different origins and otherwise report `Failed to fetch`. Do not use a wildcard or extend this alias outside development.

## 10. Responsive Verification Baseline

- Do not use application-component positioning with `position: absolute`, `position: fixed`, or hardcoded `top`, `right`, `bottom`, and `left` coordinates.
- Verify changed interfaces at widths `390`, `768`, `1280`, and `1920` pixels. Authentication plus the Dashboard, Settings, Camera Manager, and Database workspaces passed all four widths without unintended document-level horizontal overflow.
- Include a short viewport such as `390x600`. Content must use vertical scrolling when necessary rather than clipping or shrinking below accessible control sizes.
- Validation messages must push following controls through normal document flow. Verify that email errors do not overlap password controls and password errors do not overlap form options.
- Preserve Figma hierarchy, proportions, colors, typography, and spacing intent through Grid, Flexbox, `clamp()`, `min()`, `max()`, and content-driven sizing instead of canvas coordinates.
- **Connected workspace frames:** The live Figma Bridge file `AOI`, page `AOI Studio`, contains implemented product frames Dashboard `36:849`, Settings `36:1176`, Camera Manager `36:1569`, and Database `36:1632`, in addition to authentication frame `41:991`. Read live bridge metadata and screenshots before implementing; the broader 19-screen design specification is a roadmap, not proof that every frame exists on the canvas.
- **Industrial shell behavior:** Use a shared top bar, inspection toolbar, project explorer, responsive workspace, and bottom dock. Collapse the explorer into a horizontally scrollable view selector on tablet/mobile, and stack context panels in normal flow at narrower widths.
- **Light industrial theme baseline:** Product chrome, cards, forms, tables, and navigation use light neutral backgrounds with dark text. Dark surfaces are reserved for bounded optical, camera, heatmap, or depth visualizations where they improve data contrast. Machine state cards pair semantic color with explicit labels such as `OK`, `WAIT`, and `ERR`.
- **320px scrollbar edge case:** Do not apply `min-width: 320px` to `html`, `body`, or `#root`. A vertical scrollbar can reduce the layout viewport below 320 CSS pixels and turn that minimum into document-level horizontal overflow. Use `min-width: 0` on the document roots and enforce intrinsic constraints inside components.
- **Container-query cascade:** Workspace cards depend on the width left after application chrome, not only on viewport width. Keep container-query rules after overlapping viewport media rules or use equivalent specificity so older breakpoint declarations cannot restore minimum grid-track widths and clip status or KPI cards.
- **Current resize matrix:** Dashboard, Settings, Camera Manager, and Database passed document-level and unexpected element-level overflow checks at `320`, `390`, `480`, `600`, `768`, `1024`, `1280`, `1600`, and `1920` pixel widths. Horizontal overflow remains allowed only inside intrinsic tab rails, toolbars, docks, and table wrappers.

## 11. Validation Commands

Run these after environment, authentication, I/O, or responsive-layout changes:

```bash
bash scripts/install/verify-environment.sh
bash scripts/test/test.sh
bash scripts/build/build.sh
codegraph sync .
codegraph status .
```

The current baseline is 15 backend tests, 14 core tests, 12 integration tests, 11 frontend tests, a successful TypeScript production build, and zero npm audit findings.

## 12. Workflow Editor Contracts and Diagnostics

- **Runtime-package boundary:** Every catalog method has a matching package at `core/nodes/<category>/<node-id>/node.py` with explicit input/output variable names, a placeholder `execute()` entry point, and `USE = test | debug | release`. A package or `test` badge still does not imply that OpenCV, PyTorch, Anomalib, model weights, training, or inference is installed.
- **Core ownership:** `core/algorithms` owns catalog metadata, typed port templates, and parameter constraints. `core/pipeline` owns graph validation and stable topological ordering. The frontend may provide immediate feedback but the backend must validate the complete submitted graph through core before persistence.
- **Persistence contract:** Store AOI-owned camelCase documents under `data/projects/<recipe-slug>/workflow.json`. Writes use a sibling temporary file, flush, `fsync`, and atomic replacement. A save requires an exact revision match, increments once on success, and returns HTTP `409` for stale drafts without overwriting storage.
- **Runtime data ownership:** Recipe workflow files under `data/projects/` are local runtime data and remain ignored by Git. Keep only `data/projects/.gitkeep` in source control.
- **Monorepo backend imports:** The development launcher starts Uvicorn from `backend/`, so its process must receive a `PYTHONPATH` containing both the repository root and `backend/`. Otherwise backend imports succeed in repository-root tests but runtime startup fails when workflow routes import sibling `core` modules.
- **React Flow presentation state:** Apply every React Flow node change to local presentation nodes so measured dimensions remain initialized. Synchronize AOI node values into that presentation state while preserving `measured`, and call `useUpdateNodeInternals` after AOI nodes or ports change so existing edge paths remain visible.
- **Atomic node deletion:** React Flow can emit dependent edge removals before a node removal callback. Intercept node deletion with `onBeforeDelete`, delegate the node-and-edge confirmation to the AOI draft owner, and cancel React Flow's default batch so rejecting confirmation leaves both nodes and edges unchanged.
- **Browser verification:** The editor and Dashboard Inspection flow passed document-overflow checks at 390, 768, 1280, and 1920 pixel layout widths, including 390x600. Catalog drag/drop, typed edge acceptance/rejection, free node movement, zoom/fit, edge deletion, atomic node confirmation, execution drag reorder, keyboard alternatives, inspector parameters and variadic ports, successful saves, stale `409` recovery, focus visibility, and reduced motion were exercised in an authenticated browser.

## 13. Workstation Preference Persistence

- Store user-scoped workstation state under `data/preferences/users/<user-id>/<workstation-id>.json`; validate workstation IDs as lowercase kebab-case before creating a path.
- Preference writes use the workflow repository's atomic pattern: sibling temporary file, flush, `fsync`, and `os.replace`. Exact revision matching prevents two browser tabs from silently overwriting each other.
- Dashboard viewer size is persisted as bounded grid units rather than screen pixels so the layout remains portable across viewport sizes. Photometric image count is derived from light count and is never persisted as an independent value.
- GitNexus re-indexing from WSL can fail with `invalid ELF header` when WSL resolves a Windows global npm installation containing a Windows native module. In that situation, use the up-to-date CodeGraph index and repair the Node/npm executable boundary before relying on GitNexus change detection.

## 14. Repository Documentation Layout

- A scaffold generator previously created directories named `README.md` containing identical `README.md` placeholder files. These paths add no module boundary, confuse file navigation, and must not be recreated.
- Keep maintained operational documentation at the repository root and under `scripts/`; keep topic-specific reports directly under `docs/<topic>/` rather than inside a README-named wrapper directory.
- Do not preserve unused source-module directories with placeholder documentation. Add the directory when implementation exists. For required runtime directories, use narrowly scoped `.gitkeep` files and matching ignore rules instead.

## 15. Browser Credential Autofill and Tab-Scoped Authentication

- Chrome password autofill needs conventional credential metadata, not only labels and input types. The sign-in form uses `name="username"` with `autocomplete="username"` and `name="password"` with `autocomplete="current-password"`.
- AOI Studio authentication is tab-scoped. Store the authenticated session only in `sessionStorage`: refreshing the current tab preserves the workspace, while opening the site in a new tab starts at sign-in.
- Never restore authentication from `localStorage`. Remove the legacy `aoi-studio-session` local-storage entry during startup so previously persisted or expired tokens cannot bypass sign-in and trigger protected API errors.

## 16. Standalone Simulator Console and Windows Camera Input

- Keep simulation-only controls in a standalone loopback console rather than the authenticated production HMI. Fault injection, reset, jog, and virtual interlock endpoints must never appear in hardware adapters.
- In WSL, prefer browser `getUserMedia()` for a Windows webcam. The browser owns camera permission and uploads a selected frame as PNG; this avoids USB/IP attachment, `/dev/video*` driver differences, and absolute Windows paths.
- Browser-selected folders expose file contents, not a portable directory path. Normalize supported browser image formats to lossless PNG and copy them into simulator-managed storage with bounded size and safe IDs.
- `AOI_SIMULATOR_NO_BROWSER=1` keeps the standalone launcher automation-safe while normal interactive startup still opens the Windows browser.

## 17. Authenticated Device Gateway and Artifact Integrity

- The browser communicates only with the authenticated FastAPI control plane. Camera and motion adapter origins are trusted loopback configuration values, never request parameters, so the gateway cannot be used as an arbitrary network proxy.
- Typed adapter clients validate protocol `1.0`, service identity, readiness, Pydantic response contracts, and bounded connect/read/write timeouts before device operations. Preserve health reads for unavailable hardware diagnostics, but reject capture and motion commands unless the adapter reports `ready`.
- A camera capture is not accepted as ready until the backend downloads its inspection artifact, enforces the media-type and size limits, verifies byte length, and compares SHA-256 with capture metadata. The browser receives verified content through backend port `8000`, not directly from the camera adapter.
- Keep simulator-only controls such as jog, reset, interlock mutation, and fault injection off the production gateway. The shared gateway exposes only health, capabilities, capture, motion state, home, absolute move, stop, and clear-fault contracts that hardware adapters can implement safely.

## 18. Shared Hardware Configuration and Polling Safety

- Treat adapter state as the single source of truth for both AOI Studio and the Simulator Console. Common camera and motion settings use identical `GET/PUT /configuration` contracts in simulation and hardware adapters; simulation-only source selection and fault controls remain separate.
- Polling must never overwrite an unsaved operator draft. Mark a configuration form dirty on its first input event, suspend draft replacement while dirty, and resume synchronization only after a successful Apply.
- Hardware mode must start the HMI when CSI/UART adapters respond with a valid protocol but report `unavailable`. Show diagnostics, omit operational state/configuration requests, disable commands, and never substitute simulator adapters.
- In simulation mode, `run_dev.sh` owns the console as a fifth process group. Runtime mode must be read from the protected PID file for later `status` checks, otherwise a status invocation incorrectly applies hardware health semantics to a running simulation stack.

## 19. Foundation Repair and Audit Baseline

- Single-Administrator mode disables public registration by default while retaining idempotent local bootstrap. Keep the seed identity named `AOI Administrator`; do not reintroduce sign-up UI without an approved authorization design.
- Inspection API responses must be built from loaded relationships. Never replace persisted defects or image evidence with empty placeholder arrays.
- Treat camera and motion availability independently. Fetch configuration or operational state only for the adapter that reports ready; degradation of one adapter must not erase the other adapter's snapshot.
- Every visible locale field belongs to persisted `WorkstationPreferences` and must flow through the shared preference-change callback so revision and dirty checks remain authoritative.
- A workstation ID field is a destination selector, not permission to mutate the loaded profile's identity. Load destination state before replacing current saved and draft state.
- Dataset safety contracts include bounded batch and file size, image magic-byte validation, allowlisted names, traversal rejection, duplicate capture naming, and safe ZIP member paths. Preserve characterization tests even when production behavior already passes.
- Audit only bounded security metadata: verified actor ID, action, method, path, resource identity, request ID, status, result, and timestamp. Never read or store request bodies, credentials, bearer tokens, secrets, or image bytes. Audit failures must be logged and must not replace original route responses.
- GitNexus resolves repositories through its global registry, not necessarily current worktree. When a worktree and main checkout share repository name, index worktree explicitly and pass its path to `detect-changes --repo ...`; otherwise change detection can inspect clean main checkout and incorrectly report `No changes detected.`

## 20. PostgreSQL Settings Platform

- Alembic is the only schema-evolution mechanism. Startup verifies head; it never runs `create_all`, stamps, or upgrades silently.
- PostgreSQL row locks and expected revisions replace file locks. Versions are immutable; rollback inserts a source-linked version.
- Workstation preference JSON is migration input only. Dry-run before `--apply`; equal checksums are no-op and conflicts block the batch.
- Activation idempotency keys are distinct from request IDs. Reuse request IDs violates audit uniqueness; replay only the `Idempotency-Key` with a fresh request ID.
- Portable settings export verifies canonical SHA-256 but is not a PostgreSQL disaster-recovery backup.
