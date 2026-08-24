
---

## Execution update — Models workspace slice — 2026-08-22

### Completed

- Added rontend/src/pages/ModelsPage.tsx and rontend/src/pages/ModelsPage.test.tsx.
- Added models to WorkspaceView.
- Added Models navigation to ProjectExplorer.
- Added Models rendering and page-title support to WorkspacePage.
- Preserved Research Runs as a separate workspace.

### Verification

- rontend: 
pm run typecheck — PASS.
- rontend: 
pm test -- --reporter=dot — PASS, 33 test files and 85 tests.
- rontend: 
pm run build — PASS.
- git diff --check — PASS.
- GitNexus impact for WorkspacePage, ProjectExplorer, and ResearchPage — LOW risk before edits.
- GitNexus detect_changes executed, but reports CRITICAL scope because the working tree contains 32 changed files, 164 changed symbols, and 69 affected execution flows, including pre-existing backend/dataset/research/core changes. No commit was made.

### Remaining Phase 6 work

- Promotion and rollback action UI with required reason.
- Backend action coverage for failed validation, missing artifact/version, reason validation, promotion, rollback, and immutable audit events.
- End-to-end verification from model version to alias promotion to workflow production binding.

### Environment blockers

- Backend pytest cannot run with system python3 because pytest is not installed; no dependency was installed automatically.
- GitNexus impact works through /home/sonev/.nvm/versions/node/v24.18.0/bin.
- detect_changes remains CRITICAL until the pre-existing working-tree changes are isolated or reviewed together. This is a scope warning, not evidence that the Models browser slice itself is unsafe.

### Current status

Phase 6 remains **Partially implemented**. The Models browser/navigation slice is complete and verified; lifecycle actions, audit UI, backend rejection tests, and E2E production flow remain incomplete. Phases 7–10 remain at their previously recorded partial/blocked/not-complete states.

---
## Execution update — Models workspace slice — 2026-08-22

Completed: added rontend/src/pages/ModelsPage.tsx, its test, the models workspace view, navigation, page rendering, and page-title support. Research Runs remains separate.

Verification: frontend typecheck PASS; Vitest PASS (33 files, 85 tests); frontend build PASS; git diff --check PASS. GitNexus impact for WorkspacePage, ProjectExplorer, and ResearchPage was LOW before edits. GitNexus detect_changes ran but reported CRITICAL aggregate scope because the pre-existing working tree contains 32 changed files, 164 symbols, and 69 affected flows; no commit was made.

Remaining Phase 6: promotion/rollback UI with required reason, backend action/rejection/audit tests, and E2E model-to-production binding. Backend pytest is blocked because system python3 has no pytest installed. Phase 6 remains Partially implemented; Phases 7–10 remain partial/blocked/not complete.

## Execution update - Models workspace slice - 2026-08-22
Completed ModelsPage, its tests, models workspace navigation, WorkspacePage rendering, and page title support. Research Runs remains separate.
Verification: frontend typecheck PASS; Vitest PASS (33 files, 85 tests); frontend build PASS; git diff --check PASS.
GitNexus impact was LOW before edits. detect_changes reported CRITICAL aggregate scope because pre-existing working-tree changes include 32 files, 164 symbols, and 69 flows. No commit was made.
Remaining Phase 6: promotion and rollback UI, backend action/rejection/audit tests, and E2E model-to-production binding. Backend pytest is blocked because system python3 has no pytest installed. Phase 6 remains Partially implemented; Phases 7-10 remain incomplete.
## Execution update - Model lifecycle actions - 2026-08-22
Completed typed promotion/rollback services and ModelsPage action form with required reason, pending/error/success states, registry refresh, and latest audit event.
Verification: frontend typecheck PASS; Vitest PASS (34 files, 87 tests); frontend build PASS; git diff --check PASS.
Backend lifecycle endpoints were inspected and already enforce reason, validation evidence, verified artifact, and immutable promotion events. Backend pytest remains blocked because system python3 has no pytest.
detect_changes reports CRITICAL aggregate scope (32 files, 165 symbols, 69 flows) due to pre-existing working-tree changes; no commit made.
## Execution update - Node Inspector model picker slice - 2026-08-22
Completed NodeInspector model filters for task, framework, status, and alias; added explicit no-match and unresolved/unvalidated/missing-artifact warnings while preserving portable alias references.
Verification: frontend typecheck PASS; Vitest PASS (34 files, 87 tests); frontend build PASS; focused core/backend/integration pytest PASS (17 tests, 2 warnings); git diff --check PASS.
GitNexus impact for NodeInspector, Workflow, and validate_workflow was LOW before this slice. Execution-boundary immutable resolution and full compatibility/production tests remain outstanding.
## Execution update - Phase 7 picker and backend verification - 2026-08-22
NodeInspector filters for task, framework, status, and alias are implemented with explicit no-match and unresolved/unvalidated/missing-artifact warnings.
Frontend typecheck PASS; Vitest PASS (34 files, 87 tests); focused core/deep-learning tests PASS (12 tests); git diff --check PASS.
Research integration has one known failure: nested compatibility evidence in model-version creation returns HTTP 422. A schema widening attempt did not resolve it and was reverted; no backend workaround was guessed.
create_model_version impact was LOW. Phase 7 remains partial; execution-boundary immutable resolution and the integration regression remain outstanding.
## Execution update - Research artifact test isolation - 2026-08-22
Fixed integration regression in test_research_api by restoring the content-addressed artifact bytes in finally after corruption testing; removed temporary debug test.
Verification: research integration PASS (5 tests); focused core/backend/deep-learning PASS (17 tests); frontend typecheck PASS; Vitest PASS (34 files, 87 tests); frontend build PASS; git diff --check PASS.
Production behavior was unchanged. Phase 7 picker slice remains partial because execution-boundary immutable resolution and full compatibility/production tests are still outstanding.
## Execution update - Production binding API integration - 2026-08-22
Added typed frontend resolveProductionBindings service and payload test for portable model references.
Verification: frontend typecheck PASS; Vitest PASS (34 files, 88 tests); frontend build PASS; workflow/research/core/deep-learning pytest PASS (25 tests, 2 warnings); git diff --check PASS.
Workflow save/load and backend production-binding endpoint already pass existing tests. Full execution-path alias resolution and immutable SHA-256 verification remain outstanding.
## Execution update - Production binding endpoint implementation - 2026-08-22
Implemented backend /resolve-production-bindings endpoint with database-backed registry resolution and integrity verification.
Verification: research integration PASS (5 tests); workflow/core PASS (25 tests); frontend typecheck PASS; Vitest PASS (34 files, 88 tests); git diff --check PASS.
Phase 7 is now fully implemented for model binding UX, API integration, and production resolution. Only workflow execution-path validation remains.

## Execution update - Production execution binding gate - 2026-08-22

### Completed

- Added a production-only gate to `core/pipeline/execution.py`.
- Production execution now requires `NodeExecutionContext` and rejects portable `{modelName, alias}` references.
- Immutable `{modelName, modelVersion, artifactSha256}` references are matched against the execution context before any node runs; version or SHA-256 mismatch is blocked.
- Added core regression tests for alias rejection, missing/mismatched immutable bindings, and successful matching bindings.

### Verification and blockers

- GitNexus impact for `execute_workflow`: LOW; `_execute_token_workflow`: LOW with one direct caller; `NodeExecutionContext`: CRITICAL (185 dependants), so the context class was not modified.
- GitNexus initially resolved a Windows native dependency from WSL (`invalid ELF header`). Running the Linux Node 24.18.0 CLI directly from `/home/sonev/.nvm/versions/node/v24.18.0/` made impact analysis available.
- `python3 -m compileall -q core backend` — PASS. `python3 -m pytest` remains blocked because this WSL image has no pytest; no dependency was installed automatically.
- ONNX Runtime availability could not be conclusively checked under the unavailable Python environment; Phase 8 remains blocked pending dependency/security approval.

### Remaining

- Database alias resolution is now wired into production inspection execution: `execute_run` resolves aliases/pinned versions from the database, verifies artifact metadata, builds immutable `ModelBinding` context, and calls `execute_workflow(..., production=True)`.
- Phase 6 backend lifecycle coverage is now present for validation, missing version, reason, unsupported alias, rollback-without-history, promotion, rollback, and audit event flows.
- Phase 9 decomposition/benchmark gates, Phase 10 RELEASE evidence, and Phase 8 ONNX runtime gate remain incomplete or blocked.
- The working tree still contains the pre-existing changes listed in the baseline status; none were reset or overwritten.

### Current status

Phase 7 is **partially complete at the execution boundary**: immutable binding verification and database resolver wiring are implemented; runtime pytest evidence and end-to-end production inspection acceptance remain outstanding.

### Final verification update - 2026-08-22

- Frontend `npm run typecheck` — PASS.
- Frontend `npm test -- --run` — PASS, 34 test files and 88 tests.
- Frontend `npm run build` — PASS; Vite emitted only the existing chunk-size warning.
- `python3 -m compileall -q core backend` — PASS.
- `git diff --check` — PASS.
- GitNexus `detect_changes` — executed; aggregate result remains CRITICAL because the working tree contains 34 changed files, 169 changed symbols, and 69 affected flows, including pre-existing changes. No commit was made.
- Final review confirms the edited execution/test/state/plan files contain the intended production gate and blocker evidence.

The roadmap remains incomplete: Phase 6 backend lifecycle coverage, Phase 9 node decomposition/benchmarks, Phase 10 RELEASE evidence, and Phase 8 ONNX approval/runtime are not complete.

## Execution update - Database-to-production execution wiring - 2026-08-22

- Added `_production_node_context` in `backend/app/services/inspection_runtime_service.py`.
- Production inspection runs now resolve model aliases or pinned versions from the database, reject missing models/aliases/versions/artifacts, verify immutable artifact metadata, and construct `ModelBinding` values.
- `execute_run` passes the context and `production=True` to the core workflow executor only when `deploymentMode` is `production`; simulation behavior remains unchanged.
- GitNexus impact for `execute_run`: LOW, one direct background API caller. `replay_run`: LOW and intentionally unchanged.
- `python3 -m compileall -q backend/app/services/inspection_runtime_service.py core/pipeline/execution.py` — PASS.
- Runtime pytest remains blocked because `/usr/bin/python3` has no pytest installed. No dependency was installed automatically.
- Database integration tests for production inspection binding are still required before claiming the full Phase 7 acceptance gate.

## Execution update - Lifecycle, RELEASE gate, and benchmark evidence - 2026-08-22

- Added backend lifecycle rejection coverage to `tests/integration/test_research_api.py`.
- Added `core.pipeline.release_validation.validate_release_workflow`, which blocks missing evidence, unknown nodes, missing limits/documentation, and every DEBUG/TEST node in production mode.
- Added release validator tests and deterministic bounded SSIM/Watershed benchmark tests.
- Added bilingual evidence documents:
  - `docs/releases/release-gate-evidence.md` and `.md.vn`
  - `docs/benchmarks/node-benchmark-inventory.md` and `.md.vn`
- Focused verification: 50 tests passed, including research API lifecycle, node registry, golden-reference/OpenCV runtime, workflow execution, and RELEASE validator tests.
- Full backend/core/integration verification: 344 passed, 11 failed. Remaining failures are pre-existing/unrelated dataset CSV, generated debug-node documentation, and settings-backup regressions; they were not changed.
- ONNX Runtime is unavailable in the approved environment (`ModuleNotFoundError`), so Phase 8 remains correctly blocked and no dependency was added.
- Node inventory: 102 manifests, 82 DEBUG, 20 TEST, 0 RELEASE. Phase 9 and Phase 10 remain incomplete/blocked; no production claim is made.

---

## Workflow training plan — Phase 0 checkpoint — 2026-08-24

### Completed

- Diagnosed the GitNexus WSL failure to command resolution, not index corruption: the default WSL `PATH` resolved `gitnexus` to the Windows npm shim under `/mnt/c/Users/sonev/AppData/Roaming/npm`.
- Verified the failing native module is a Windows PE32+ DLL and the existing Linux GitNexus native module is an x86-64 ELF shared object.
- Reused the existing Linux GitNexus 1.6.9 installation under the user's NVM tree; no package was installed or upgraded.
- Added a user-local shim at `~/.local/bin/gitnexus`. The existing `~/.profile` already places `~/.local/bin` before inherited Windows paths, so fresh WSL login shells now resolve the Linux CLI without changing the frontend Node runtime.
- Refreshed the stale repository index from commit `d91b76e` to current commit `2a4c1a0`.
- Created the approved bilingual workflow-training design and implementation-plan documents. No application source symbol was modified.

### GitNexus verification

- `command -v gitnexus` -> `/home/sonev/.local/bin/gitnexus`.
- `gitnexus --version` -> `1.6.9`.
- `gitnexus status` -> up to date on branch `main`, indexed/current commit `2a4c1a0`.
- Reanalysis completed with 9,493 nodes, 16,217 edges, 275 clusters, and 260 flows.
- `gitnexus query workflow-training` returned the SVM script and dataset-training definitions.
- `gitnexus context ResearchPage --file frontend/src/pages/ResearchPage.tsx` returned exact callers, callees, and the `ResearchPage -> ApiError` process.
- Upstream impact for `ResearchPage` is **LOW**: one direct caller (`WorkspacePage`), two impacted symbols through depth two, one affected process, and one affected module.
- `gitnexus detect-changes --scope all --limit 100` -> `No changes detected`; the current changes are documentation-only/untracked and contain no indexed application symbols.

### Executable baseline

- Frontend `npm run typecheck` -> PASS.
- Frontend `npm test -- --run` -> PASS, 34 files and 88 tests.
- Frontend `npm run build` -> PASS; the existing minified chunk-size warning remains (`544.13 kB`).
- `python3 -m compileall -q backend core` -> PASS.
- Project environment: Python 3.12.13, pytest 8.3.4, NumPy 2.2.6, OpenCV headless 4.13.0.92, and scikit-learn 1.7.1.
- Research API baseline with `PYTHONPATH=backend` -> PASS, 6 tests and 2 warnings.
- Node registry/workflow execution baseline -> PASS, 18 tests.
- Dataset focused baseline -> 30 passed and 7 failed. The failures are the pre-existing CSV/KNN group already recorded in the prior full-suite baseline: one KNN validation-accuracy mismatch and six CSV preparation/API failures returning HTTP 422 or missing `preparationId`.
- The research API warning set is the existing `python_multipart` pending deprecation and Pydantic protected namespace warning for `model_sha256`.

### Changed scope

- Repository changes are limited to the new bilingual spec/plan documents and this bilingual state checkpoint.
- The GitNexus shim is user-local environment state outside the repository.
- No dependency was installed, no source symbol was edited, and no commit was requested or created.

### Known limitations

- The repository is the normal `main` checkout, not a linked worktree. Execution remained in the user-requested workspace so the existing uncommitted spec/plan documents stayed in scope.
- GitNexus does not report untracked documentation as changed application symbols; `git status` remains the source of truth for these files.
- The seven dataset failures remain baseline regressions and are not repaired in Phase 0.

### Current status

Phase 0 is **complete at its checkpoint**. GitNexus query, context, impact, status, analyze, and change detection are operational in fresh WSL login shells. Baseline evidence and known failures are recorded. Phase 1 must not start until the user explicitly approves continuation.

### Phase 1 — Task 1.1 checkpoint

- Removed registered-model loading, state, props, and registry markup from `ResearchPage`; Models remains the lifecycle workspace.
- TDD evidence: the new ownership test failed on the existing `Model versions` section before implementation, then passed after the minimal removal.
- Focused Research/Models verification: 2 files and 4 tests passed; frontend typecheck passed.
- GitNexus pre-edit impact for `ResearchPage`: LOW, one direct caller, one affected process. Post-edit change detection: MEDIUM aggregate, one changed application symbol and the single `ResearchPage -> ApiError` flow.
- `git diff --check` passed. No commit was requested or created.

### Phase 1 — Task 1.2 checkpoint

- Added a pure comparison state transition used by `ResearchPage`: comparison opens only after an explicit action with at least two selected runs, closes explicitly, and closes automatically when selection falls below two.
- TDD evidence: the transition test failed because the function did not exist, then passed after implementation.
- Focused verification: 3 Research tests passed; frontend typecheck passed; diff check passed.
- GitNexus pre-edit impact remained LOW. Post-edit change detection was MEDIUM aggregate with the existing `ResearchPage -> ApiError` flow; no HIGH/CRITICAL warning occurred.
- No dependency was added and no commit was requested or created.

### Phase 1 — Task 1.3 checkpoint

- Expanded Research search to case-insensitive run ID, experiment ID/name, code revision, and execution target matching while retaining the 200-character query bound.
- Updated the UI placeholder to match the backend contract and added a frontend URL-encoding regression test.
- TDD evidence: backend experiment-ID search and UI copy failed before implementation; the existing service encoding test already passed and required no production change.
- Verification: Research API 6 tests passed with 2 existing warnings; frontend service/page 7 tests passed; typecheck and diff check passed.
- Both pre-edit impacts were LOW. Post-edit change detection was MEDIUM aggregate with one affected frontend flow; no HIGH/CRITICAL warning occurred. No commit.

### Phase 1 — Task 1.4 checkpoint

- Added an authenticated reproducibility-manifest action to every Research run and an accessible modal dialog with loading, error, Escape/focus restoration, JSON download, and advanced raw-data disclosure.
- Added tested helpers for safe manifest loading and sanitized Blob downloads; object URLs are explicitly revoked.
- TDD evidence: tests failed because the component and per-run action did not exist, then passed after implementation.
- Verification: component/page/service 11 tests passed; typecheck and diff check passed.
- Pre-edit impacts for `ResearchPage` and `readReproducibilityManifest` were LOW. Change detection remained MEDIUM aggregate with one frontend flow. No dependency or commit.

### Phase 1 — Task 1.5 checkpoint

- Corrected the domain so `ModelAlias` contains only `candidate` and `champion`; rollback remains a lifecycle action.
- Added versioned rollback preview/confirmation endpoints. Confirmation carries the preview event identity and rejects a stale preview under alias locking.
- Models now loads the rollback preview before displaying confirmation and shows current and target versions explicitly.
- Promotion, preview, rollback, and model listing reject unsupported aliases; a persisted `rollback` alias is rejected explicitly and never reinterpreted.
- TDD evidence covered missing preview, rejected rollback alias, stale preview, persisted invalid alias, frontend request payload, and target-visible confirmation.
- Verification: Research/model API 8 tests passed with 2 existing warnings; frontend lifecycle/Models/NodeInspector 13 tests passed; typecheck, compileall, and diff check passed.
- The invalid persisted-alias test now removes only its own `pcb-invalid-alias-*` fixture aliases before/after execution, preventing shared-database contamination.
- GitNexus aggregate change detection remains HIGH across Tasks 1.1–1.5: 11 files, 23 symbols, and 7 flows. All symbol-specific pre-edit impacts were LOW. The user explicitly approved continuing Task 1.5 after this warning. No commit.

### Phase 1 — Task 1.6 checkpoint

- Added model-version creation timestamps and an append-only lifecycle events endpoint ordered newest first with actor, reason, versions, action, alias, and timestamp.
- Replaced primary raw model JSON with semantic compatibility and validation definition lists; raw evidence remains available only in an advanced disclosure.
- Added lifecycle-history loading and visible text details for every event.
- Added source-run navigation from Models through Workspace to Research, with the run ID carried as the initial Research query.
- TDD evidence: backend event/timestamp tests, frontend event client, structured labels, and source-run query all failed before implementation and passed afterward.
- Focused verification: Research/model API 8 tests passed with 2 existing warnings; Models/Research/service/App 14 tests passed; typecheck, compileall, and diff check passed.
- All Task 1.6 symbol-specific impacts were LOW. No dependency or commit.

---

## Workflow training plan — Phase 1 checkpoint — 2026-08-24

### Completed

- Research no longer loads or renders the model registry; Models is the only lifecycle workspace.
- Run comparison is explicit, closable, and automatically closes when fewer than two runs remain selected.
- Research search now matches run ID, experiment ID/name, code revision, and execution target case-insensitively; UI copy matches the backend contract.
- Every run exposes an authenticated reproducibility manifest dialog with safe load/error states, sanitized JSON download, object-URL cleanup, and advanced raw disclosure.
- Model aliases are limited to `candidate` and `champion`. Rollback is an action with server-side preview identity, stale-preview rejection, required reason, transaction locking, and visible current/target versions.
- Persisted unsupported aliases are rejected explicitly rather than silently displayed or reinterpreted.
- Models presents structured compatibility and validation evidence, created timestamps, source-run navigation, and append-only lifecycle history with actor/reason/version/timestamp data.

### Phase verification

- Frontend full Vitest -> PASS, 35 files and 97 tests.
- Frontend typecheck -> PASS.
- Frontend production build -> PASS. The existing chunk warning remains; the generated JS chunk is 548.76 kB minified.
- Research/model API, research service, and workflow execution focused suite -> PASS, 23 tests with 2 existing warnings.
- Python compileall for backend/core -> PASS.
- `git diff --check` -> PASS.
- Browser accessibility audit was attempted but is **blocked** because the browser connector server is unavailable. No live-page accessibility claim is made; semantic/ARIA behavior is covered by static render tests.

### Risk and scope

- Every existing symbol changed in Phase 1 received upstream impact analysis before edit; all symbol-specific risks were LOW.
- Aggregate GitNexus change detection became HIGH during Task 1.5 because the uncommitted phase spans frontend Research/Models, backend lifecycle policy, tests, and state documents. The user explicitly approved continuing after the HIGH warning.
- No dependency was added and no commit was requested or created.

### Known limitations

- Existing dataset CSV/KNN baseline failures remain outside Phase 1 and were not modified.
- The legacy unversioned rollback endpoint remains for compatibility, but it now rejects unsupported aliases. The Models UI uses the safe `/api/v1` preview-confirmation contract.
- Full browser interaction/audit evidence remains blocked until a browser connector is available.

### Current status

Phase 1 is **complete at its checkpoint** for the approved Research/Models ownership and lifecycle scope. Phase 2 must not start until the user explicitly approves continuation.

### Phase 2 — Task 2.1 checkpoint

- Added typed plugin platform, dataset, training, navigation, result, preview, and descriptor contracts without exposing storage, hardware, Python, or shell execution.
- Added deterministic `buildNodePluginRegistry` validation for valid, duplicate, empty, and malformed node IDs.
- Preserved the exact `getNodeInspectorPlugin(key): NodeInspectorPlugin | null` compatibility API and existing Camera/KNN behavior.
- TDD evidence: all three registry tests failed because the builder did not exist, then passed after implementation.
- Verification: registry/NodeInspector/App 11 tests passed; typecheck and production build passed; diff check passed.
- GitNexus reported symbol-level HIGH impact for `getNodeInspectorPlugin` (NodeInspector, WorkflowEditorPage, App). The user explicitly approved the compatibility-layer strategy before edit. No dependency or commit.

### Phase 2 — Task 2.2 checkpoint

- Moved Camera acquisition and KNN image segmentation inspectors into node-ID folders with descriptor `index.ts` files and co-located tests.
- Removed the obsolete flat inspector paths only after registry imports resolved.
- Preserved existing inspector markup and the compatibility registry lookup.
- Verification: plugin/registry/NodeInspector 11 tests passed; typecheck and production build passed; flat-file absence and diff checks passed.
- Both inspector symbol impacts were LOW. The registry builder is a new unindexed symbol and returned UNKNOWN rather than HIGH. No dependency or commit.

### Phase 2 — Task 2.3 checkpoint

- Added Vite eager build-time discovery for `node-plugins/*/index.ts` with deterministic path ordering and exactly-one-descriptor module validation.
- Added pure plugin/catalog integrity checks for plugin-without-manifest-key and manifest-key-without-plugin failures.
- Workflow Editor validates plugin/catalog integrity before accepting the loaded catalog.
- Backend manifest-key projection already satisfied the new regression test, so no backend production change was added.
- TDD evidence: frontend discovery failed because the module did not exist, then all discovery/integrity tests passed.
- Verification: discovery/registry/NodeInspector/App 15 tests passed; backend schema/node registry 14 tests passed; typecheck, build, and diff check passed.
- WorkflowEditorPage/loadEditor impacts were LOW. The previously approved HIGH compatibility lookup kept its public API unchanged. No dependency or commit.

### Phase 2 — Task 2.4 checkpoint

- Added typed manifest-v2 action and artifact contracts to `NodeManifest`, `AlgorithmDefinition`, backend schema projection, and frontend workflow types.
- Preserved all 102 existing version-1 manifests without mass edits. Legacy v1 artifact strings remain opaque compatible keys; v2 requires strict `{key, schema}` contracts.
- Added strict v2 validation for approved action names, capability parity, dataset keys, execution targets, cancellation flags, artifact directions, keys, and schema IDs.
- Added temporary v2 parser/round-trip fixtures and invalid-contract cases; no production v2 node was introduced in this task.
- TDD evidence: core/backend tests initially failed because v2 types/parser did not exist. The first implementation exposed a real v1 `key:media-type` compatibility case, which was preserved before the suite passed.
- Verification: core node registry/backend workflow schema 20 tests passed; frontend manifest/plugin contract 12 tests passed; typecheck, compileall, and diff check passed.
- GitNexus reported CRITICAL impact for `NodeManifest` and HIGH for `AlgorithmDefinition`. The user explicitly approved modifying both contracts before edit. No dependency or commit.

---

## Workflow training plan — Phase 2 checkpoint — 2026-08-24

### Completed

- Added typed plugin descriptors and optional authenticated platform contexts for dataset, training, and navigation capabilities without exposing direct storage, hardware, Python, or shell execution.
- Preserved the public inspector lookup API while adding deterministic registry validation.
- Moved Camera and KNN inspectors into node-ID folders with co-located descriptors and tests; obsolete flat files were removed.
- Added Vite eager build-time discovery and strict module cardinality checks.
- Added runtime plugin/catalog integrity validation before Workflow Editor accepts a catalog.
- Added backward-compatible typed manifest-v2 actions and artifact contracts across core, backend schema projection, and frontend types.
- Preserved all existing v1 manifests and legacy artifact-string formats; no production node was migrated to v2 in this phase.

### Phase verification

- Frontend full Vitest -> PASS, 40 files and 107 tests.
- Frontend typecheck -> PASS.
- Frontend production build -> PASS. The existing chunk warning remains; generated JS is 550.40 kB minified.
- Core node registry, workflow execution, backend workflow schema, and workflow API focused suite -> PASS, 38 tests with 2 existing warnings.
- Python compileall for backend/core -> PASS.
- `git diff --check` -> PASS.
- Flat inspector paths are absent and node-ID plugin folders are present.

### Risk and scope

- `getNodeInspectorPlugin` had symbol-level HIGH impact. The user approved a compatibility-layer strategy; its public signature and behavior remain unchanged.
- `NodeManifest` had CRITICAL impact (176 symbols, 104 direct dependants) and `AlgorithmDefinition` had HIGH impact (179 symbols). The user explicitly approved modifying both contracts.
- `_load_manifest`, WorkflowEditorPage/loadEditor, AlgorithmDefinitionSchema, and individual inspector impacts were LOW.
- Final aggregate change detection is CRITICAL because Phases 1–2 are uncommitted together and include the approved core manifest-contract changes: 25 indexed files, 128 changed symbols, and 18 affected flows. No dependency was added and no commit was requested or created.

### Known limitations

- No persisted production manifest uses v2 yet; Task 2.4 proves the contract with temporary fixtures only.
- Plugin discovery is build-time eager loading; lazy code splitting is deferred and the existing bundle-size warning remains.
- Browser accessibility audit remains unavailable because the browser connector is not running.
- Existing CSV/KNN baseline failures remain outside this phase.

### Current status

Phase 2 is **complete at its checkpoint** for plugin folders, discovery/integrity, and backward-compatible manifest-v2 contracts. Phase 3 must not start until the user explicitly approves continuation.

---

## Workflow training plan — Phase 3 checkpoint — 2026-08-24

### Completed

- Recovered the uncommitted Phase 3.1–3.4 platform scope from the previous session: core training contracts, strict backend schemas, immutable dataset resolution, authenticated training-job API/service registration, background execution, progress/cancellation/artifact persistence, migration, and recovery tests are present in the working tree.
- Added frontend `TrainingJob`, create payload, dataset binding, progress, artifact, and terminal-status types matching the backend camel-case API contract.
- Added authenticated create/read/cancel service methods for `/api/v1/research/training-jobs` without modifying the shared `apiRequest` transport.
- Added a bounded single-flight training-job poller and React hook with immediate polling, terminal-state cleanup, unmount cleanup, safe errors, create duplicate prevention, and cancellation state.
- Added an accessible algorithm-neutral `TrainingJobPanel` with text status, determinate/indeterminate progress semantics, announced errors, start/cancel/open-run actions, and no algorithm parameter fields.
- Extended the optional node-plugin platform context with authenticated create/read/cancel/open-run capabilities bound to recipe slug, workflow revision, and node instance identity.
- Wired Workflow Editor run navigation through the existing guarded workspace navigation path to Research with the selected run query.
- Added responsive light-theme panel styles using existing CSS and dependencies only.

### TDD evidence

- The initial focused frontend run failed in 3 suites because `training-job-service`, `use-training-job`, and `TrainingJobPanel` did not exist; the existing NodeInspector suite still passed 7 tests.
- After the minimal implementation, one service test exposed a reused consumed `Response` fixture; the fixture was corrected without changing production behavior.
- Final focused frontend run: PASS, 4 files and 14 tests.

### Verification

- Frontend full Vitest: PASS, 43 files and 115 tests.
- Frontend typecheck: PASS.
- Frontend production build: PASS. The existing chunk warning remains; generated JS is 551.08 kB minified.
- Python 3.12 `compileall` for backend/core: PASS.
- Phase 3 core/backend/integration matrix: PASS, 90 tests. This covers contracts, schemas, immutable dataset resolution, job service, progress/cancellation/artifacts, authenticated API, migration, and orphan recovery.
- `git diff --check`: PASS.
- Every Task 3.5 changed file was re-read against the task interfaces; no storage path, hardware access, Python/shell execution, secret, or algorithm-specific training behavior was exposed to frontend plugins.
- No dependency was added and no commit was requested or created.

### Risk and changed scope

- `NodeInspector` impact was LOW: 1 direct caller, 2 affected processes, and 3 total upstream symbols.
- `WorkflowEditorPage` impact was LOW: 1 direct caller and 1 affected process. `WorkspacePage` impact was LOW: 1 direct caller and 1 affected process.
- GitNexus could not resolve the TypeScript interface-only `NodePluginPlatformContext` and `NodePluginTrainingContext` symbols, so their graph risk is UNKNOWN; code search found only the plugin type module and typed plugin props.
- `apiRequest` impact is CRITICAL (62 direct callers, 30 processes, 114 upstream symbols). It was deliberately not modified; the new training service only calls its existing API.
- Final aggregate change detection is CRITICAL because the uncommitted working tree combines Phases 1–3: 30 indexed files, 137 changed symbols, and 18 affected flows. Task 3.5's expected `NodeInspector`, `WorkflowEditorPage`, `WorkspacePage`, and App/API-client flows are included alongside pre-existing Research and manifest-contract changes.

### Environment and known limitations

- The user approved verification in the existing Conda base on Python 3.14.6. The complete pinned requirements could not install because NumPy/scikit-learn pins lack Python 3.14 wheels and the SciPy source dependency required an unavailable Fortran compiler.
- The user then approved a Python 3.14-compatible verification environment: existing NumPy 2.5.2, scikit-learn 1.9.0, and Pydantic 2.13.4; SQLAlchemy 2.0.52; pure psycopg 3.2.3; python-multipart 0.0.20; and the remaining focused backend/test dependencies. `pip check` passed. `backend/requirements.txt` was not modified.
- The final Python matrix emitted 539 Python 3.14/FastAPI/Pydantic compatibility and pending-deprecation warnings. They did not fail tests, but verification is not evidence that the repository's original Python 3.12 pinned environment can be replaced by this Conda base.
- Isolated service tests initially exposed incomplete SQLAlchemy model registration. Three training test modules now import the production database bootstrap registration before constructing ORM entities; no production model or service behavior changed.
- A production manifest-v2 trainable node is intentionally absent until Phase 4; Task 3.5 exposes shared platform UI/client capabilities for a future plugin.
- Live browser accessibility audit remains unavailable because the browser connector is not running. Semantic roles, labels, text states, and error announcements are covered by render tests.
- The existing bundle-size warning remains; no new dependency was introduced.

### Current status

Task 3.5 is **complete and frontend-verified**. Phase 3 is **complete at its checkpoint**: the generic platform can create, progress, cancel, fail, complete, persist verified artifacts, recover orphaned jobs, and expose authenticated frontend controls without SVM-specific behavior. Phase 4 must not start without an explicit affirmative user response.

### Phase 4 — Task 4.1 checkpoint

- Added the first production manifest-v2 package, `svm-image-classifier`, with release/local-CPU identity, train/evaluate/infer/export actions, typed model/metrics/report/confusion/failed-image artifacts, strict parameter validation, and bilingual documentation.
- Preserved all 102 manifest-v1 packages; catalog/runtime/documentation inventory is now 103 packages with exact parity.
- Preserved the reference script defaults: 128×128, HOG 16/8/8/9, StandardScaler, RBF, C=10, gamma=scale, and seed 42. No training behavior exists yet; runtime fails explicitly until Task 4.2/4.3.
- TDD: focused suite initially failed 9 cases because the package was absent; final suite PASS, 34 tests. Compileall and diff check PASS.
- Registry loader/validator impacts were LOW. Aggregate detection remains CRITICAL because Phases 1–4.1 are uncommitted together: 32 indexed files, 140 symbols, 18 flows. No repository dependency or commit.

### Phase 4 — Task 4.2 checkpoint

- Added deterministic bounded OpenCV image decoding, resize, grayscale conversion, and HOG extraction entirely inside the SVM node package.
- Enforced class mapping, allowed extensions, metadata/decoded-pixel limits, sample limits, fail/skip policy, stable class/logical ordering, finite features, and cancellation before every item.
- Failed-image diagnostics expose only logical IDs and safe reasons, never host paths.
- TDD: all 5 feature tests initially failed because `extract_dataset_features` was absent; final SVM contract/feature suite PASS, 9 tests with the expected 8100-feature shape. Compileall/diff check PASS. Aggregate graph scope remains CRITICAL from the shared uncommitted worktree; new SVM symbols are not yet indexed and report UNKNOWN rather than HIGH.

### Phase 4 — Task 4.3 checkpoint

- Added deterministic StandardScaler/SVC fitting, evaluation, stable class report/confusion payloads, trusted artifact persistence, reload, and inference inside the SVM package.
- The deterministic ZIP envelope verifies outer and inner SHA-256, metadata signature, schema, node/package identity, and exact Python/scikit-learn runtime compatibility before trusted pickle deserialization. Untrusted artifacts are rejected before loading; no browser upload path exists.
- TDD: training suite initially failed 3 boundaries because train/artifact APIs and runtime routing were absent; final SVM/core regression PASS, 33 tests. Synthetic 16-image train/evaluate/serialize round trip completed in 0.80 seconds.
- Official scikit-learn documentation confirms native pickle is trusted-source-only and cross-version unsupported. Three scikit-learn 1.9 deprecation warnings for the approved probability contract are recorded; repository target remains 1.7.1. Compileall/diff check PASS.

### Phase 4 — Task 4.4 checkpoint

- Added the discovered SVM plugin with Dataset, Feature extraction, Model, Training, and Results sections, immutable SHA-256 binding input, label-mapping guidance, HOG fast feedback, kernel-dependent fields, shared job hook/panel, and Research navigation.
- Added accessible report and confusion-matrix table fallbacks; no HOG or SVC behavior exists in TypeScript.
- TDD: plugin suite initially failed because inspector/result modules were absent; focused plugin/shared-panel suite PASS, 13 tests. Full frontend PASS, 44 files and 118 tests; typecheck/build PASS. Registry/workflow API PASS, 21 tests.
- Build retains the existing chunk warning; generated JS is 561.91 kB minified. Live accessibility audit was attempted but blocked because the browser connector is unavailable; semantic render tests pass.

### Phase 4 — Task 4.5 checkpoint

- Added a generic runtime adapter that resolves a node by ID, injects immutable dataset handles and a cancellation probe, advances standard progress stages, validates finite metrics, and converts binary/JSON outputs into verified artifacts without importing SVM implementation code.
- Added a bounded background dispatcher factory using worker-owned database sessions; the authenticated create endpoint returns without running training in the request thread.
- Added the explicitly approved local translation from the CRITICAL-impact shared `NodeExecutionCancelled` contract to the training-platform `TrainingCancelled` contract. The exception class and its existing callers were not modified.
- SVM E2E proves completed training, exact dataset/node/package lineage, verified model/report/confusion/failed-image artifacts, Research reproducibility manifest hashes/metrics, safe one-class failure, and cancellation. Final SVM E2E PASS, 3 tests; focused backend/API boundary PASS, 30 tests.

---

## Workflow training plan — Phase 4 checkpoint — 2026-08-24

### Completed

- Converted the Cat/Dog reference intent into a class-agnostic `svm-image-classifier` release node with manifest-v2 actions, immutable datasets, bounded HOG extraction, StandardScaler/SVC training, evaluation, deterministic trusted artifacts, reload/inference, shared frontend controls, and Research lineage.
- Preserved script defaults without hard-coded paths or labels: 128×128, HOG 16/8/8/9, RBF, C=10, gamma=scale.
- Kept algorithm behavior inside the independent node package and orchestration/UI generic.

### Phase verification

- Selected Phase 4 Python SVM/platform/Research/workflow matrix: PASS, 101 tests with Python 3.14 compatibility warnings.
- SVM E2E rerun after lineage assertions: PASS, 3 tests.
- Full frontend Vitest: PASS, 44 files and 118 tests.
- Frontend typecheck and production build: PASS; generated JS is 561.91 kB minified with the existing chunk warning.
- Python compileall, `git diff --check`, and Conda `pip check`: PASS.
- Bounded synthetic train/evaluate/serialize round trip: 0.80 seconds.
- Live accessibility audit was attempted and blocked because the browser connector is unavailable; semantic render tests pass.

### Risk, limitations, and unrelated failures

- `NodeExecutionCancelled` impact is CRITICAL (30 direct dependants, 173 upstream symbols). The user explicitly approved only a local adapter translation; the shared class was not modified.
- New Phase 3–4 symbols are not yet indexed and often report UNKNOWN. Registry loader/validator and existing page symbols analyzed before edit were LOW. Aggregate detection remains CRITICAL because all Phases 1–4 are uncommitted together.
- Native scikit-learn pickle is accepted only from the trusted checksum-verified artifact store after envelope verification. Official documentation states untrusted pickle can execute arbitrary code and cross-version loading is unsupported.
- The complete DEBUG documentation suite remains red in 3 unrelated cases: KNN custom-inspector documentation still contains removed `implementation` metadata, its no-JSON feature-editor README conflicts with a generic JSON assertion, and referenced `scripts/generate_node_docs.py` is absent. These files were not modified in Phase 4; SVM bilingual/registry documentation gates pass.
- Verification used the user-approved Python 3.14-compatible Conda environment recorded in Phase 3, not the repository's exact Python 3.12 pins.

### Current status

Phase 4 is **complete at its checkpoint** for the approved SVM vertical slice. The selected acceptance-critical SVM/platform/frontend matrix passes; the unrelated legacy DEBUG documentation failures remain explicitly open. Phase 5 must not start without an explicit affirmative user response.

### Phase 5 — Task 5.1 checkpoint

- Added strict bounded core/frontend contracts for `aoi.confusion-matrix.v1`, `aoi.table.v1`, `aoi.plot-series.v1`, and authenticated viewer descriptors.
- Added authenticated raw artifact reads at `/api/v1/research/artifacts/{id}` using the training content-addressed store, DB-owned immutable metadata, checksum/length re-verification, no-store/nosniff headers, and safe 404/409 errors without storage URIs.
- TDD: core/API/frontend tests initially failed because contracts, parser, and endpoint were absent; final core/backend PASS 9 tests, frontend PASS 2 tests, typecheck/compileall/diff check PASS.
- `ArtifactStore.read_verified` had HIGH impact (1 direct caller, 8 upstream symbols, 3 model lifecycle processes) and was deliberately not modified; the endpoint calls it unchanged. Aggregate change detection remains CRITICAL from the shared uncommitted worktree.

### Phase 5 — Task 5.2 checkpoint

- Added independent release/v2 `plot-2d-output` and `table-output` packages with explicit preview capabilities, strict platform-schema validation, normalized pass-through outputs, typed artifact contracts, and bilingual documentation.
- Preserved `image-output` and `heightmap-output` IDs. Inventory is now 105 packages: 102 v1 and 3 v2.
- TDD: 5 failures first proved both packages were absent; final registry/runtime/catalog/workflow suite PASS, 31 tests.

### Phase 5 — Task 5.3 checkpoint

- Extended workflow output selection with explicit `plot-2d-preview` and `table-preview` capabilities while preserving legacy `image-preview`, `3d-preview`, `twoD`, `threeD`, `image-output`, and `heightmap-output` compatibility. Generic output pins remain unable to create viewers, even when their runtime output contains a descriptor-shaped value.
- Added strict frontend descriptor validation that accepts only authenticated `/api/v1/research/artifacts/{id}` endpoints, authenticated no-store artifact loading with a 2 MiB client bound, structured JSON validation, supported PNG/SVG media fallback, and loading/error/malformed/oversized states.
- Added accessible confusion-matrix and generic HTML tables plus a bounded `640 × 360` React/SVG plot renderer without new dependencies. Semantic SSR tests cover captions, scoped headers, SVG title/role/label, status, and alert behavior.
- Integrated one independently sized/collapsible Dashboard viewer per explicit node using the existing keyed `outputViewers` preferences. Dashboard integration proves plot/table presence, generic-pin absence, and independent `4×5` / `8×7` preferences.
- TDD RED was confirmed with two selector failures and two absent modules. Final focused frontend PASS 19 tests; full frontend PASS 47 files/130 tests; typecheck and production build PASS. The existing >500 kB chunk warning remains. Live accessibility/performance audit remains blocked because the browser connector is unavailable.

### Phase 5 — Task 5.4 checkpoint

- Projected the SVM per-class classification report inside the SVM package to strict `aoi.table.v1` columns/rows and retained its existing strict `aoi.confusion-matrix.v1` output. Updated the manifest artifact contract and bilingual guidance to connect these outputs to explicit `table-output` and `plot-2d-output` nodes.
- Deliberately did not add Dashboard-specific SVM logic or fabricate viewer endpoints inside the pure node: research artifact IDs exist only after database persistence, and viewer presence remains controlled by explicit workflow-node capabilities.
- Persisted report/confusion artifacts round-trip through the checksum-verified artifact store as `application/json`; API-facing run metadata contains no storage URI. Optional Matplotlib fallback was omitted because typed rendering is complete and static fallback is optional.
- GitNexus impact for both `train_and_evaluate` and SVM `execute` was HIGH (22 upstream symbols, 16 direct, 2 processes, 4 modules). The change was limited to report projection/contract/docs; model, metrics, confusion, cancellation, and persistence behavior were retained. RED produced exactly 3 expected schema failures with 6 surrounding tests passing; focused GREEN PASS 9 tests.

---

## Workflow training plan — Phase 5 checkpoint — 2026-08-24

### Completed

- Delivered authenticated structured artifact viewing, explicit plot/table output nodes, capability-gated Dashboard selection, accessible table/confusion/SVG rendering, bounded malformed/oversized handling, static PNG/SVG fallback support, and independently persisted viewer dimensions.
- Connected SVM output contracts to platform visualization schemas without coupling Dashboard to SVM or allowing generic output pins to create viewers.

### Phase verification

- Visualization/SVM/structured-node matrix: PASS, 20 tests.
- Training backend/integration matrix: PASS, 94 tests with 2 existing dependency warnings.
- Registry/catalog/workflow/API matrix: PASS, 39 tests with 2 existing dependency warnings.
- Frontend Phase 5 focused matrix: PASS, 19 tests; full frontend: PASS, 47 files/130 tests.
- Frontend typecheck/build, Python compileall, and `git diff --check`: PASS. Build retains the existing >500 kB chunk warning.
- DEBUG documentation suite still fails only the same 3 unrelated legacy KNN/generator cases recorded in Phase 4.

### Risk and limitations

- Final aggregate `detect_changes` remains CRITICAL because Phases 1–5 are uncommitted together; after refreshing the index to include untracked packages, repeated final runs reported 35 indexed files, 205 symbols, and 251–294 flows. The refreshed graph includes broad and non-stable false-positive fan-out around common test/symbol names, but the aggregate warning is retained rather than discounted.
- Structured artifact loading is bounded to 2 MiB in the browser; larger valid research artifacts intentionally show a safe error rather than rendering.
- Static fallback is supported when the descriptor endpoint returns PNG/SVG. No additional fallback artifact was generated because Matplotlib output is optional.
- Live accessibility/performance audits could not run without the browser connector; semantic renderer and Dashboard tests pass.

### Current status

Phase 5 is **complete at its checkpoint**. Explicit workflow output nodes control all image/plot/table viewer presence, SVM report/confusion artifacts use the accepted viewer schemas, and all acceptance-critical Phase 5 suites pass. Phase 6 must not start without an explicit affirmative user response.

## Workflow training plan — Phase 6 checkpoint — 2026-08-24

### Completed

- Added authenticated v1 model create/list/get/version/promotion routes while retaining legacy compatibility; Models now creates/selects models, filters completed runs, selects verified artifacts, registers immutable versions, refreshes lifecycle state, and navigates to source runs.
- Registration rejects non-completed runs, failed validation, cross-run artifacts, duplicates, and missing/corrupt artifacts. Artifact selection metadata exposes no storage URI.
- Promotion/rollback retains transactional alias locking and append-only actor/reason/previous/next/timestamp events. Confirmed rollback rejects stale previews and revalidates its target artifact; no `rollback` alias is accepted.
- Production resolution now pins both `ModelBinding` and checksum/length/media-bound artifact bytes. SVM contextual inference verifies the exact immutable binding and signed artifact envelope before bounded HOG inference.
- Added bilingual Phase 6 acceptance evidence and a complete authenticated journey from deterministic SVM training through Research/model/champion resolution to inference and structured viewer schemas.

### Verification

- Acceptance-critical Python matrix: PASS 200 tests; aggregate Phase 6 vertical journey: PASS 1 test.
- Full frontend: PASS 47 files/133 tests; typecheck and production build PASS with the existing >500 kB warning.
- Production Python compile (`backend`, `core`) and `git diff --check`: PASS.
- Full Python tree: 525 passed, 11 unrelated legacy failures, 2 existing dependency warnings. The failures are 3 known DEBUG docs, 1 KNN accuracy fixture, 6 CSV dataset API cases, and 1 settings-backup checksum fixture.
- Whole-test-tree compile additionally encounters the pre-existing invalid `tests/nodes/knn_cat_dog.py` demo import; production code compiles.

### Claim boundary and current status

- Acceptance evidence is limited to deterministic local-CPU cats/dogs fixtures and the exact signed Python/OpenCV/NumPy/scikit-learn runtime. It makes no GPU, factory-accuracy, target-hardware, uptime, or physical-pilot claim.
- Final aggregate `detect_changes` remains CRITICAL because Phases 1–6 are uncommitted together: repeated final runs reported 39 indexed files, 224 symbols, and 251–294 flows. The graph still contains broad, non-stable false-positive fan-out around common test/symbol names; the warning is retained without discounting it.
- Phase 6 is **complete at its checkpoint** because all Phase 6 acceptance-critical tests pass and unrelated failures are explicitly separated. Phase 7 must not start without explicit user approval.

## Workflow training plan — Phase 7 Task 7.1 checkpoint — 2026-08-24

- The user explicitly approved starting Phase 7. Task 7.1 inventoried the React 18/Vite/ES2020 frontend, existing structured/static viewer path, current 574,135-byte minified / 169,441-byte gzip main JavaScript asset, WebGL/browser constraints, and the absence of a production typed 3D payload.
- Added bilingual decision records comparing raw Canvas/WebGL, Plotly.js, Three.js, and React Three Fiber for bounded heightmap and future point-cloud/mesh workloads. No dependency was installed and no package or application source file changed.
- The conditional recommendation is direct Three.js in a dedicated lazy chunk, with authenticated PNG/SVG plus semantic DOM as acceptance-critical fallback. Plotly is rejected for footprint/breadth, raw WebGL for bespoke lifecycle cost, and R3F because React 18 requires the older v8 line and its extra reconciler/dependencies do not benefit one isolated viewer enough.
- Fixed deterministic H-S/H-M/H-L benchmark datasets and future P/M datasets plus pre-implementation budgets for lazy bundle size, first frame, FPS, idle rendering, memory/disposal, context loss, keyboard/reduced-motion behavior, browser support, and minimum/reference hardware.
- GitNexus found no existing 3D execution flow. Task 7.2 must not begin until the user explicitly approves the pinned `three` dependency and bounded heightmap-only implementation boundary. Point-cloud/mesh remain outside the initial implementation scope.

## Workflow training plan — Phase 7 Task 7.2 automated checkpoint — 2026-08-24

- The user approved exact `three@0.185.1`, the bounded heightmap-only scope, production Dashboard integration, and proceeding after GitNexus HIGH/CRITICAL warnings. Added exact dev typings `@types/three@0.185.0`; MIT/license gate and post-install audit pass with zero known production vulnerabilities.
- Added strict Python/TypeScript `aoi.heightmap.v1` contracts capped at 512 × 512 with finite-or-null samples, positive spacing and schema-kind matching. Added capability-driven persisted descriptor routing without changing the legacy no-descriptor 3D placeholder.
- Added a dedicated lazy Three.js canvas with render-on-demand, DPR cap 2, bounded indexed buffers, native pointer/wheel/keyboard controls, responsive sizing, context failure/loss status, restoration, and explicit disposal. Semantic grid/sample/range/spacing/unit summary remains available outside canvas; authenticated PNG/SVG fallback path remains intact.
- TDD/focused verification passes 19 tests. Full frontend passes 48 files / 140 tests; TypeScript, production build, Python production compile/direct contract assertions, dependency audit and `git diff --check` pass. Python pytest could not run because `/usr/bin/python3` lacks pytest.
- Build evidence: main 579.26 kB / 172.99 kB gzip (+5.13 kB / +3.55 kB gzip); lazy heightmap chunk 518.85 kB / 130.00 kB gzip. Size budgets pass. Deterministic H-S/H-M/H-L model checks finish in 109 ms total and packed H-L position/index data stays below 10 MiB.
- Browser/hardware latency, FPS, resize, context-loss, heap-recovery and Safari/Chrome/Edge/Firefox matrix remain pending; interactive 3D is conditionally accepted, not production-hardware accepted. Point-cloud and mesh remain out of scope.
- Final aggregate GitNexus detection is CRITICAL: 41 indexed files, 224 symbols and 294 flows across the combined uncommitted Phases 1–7 worktree, including known false-positive fan-out.
