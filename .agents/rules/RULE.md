---
name: rule
description: Use this rule before editing the project
metadata:
  origin: Sown
---

# AOI_APP Project Rules

## 1. Purpose
This document defines the standard rules for folder structure, file names, variable naming, commit messages, API design, security, testing, and language usage across the project.

## 2. General principles
- Prefer clear, searchable, maintainable, and extensible code.
- Each module should have a single primary responsibility.
- Before creating a new file, check whether a similar module already exists.
- Do not place files in the root folder if a proper functional folder already exists.
- Keep the project consistent across backend, frontend, core, database, and data modules.

## 3. Folder naming rules
- Use lowercase names only.
- Use kebab-case for folder names.
- Example: `user-management`, `ai-pipeline`, `image-processing`.
- Folder names must describe the function clearly.
- Avoid generic names such as `temp`, `new`, `abc`, `final`, or `misc`.
- Use a predictable structure for functional folders: `feature/`, `domain/`, `service/`, `types/`, `tests/`.

## 4. File naming rules
- Python files: use `snake_case.py`.
- TypeScript and JavaScript files: use `kebab-case.ts` or `kebab-case.tsx`.
- React components: use `PascalCase.tsx`.
- Test files: use suffixes such as `.test.ts`, `.test.py`, or `.spec.ts`.
- Avoid ambiguous names or names that conflict with other modules.

## 5. Naming rules for variables, functions, and classes
- Python:
  - variables and functions: `snake_case`
  - classes: `PascalCase`
  - constants: `UPPER_SNAKE_CASE`
- TypeScript and JavaScript:
  - variables and functions: `camelCase`
  - components, classes, and interfaces: `PascalCase`
  - constants: `UPPER_SNAKE_CASE`
- Boolean names should start with `is`, `has`, `can`, or `should`.
- Function names must describe behavior, for example: `load_user_profile`, `calculate_defect_score`.

## 6. Functional folder ownership and responsibility
- `backend/`: APIs, authentication, schemas, services, middleware, and websocket modules.
- `frontend/src/`: `components/`, `pages/`, `hooks/`, `services/`, `store/`, `types/`, `utils/`, and `styles/`.
- `core/`: business logic, algorithms, calibration, vision, matching, measurement, and pipeline logic.
- `data/`: cache, images, models, projects, reports, and temporary files.
- `database/`: schema, migrations, seed data, and backup scripts.
- `tests/`: organize by layer such as `backend`, `frontend`, `integration`, and `performance`.

## 7. Layering rules
- Frontend is responsible only for UI rendering and calling services or APIs.
- Backend handles requests, responses, validation, authentication, and basic business flow.
- Core contains shared business logic, algorithms, and data processing logic.
- Database contains only schema, migrations, and data structure definitions.
- Do not place business logic directly inside UI components or routes.

## 8. Commit message rules
- Use clear and consistent commit messages in English.
- Follow the Conventional Commits style when possible:
  - `feat: add user profile endpoint`
  - `fix: correct defect score calculation`
  - `refactor: simplify image preprocessing flow`
  - `test: add unit tests for calibration service`
  - `docs: update API documentation`
  - `chore: update dependencies`
- Keep the subject line short and imperative.
- Include a scope when helpful, for example: `feat(api): add user authentication`.
- Avoid vague messages like `update`, `fix stuff`, or `misc changes`.

## 9. API rules
- Use RESTful resource-based naming.
- Prefer plural nouns for collections, for example: `/users`, `/projects`, `/defects`.
- Keep endpoint names consistent and predictable.
- Use clear and consistent request/response schemas.
- Return proper HTTP status codes and meaningful error messages.
- Validate all input data on the server side.
- Version APIs when breaking changes are introduced.

## 10. Security rules
- Never hardcode secrets, tokens, passwords, or private keys.
- Use environment variables or secure configuration storage.
- Validate and sanitize all input from users and external systems.
- Apply authentication and authorization checks for protected resources.
- Do not expose sensitive information in logs, responses, or error messages.
- Follow the principle of least privilege for services and access tokens.

## 11. Testing rules
- Add or update tests whenever behavior changes.
- Prefer a test-first approach when implementing or fixing a feature.
- Write unit tests for isolated logic and integration tests for cross-module behavior.
- Keep tests readable, deterministic, and independent.
- Do not skip tests for critical flows such as authentication, data processing, or API contracts.
- Use meaningful test names that describe the expected behavior.

## 12. Language rules
- All code, file names, variables, functions, classes, comments, logs, UI text, API payload keys, and test names must be written in English.
- Vietnamese should be used only for chat replies and conversational communication with humans.
- Do not mix Vietnamese into code, logs, UI strings, commit messages, or documentation that is part of the codebase.
- Every markdown file (`.md`) created or modified in the repository must have a corresponding `.md.vn` translation file written in Vietnamese (e.g. `README.md` and `README.md.vn`).

## 13. Additional rules
- Names must be meaningful and should not use unclear abbreviations.
- If multiple files implement the same concept, use a consistent prefix or suffix such as `user-service`, `auth-middleware`, or `defect-report`.
- Do not hardcode repeated values; use constants, enums, or configuration files instead.
- Comments should explain why something exists, not repeat what the code already clearly shows.
- When editing an existing module, preserve the naming style and structure already used there.

## 14. Path rules
- Always use relative paths when referring to files, directories, or assets within the project.
- Absolutely avoid absolute paths (e.g. `/home/...` or `C:\...` or `\\wsl.localhost\...`) to ensure the project remains portable and runs smoothly when transferred to other machines.
- Use path utility libraries (like Python's `pathlib` or Node's `path`) with relative references to resolve local project assets dynamically.

## 15. Responsive interface rules
- Product interfaces must use a light visual theme as the primary appearance: light neutral page backgrounds, white or near-white surfaces, dark readable text, and semantic accent colors reserved for actions and machine states. Dark surfaces are permitted only inside bounded technical visualizations such as camera feeds, optical images, heatmaps, and depth viewers where they improve data contrast.
- Light-theme colors must meet WCAG AA contrast for text and interactive states. Status must never be communicated by color alone; pair color with a label, icon, shape, or pattern.
- Web interfaces must adapt automatically to the available viewport and container size.
- Use normal document flow with CSS Grid, Flexbox, responsive units, `min()`, `max()`, `clamp()`, and content-driven sizing.
- Do not use `position: absolute` or `position: fixed` to place application components or reproduce Figma screen coordinates.
- Do not position application components with hardcoded `top`, `right`, `bottom`, or `left` coordinates.
- Figma coordinates are visual references, not implementation coordinates. Preserve hierarchy, proportions, spacing, and design tokens through responsive layout primitives.
- Define responsive behavior for mobile, tablet, desktop, zoomed content, and both short and tall viewports.
- Fixed dimensions are permitted only when they express an intrinsic constraint such as an icon size, border width, minimum accessible control height, or bounded `max-width`; they must not cause viewport overflow.
- Validation messages and dynamic content must remain in normal document flow so they cannot overlap adjacent controls.
- Layouts must resize continuously from 320px upward, including intermediate widths, browser zoom, split-screen windows, and containers made narrower by navigation panels. Do not design only for named device breakpoints.
- Prefer container queries for components whose available width depends on surrounding application chrome. Horizontal scrolling is allowed only for intrinsically wide controls or data such as tab rails and tables, never for the document itself.
- Verify changed interfaces at a minimum of 390px, 768px, 1280px, and 1920px viewport widths and confirm that no unintended horizontal overflow occurs.

## 16. Examples
- Folder: `user-management/`
- Python file: `user_service.py`
- TypeScript component: `user-profile-card.tsx`
- Variable: `defectCount`, `isLoading`, `MAX_IMAGE_SIZE`
- Commit: `feat(api): add user authentication`
- Relative Path (Python): `Path(__file__).parent.parent / "data" / "images"` instead of `/home/sonev/graduation_project/main/AOI_APP/data/images`

## 17. AI Experience and Memory rules
- When resolving a bug, encountering unique configurations, or identifying critical technical notes, the AI agent must record this knowledge.
- Save these notes as `memory.md` (in English) and `memory.md.vn` (in Vietnamese) inside the `.agents/experience/` directory to preserve operational knowledge for future agents.

## 18. Project code-graph query rules
- Before reading, understanding, debugging, refactoring, or changing project code, the AI agent must query the project with CodeGraph or GitNexus when either tool is available.
- Prefer GitNexus for symbol context, execution flows, dependency relationships, impact analysis, and change detection. Use CodeGraph when it is the available project code-graph tool or when its graph view is more appropriate.
- Read the relevant project/index context before making assumptions about architecture or dependencies. If the index is stale, refresh it before relying on graph results.
- For changes to functions, classes, or methods, run impact analysis first and report the affected callers, execution flows, and risk level. Do not proceed without warning the user when the risk is high or critical.
- After editing, run the graph change-detection check when available to confirm that only the expected symbols and execution flows were affected.

## 19. Core node independence rules
- Every `node.py` under `core/nodes/` must be an independent, replaceable component.
- A node must not import, call, or depend on another node's functions, classes, implementation details, or mutable runtime state. Do not create shared helper functions between nodes.
- Node implementations must not use shared `*_runtime.py` files or other runtime implementation files as a shortcut for node behavior. The node must contain the behavior it owns and declare its own dependencies explicitly.
- Nodes may communicate only through the documented node input/output contract and approved pipeline interfaces; they must not rely on hidden cross-node state, import order, or side effects.
- Replacing or removing one node must not require edits to unrelated node implementations. If common behavior is truly required, first ask the user to approve a change to the node contract or a separately documented platform-level interface.

## 20. Clarification rule for uncertain requests
- If the AI agent is not certain about the user's requirement, intended scope, expected behavior, or direction of the edit, it must ask the user for clarification before changing files or running state-changing commands.
- The clarification must explicitly explain what is uncertain, why that uncertainty matters, and the concrete choices or edit options available. Include the expected impact of each option when it is known.
- Do not silently choose an interpretation for an ambiguous request. Continue only after the user confirms the requirement or selects an option.

## 21. Non-interactive command and installation rules
- Commands must be run in non-interactive mode whenever possible so the agent does not stop at a pager prompt such as `:` or wait for manual `Enter` and `q` input.
- For Git output, use `git --no-pager ...` or set `GIT_PAGER=cat`, `PAGER=cat`, and `TERM=dumb`. Never use an interactive pager for `status`, `diff`, `log`, `show`, or file inspection.
- For file inspection, use direct non-paginated commands such as `Get-Content`, `cat`, or the approved file-reading tools. Do not pipe output to `less`, `more`, `vim`, or another interactive viewer.
- For package installation and commands that may ask for confirmation, use the package manager's documented non-interactive/assume-yes option and set the appropriate CI flag. Examples: `npm install --yes` or `npm_config_yes=true`, `pip install --no-input`, `apt-get -y`, and `CI=1` where supported.
- Do not wait for or request manual `y/n`, `Enter`, or `q` input from the user. If a tool has no safe non-interactive option, stop and explain the exact command and required confirmation instead of launching an interactive process.
- Avoid commands that require a TTY or an interactive shell. Add explicit timeouts where the execution environment supports them, and report a timeout rather than leaving a command running indefinitely.

## 22. VS Code terminal tab hygiene
- Unless multiple commands must run concurrently, use only one VS Code terminal tab for the task.
- When a command or test is complete and its terminal is no longer needed, clear its output or close/remove the terminal tab before starting another unrelated command.
- Do not create extra terminal tabs for independent sequential work; batch independent commands in one terminal invocation when safe.

## 23. WSL command execution
- When the project is located in the WSL filesystem and a Linux command, GitNexus operation, Python command, or test is required, prefer executing it through the Ubuntu WSL distribution from the project directory `/home/sonev/graduation_project/main/AOI_APP`.
- From a Windows/Cline command runner, use this exact wrapper: `wsl.exe -d Ubuntu -- bash -lc \"cd /home/sonev/graduation_project/main/AOI_APP && <command>\"`. The wrapper starts Ubuntu, changes to the Linux project directory, executes the command, returns its exit code, and then closes the non-interactive shell.
- The wrapper is the non-interactive equivalent of the project terminal prompt `(base) sonev@Son:~/graduation_project/main/AOI_APP$`; do not try to reproduce the prompt with `echo` or use a Windows UNC path as the Linux working directory.
- Before a group of commands, optionally verify the WSL context with `wsl.exe -d Ubuntu -- bash -lc \"cd /home/sonev/graduation_project/main/AOI_APP && whoami && hostname && pwd\"`. Expected values are user `sonev`, host `Son`, and project path `/home/sonev/graduation_project/main/AOI_APP`.
- Put all Linux commands inside the same `bash -lc` block and chain dependent commands with `&&`; use `;` only when a later command must run after a failed command. Example: `wsl.exe -d Ubuntu -- bash -lc \"cd /home/sonev/graduation_project/main/AOI_APP && git --no-pager status --short && python -m compileall -q core\"`.
- Run common project operations through WSL as follows:
  - Git: `wsl.exe -d Ubuntu -- bash -lc \"cd /home/sonev/graduation_project/main/AOI_APP && git --no-pager diff --check\"`.
  - Python: `wsl.exe -d Ubuntu -- bash -lc \"cd /home/sonev/graduation_project/main/AOI_APP && python -m compileall -q core\"`.
  - Tests: `wsl.exe -d Ubuntu -- bash -lc \"cd /home/sonev/graduation_project/main/AOI_APP && python -m pytest -q tests/core\"`.
  - GitNexus: `wsl.exe -d Ubuntu -- bash -lc \"cd /home/sonev/graduation_project/main/AOI_APP && node .gitnexus/run.cjs detect_changes\"`.
- Quote the outer Windows command and inner Bash command carefully. Use Linux paths after `bash -lc`; do not pass `\\wsl.localhost\\Ubuntu\\...`, `C:\\...`, or PowerShell variables to a Linux command. Escape `$`, backticks, quotes, and command substitutions when they must be evaluated inside WSL rather than by the outer shell.
- Do not use `wsl.exe` without `-d Ubuntu`, do not rely on the user's current Windows directory, and do not run the command from `/mnt/c/...` when the project is stored under `/home/sonev/...`.
- Do not open or depend on an interactive WSL terminal, and do not wait for manual input. Commands must remain non-interactive and must use explicit pager/confirmation options where applicable.
- Keep the WSL working directory and environment consistent with the project. Do not mix Windows and WSL path syntaxes inside the same Linux command.
- If WSL is unavailable or the command cannot be executed safely through WSL, report the limitation and use the safest available fallback without changing project state unexpectedly.
