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

The current baseline is three backend unit tests, two authentication/I/O integration tests, five frontend validation/filtering tests, a successful TypeScript production build, and zero npm audit findings.
