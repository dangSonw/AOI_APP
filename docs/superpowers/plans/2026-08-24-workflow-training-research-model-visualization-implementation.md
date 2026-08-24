# Workflow Training, Research, Model Registry, and Visualization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` task-by-task. Checkboxes record evidence, not intent. After every task run its checkpoint. After every phase, stop and ask the user whether to continue; an agent must not infer approval.

**Goal:** Deliver an auditable workflow-driven training platform, correct Research/Models ownership, a reusable HOG/SVM image-classifier vertical slice, and explicit structured visualization outputs.

**Architecture:** Node packages own algorithm behavior; matching frontend plugin folders own algorithm-specific UI; backend platform services own immutable references, job orchestration, artifacts, research lineage, and model lifecycle. Research manages experiments/runs, Models manages versions/aliases, and explicit output nodes select viewers.

**Tech Stack:** Python 3.12, FastAPI, Pydantic 2, SQLAlchemy 2, PostgreSQL, pytest, NumPy, OpenCV, scikit-learn, React 18, TypeScript 5.6, Vite 8, Vitest, existing workflow/catalog and GitNexus tooling.

**Approved spec:** `docs/superpowers/specs/2026-08-24-workflow-training-research-model-visualization-design.md`

## Global constraints

- Follow `.agents/rules/RULE.md` and `AGENTS.md`; use the required Ubuntu WSL wrapper for Linux commands.
- Preserve unrelated work; never reset, clean, checkout, or overwrite user changes.
- Code/UI/API/tests/logs/comments/English docs use English; every Markdown edit has a `.md.vn` counterpart.
- Use existing dependencies. Dependency installation requires a separate user approval gate.
- Before editing a function/class/method, run GitNexus upstream impact, report direct callers/processes/risk, and stop on HIGH/CRITICAL pending user confirmation.
- Before every optional commit and every phase completion, run GitNexus change detection.
- Use TDD: failing test, confirm expected failure, minimal implementation, focused green test, relevant regression suite.
- Frontend contains presentation and authenticated API calls only; backend owns orchestration/policy; nodes own algorithm behavior.
- Do not remove persisted node IDs/routes until migration and compatibility tests pass.
- Do not start the next phase after a phase checkpoint without an explicit affirmative user response.

## Universal task checkpoint

Every task below ends with these mandatory steps, in addition to its focused commands:

- [ ] Read every file changed by the task and compare it with the task Interfaces block.
- [ ] Run the focused tests named by the task and record counts/exit codes in `docs/superpowers/plans/state.md` and `.md.vn`.
- [ ] Run `git --no-pager diff --check` and inspect `git --no-pager diff -- <task files>`.
- [ ] Confirm `git status --short` contains no unexpected file; do not alter unrelated entries.
- [ ] Run GitNexus change detection when available; record affected symbols/flows and risk. If unavailable, record the exact blocker and do not claim graph verification.
- [ ] If a commit is requested, commit only task files after change detection with the task's Conventional Commit message. Otherwise record `No commit requested`.
- [ ] Mark the task complete only when all expected evidence is present; otherwise mark it Blocked or Partially complete and stop before dependent tasks.

## Universal phase approval gate

At the end of every phase:

1. Run the phase test matrix and acceptance checklist.
2. Re-read all phase changes against the approved spec.
3. Update both state files with Completed, Verification, Changed scope, Known limitations, and Current status.
4. Run `git diff --check`, full phase-relevant tests/build, and GitNexus change detection.
5. Present exact evidence and remaining risks to the user.
6. Ask exactly: **“Phase N has reached its checkpoint. Continue to Phase N+1?”**
7. Stop. Only `Yes/Continue/Proceed` or an unambiguous equivalent authorizes the next phase.

---

## Phase 0 — Tooling and baseline safety

### Task 0.1: Repair and verify Linux GitNexus execution

**Files:** Read `.agents/rules/RULE.md`, `AGENTS.md`, `.claude/skills/gitnexus/**`; modify only the two state files if environment repair needs no repository change.

**Interfaces:**
- Produces: working `query/context/impact/detect_changes` commands against repository `AOI_APP`, or an explicit blocker that prevents Phase 1 edits.

- [ ] Capture `which node`, `node --version`, `npm root -g`, GitNexus binary path, and current index metadata through Ubuntu WSL.
- [ ] Confirm GitNexus does not load a Windows `.node` binary. Do not install a package automatically.
- [ ] If the Linux package is absent or incompatible, report the exact non-interactive install/configuration action and ask for dependency approval.
- [ ] When executable, read repository context and refresh a stale index with the documented GitNexus analyze command.
- [ ] Run a harmless upstream impact for `ResearchPage`, a context query for workflow training, and change detection on the clean baseline.
- [ ] Record command, version, index freshness, and result in both state files.

**Focused verification:** `git --no-pager status --short`; GitNexus context, impact, and change-detection commands must exit successfully.

### Task 0.2: Capture executable baseline

**Files:** Modify `docs/superpowers/plans/state.md` and `.md.vn` only.

**Interfaces:**
- Produces: baseline commands/counts for frontend, research API, node registry, workflow execution, and current SVM script prerequisites.

- [ ] Record git status/diff stat and Python/Node/npm versions.
- [ ] Run frontend typecheck, full Vitest, and production build.
- [ ] Run focused backend research API, core registry/execution, and dataset contract tests using the confirmed Python environment.
- [ ] Compile `backend` and `core` if pytest is blocked; compilation is blocker evidence, not a substitute for tests.
- [ ] Check import availability/version for `cv2`, `numpy`, and `sklearn` without installing anything.
- [ ] Record passing counts, failures, warnings, and unrelated pre-existing failures exactly.

**Focused verification:** `npm run typecheck`, `npm test -- --run`, `npm run build`, applicable pytest commands, and `python -m compileall -q backend core`.

### Phase 0 checkpoint

- [ ] GitNexus impact and change detection are operational; otherwise Phase 1 is Blocked.
- [ ] Baseline evidence and pre-existing failures are recorded bilingually.
- [ ] Working tree contains only expected documentation changes.
- [ ] Ask: **“Phase 0 has reached its checkpoint. Continue to Phase 1?”** and stop.

---

## Phase 1 — Correct Research and Models ownership

### Task 1.1: Remove the duplicate model registry from Research

**Files:** Modify `frontend/src/pages/ResearchPage.tsx`; test `frontend/src/pages/ResearchPage.test.tsx`.

**Interfaces:**
- Produces: `ResearchPage` receives runs only for registry rendering; model lifecycle remains reachable through the Models workspace.

- [ ] Impact-analyze `ResearchPage`; report callers/processes/risk.
- [ ] Add a failing render test asserting Research contains `Research runs` but not `Model versions`, model aliases, or the no-model empty state.
- [ ] Run the focused Vitest test and confirm it fails because the duplicate section is present.
- [ ] Remove model loading/state/markup and unused imports/props from Research; do not alter Models.
- [ ] Run Research and Models page tests and confirm both responsibilities remain covered.

**Focused verification:** `npm test -- --run frontend/src/pages/ResearchPage.test.tsx frontend/src/pages/ModelsPage.test.tsx`.

### Task 1.2: Make comparison an explicit user action

**Files:** Modify/test `frontend/src/pages/ResearchPage.tsx` and `ResearchPage.test.tsx`.

**Interfaces:**
- Produces: comparison-open state; `Compare selected` opens only for at least two selected runs; `Close comparison` closes it.

- [ ] Impact-analyze `ResearchPage` again if the index reports changed symbol context.
- [ ] Add interaction tests for disabled with fewer than two, explicit open, close, and selection removal.
- [ ] Confirm the tests fail because comparison currently appears implicitly and the button has no handler.
- [ ] Implement explicit comparison state and accessible button labels; preserve selected run order.
- [ ] Run focused tests and an accessibility-oriented markup assertion for button state.

**Focused verification:** focused Research Vitest plus frontend typecheck.

### Task 1.3: Align Research search behavior with its promise

**Files:** Modify `backend/app/api/research.py`, integration research API tests, `frontend/src/services/research-service.test.ts`, and Research tests only if placeholder/filter UI changes.

**Interfaces:**
- Consumes: `GET /api/research/runs?query=` compatibility route.
- Produces: case-insensitive matching for run ID, experiment ID/name, code revision, and execution target; maximum query length remains 200.

- [ ] Impact-analyze `search_runs` and frontend `searchResearchRuns`; report blast radius.
- [ ] Add backend failing cases for every documented search field and a non-match.
- [ ] Confirm failures for code revision/execution target before implementation.
- [ ] Extend the SQL predicate without exposing unrestricted JSON/path search.
- [ ] Add/retain frontend request encoding test and make placeholder text exactly match supported fields.
- [ ] Run focused backend/frontend tests.

**Focused verification:** research API test selection and `frontend/src/services/research-service.test.ts`.

### Task 1.4: Expose reproducibility manifests safely

**Files:** Create `frontend/src/components/research/ReproducibilityManifestDialog.tsx` and test; modify Research page/service tests and relevant styles.

**Interfaces:**
- Consumes: `readReproducibilityManifest(accessToken, runId)`.
- Produces: view/download action using an in-memory JSON Blob; no storage URI or host path is added by frontend.

- [ ] Impact-analyze `ResearchPage` and `readReproducibilityManifest`.
- [ ] Write failing tests for load, error, close, and sanitized JSON download filename `<run-id>-reproducibility.json`.
- [ ] Confirm failure because no action/dialog exists.
- [ ] Implement a semantic dialog/details component, loading/error state, Blob URL creation, and URL revocation cleanup.
- [ ] Wire one action per run and keep raw JSON inside an advanced disclosure.
- [ ] Run focused tests, typecheck, and verify keyboard labels.

**Focused verification:** Research/component/service Vitest and typecheck.

### Task 1.5: Correct model alias/action types and rollback preview

**Files:** Modify frontend research types/service/Models page/tests; backend research API/models/schemas or migration; integration research API tests.

**Interfaces:**
- Produces: `ModelAlias = 'candidate' | 'champion'`; rollback is `ModelLifecycleAction`; `GET /api/v1/models/{name}/aliases/{alias}/rollback-preview` returns current and target versions plus stable event identity.

- [ ] Impact-analyze `ModelsPage`, `promote_model`, `rollback_model`, payload helpers, and changed model/schema symbols.
- [ ] Add failing type/service/API tests rejecting alias `rollback`, previewing target, requiring reason, and preventing stale preview execution.
- [ ] Confirm old code accepts/promotes `rollback` or lacks preview.
- [ ] Implement alias validation, transactional preview/execution guard, typed client, and confirmation copy showing current/target.
- [ ] Add an explicit migration/rejection test for any persisted `rollback` alias; never silently reinterpret it.
- [ ] Run focused frontend/backend tests.

**Focused verification:** Models/service Vitest and model lifecycle integration tests.

### Task 1.6: Present structured model evidence and lifecycle history

**Files:** Modify Models page/types/service/tests and backend model payload/event endpoint/tests; relevant responsive CSS.

**Interfaces:**
- Produces: structured compatibility/validation fields, source-run links, and append-only events from `GET /api/v1/models/{name}/events`.

- [ ] Impact-analyze affected payload helpers/endpoints and `ModelsPage`.
- [ ] Write failing API and render tests for event ordering, actor/timestamp/reason, compatibility fields, and advanced raw details.
- [ ] Implement the event endpoint and typed service.
- [ ] Replace primary raw JSON with semantic definition lists/tables; retain advanced raw evidence disclosure.
- [ ] Ensure status is text plus semantic styling, not color alone.
- [ ] Run focused tests, accessibility audit if browser connector is available, typecheck, and build.

### Phase 1 checkpoint

- [ ] Research has no model-registry duplication; compare/search/manifest behavior meets tests.
- [ ] Models owns candidate/champion lifecycle, target-visible rollback, and history.
- [ ] Run full frontend suite/typecheck/build and focused research/model backend integration suite.
- [ ] Update state files and GitNexus change detection scope.
- [ ] Ask: **“Phase 1 has reached its checkpoint. Continue to Phase 2?”** and stop.

---

## Phase 2 — Per-node plugin folders and extensible contracts

### Task 2.1: Define plugin descriptor and context types

**Files:** Modify `frontend/src/node-plugins/types.ts`; create `frontend/src/node-plugins/registry.test.ts`; modify workflow types only when required.

**Interfaces:**
- Produces: `NodePluginDescriptor`, inspector/result/preview plugin types, authenticated platform context, and navigation callbacks; no direct storage/hardware executor.

- [ ] Impact-analyze existing plugin types and `NodeInspector` callers.
- [ ] Write compile/runtime tests for a valid descriptor and rejection of duplicate/empty node IDs.
- [ ] Implement the minimal types and pure registry validation helper.
- [ ] Keep backward adapter support for current inspector function registrations.
- [ ] Run focused tests and typecheck.

### Task 2.2: Move existing inspectors into node-ID folders

**Files:** Move camera and KNN inspector files into `frontend/src/node-plugins/<node-id>/`; add `index.ts` and co-located tests; modify registry imports.

**Interfaces:**
- Consumes: compatibility adapter from Task 2.1.
- Produces: identical `camera-acquisition` and `knn-image-segmentation` behavior from folder descriptors.

- [ ] Impact-analyze both inspector components and registry lookup.
- [ ] Preserve behavior with focused pre-move tests.
- [ ] Move files using node IDs and update imports without changing UI behavior.
- [ ] Add descriptor ID tests and remove obsolete flat files only after all imports resolve.
- [ ] Run plugin, NodeInspector, typecheck, and build tests.

### Task 2.3: Add build-time plugin discovery and integrity validation

**Files:** Modify registry; create discovery module/tests; modify Vite typing declarations if needed; backend/catalog contract tests for manifest custom keys.

**Interfaces:**
- Produces: deterministic descriptor map built from `import.meta.glob('./*/index.ts', { eager: true })`; catalog validation reports duplicate/missing plugin registrations.

- [ ] Impact-analyze registry/catalog normalization symbols.
- [ ] Write failing tests for valid discovery, duplicate ID, plugin without manifest, and manifest custom key without plugin.
- [ ] Implement deterministic discovery and descriptive startup/build errors.
- [ ] Preserve a test-injectable pure function so Vitest does not depend on filesystem ordering.
- [ ] Run frontend registry/catalog/backend registry tests and build.

### Task 2.4: Extend manifest projection with optional v2 actions/artifacts

**Files:** Modify core node models/registry, backend workflow schemas, frontend workflow types, and contract tests.

**Interfaces:**
- Produces: optional `actions`, typed artifact contracts, and supported capabilities while preserving v1 payloads.

- [ ] Impact-analyze every changed model/schema/registry symbol and warn on broad catalog risk.
- [ ] Add failing Python and TypeScript contract fixtures for v1 compatibility and v2 round-trip.
- [ ] Implement strict parsing with unknown action/schema rejection and no change to existing IDs.
- [ ] Add parity tests for manifest/runtime/plugin keys.
- [ ] Run catalog, workflow schema, frontend type, and existing node registry suites.

### Phase 2 checkpoint

- [ ] Existing inspectors behave unchanged from folders; discovery/integrity tests pass.
- [ ] Manifest v1 remains compatible and v2 contracts round-trip.
- [ ] Run frontend full suite/typecheck/build and core/backend registry/contract suites.
- [ ] Update state and change detection.
- [ ] Ask: **“Phase 2 has reached its checkpoint. Continue to Phase 3?”** and stop.

---

## Phase 3 — Training job, immutable dataset, artifact, and progress platform

### Task 3.1: Define training schemas and state transitions

**Files:** Create backend training schemas/service tests and core training contract module/tests; modify research models/migration only after impact analysis.

**Interfaces:**
- Produces: `TrainingJobCreate`, `TrainingJobStatus`, `TrainingProgress`, immutable `DatasetBinding`, allowed transition function, parent-run retry linkage.

- [ ] Impact-analyze ResearchRun models and migration registration.
- [ ] Write failing transition tests for all valid paths and every terminal-state rejection.
- [ ] Implement pure transition validation and Pydantic request/response schemas.
- [ ] Reject client-authored metrics, artifacts, environment, code revision, and terminal status in creation payload.
- [ ] Add database migration/model fields for progress/parent/action identity with upgrade/downgrade tests.
- [ ] Run schema/state/migration tests.

### Task 3.2: Resolve immutable dataset versions

**Files:** Modify dataset service/schema/API as required; create training dataset resolver and tests.

**Interfaces:**
- Consumes: `{datasetId, version}` bindings.
- Produces: server-only immutable dataset handle with item metadata; never returns a host path to frontend.

- [ ] Impact-analyze dataset read/version symbols.
- [ ] Add failing tests for missing/mutable/mismatched versions, class mapping, split metadata, and path traversal.
- [ ] Implement resolver using existing dataset persistence and path utilities.
- [ ] Bound item count, decoded dimensions, and accepted logical media types.
- [ ] Run dataset and security regressions.

### Task 3.3: Implement research training-job API and orchestrator boundary

**Files:** Create versioned research API/service modules and tests; register router; adapt existing ResearchRun persistence.

**Interfaces:**
- Produces: create/read/cancel endpoints; orchestrator receives resolved node action, datasets, parameters, actor, and cancellation token.

- [ ] Impact-analyze app router, research persistence, and node registry loading.
- [ ] Write failing authenticated API tests for create/read/cancel, unknown node/action/target, invalid parameters, and duplicate cancellation.
- [ ] Implement request validation, server-generated run metadata, and transaction-safe state updates.
- [ ] Keep algorithm execution behind a typed callable; do not add SVM logic here.
- [ ] Preserve legacy run-read routes while preventing new client-authored result creation in v1.
- [ ] Run focused API/service tests.

### Task 3.4: Persist progress, cancellation, and verified artifacts

**Files:** Modify/create orchestrator, artifact service, research models/API tests, and background execution integration tests.

**Interfaces:**
- Produces: monotonic stage progress, bounded safe cancellation, content-addressed typed artifacts, terminal failure persistence.

- [ ] Impact-analyze ArtifactStore and background execution symbols.
- [ ] Add failing tests for progress monotonicity, cancel race, checksum/length mismatch, size limit, failure cleanup, and terminal immutability.
- [ ] Implement safe checkpoint callback and atomic artifact record creation.
- [ ] Verify artifact reads and hide storage URI from API payloads.
- [ ] Add restart/recovery behavior that marks orphaned running jobs failed with a stable reason unless a supported worker lease remains.
- [ ] Run service/integration tests.

### Task 3.5: Add authenticated frontend training client and generic job panel

**Files:** Create frontend research-job types/service/tests and shared node-plugin job panel/tests; extend NodeInspector context.

**Interfaces:**
- Produces: create/read/cancel client; bounded polling with cleanup; generic status/progress/error/action UI supplied to custom plugins.

- [ ] Impact-analyze NodeInspector and service client symbols.
- [ ] Write failing tests for payload, polling start/stop, terminal cleanup, cancel, errors, and duplicate-start prevention.
- [ ] Implement service methods and polling hook using existing API client/auth.
- [ ] Add accessible generic panel without algorithm parameter fields.
- [ ] Run focused tests, fake-timer cleanup tests, typecheck, and build.

### Phase 3 checkpoint

- [ ] A fake trainable node can create, progress, cancel, fail, and complete a verified run without SVM-specific platform code.
- [ ] Immutable dataset and artifact security tests pass.
- [ ] Run backend/core integration suites and frontend full suite/typecheck/build.
- [ ] Update state and change detection.
- [ ] Ask: **“Phase 3 has reached its checkpoint. Continue to Phase 4?”** and stop.

---

## Phase 4 — SVM image-classifier vertical slice

### Task 4.1: Add SVM manifest, documentation, and validation contract

**Files:** Create `core/nodes/classification/svm-image-classifier/{__init__.py,node.py,manifest.json,documentation.json,README.md,README.md.vn}` and registry/documentation tests.

**Interfaces:**
- Produces: node ID `svm-image-classifier`; `train/evaluate/infer/export`; dataset inputs and model/metrics/report/confusion outputs.

- [ ] Confirm scikit-learn/OpenCV versions from Phase 0 and impact-analyze catalog/registry validators.
- [ ] Add failing manifest/runtime/documentation parity tests.
- [ ] Implement constants, strict parameter validation, manifest v2, and bilingual documentation without training behavior yet.
- [ ] Validate HOG divisibility, positive dimensions, kernel-dependent fields, bounds, and execution target.
- [ ] Run node registry/documentation tests.

### Task 4.2: Implement bounded image loading and HOG extraction

**Files:** Modify SVM `node.py`; create focused node tests/fixtures under `tests/nodes/`.

**Interfaces:**
- Produces: deterministic `(features, labels, diagnostics)` from immutable dataset items; allowed extensions and fail/skip policy.

- [ ] Impact-analyze new node symbols before subsequent edits as required by project policy.
- [ ] Write failing tests for valid images, corrupt images, unsupported extensions, class order, empty/missing classes, dimension/sample limits, and cancellation.
- [ ] Implement OpenCV decode/resize/grayscale/HOG entirely inside this node.
- [ ] Ensure diagnostics use logical item IDs, never host paths.
- [ ] Run focused tests and deterministic feature-shape assertions.

### Task 4.3: Implement training, evaluation, serialization, and inference

**Files:** Modify SVM node/tests; add artifact round-trip and deterministic dataset fixtures.

**Interfaces:**
- Produces: fitted `Pipeline(StandardScaler?, SVC)`, metrics, report, confusion matrix, model artifact/signature; inference reloads the same signature.

- [ ] Write failing tests matching the script defaults (`128x128`, RBF, `C=10`, `gamma=scale`) and synthetic Cat/Dog-like fixtures.
- [ ] Confirm failure before fitting behavior exists.
- [ ] Implement training/evaluation with stable class order and finite bounded metrics.
- [ ] Serialize with explicit schema/framework/version/preprocessing/HOG/classes/datasets/parameters; reject checksum/signature mismatch on reload.
- [ ] Test round-trip prediction equivalence, cancellation stages, malformed artifact, one-class dataset, and reproducibility.
- [ ] Run focused node/core tests and a bounded benchmark.

### Task 4.4: Build SVM plugin UI

**Files:** Create `frontend/src/node-plugins/svm-image-classifier/` descriptor, types, service adapter, inspector, result view, and tests; update styles.

**Interfaces:**
- Consumes: plugin/training/dataset contracts from Phases 2–3.
- Produces: Dataset, Feature extraction, Model, Training, Results sections and Research navigation.

- [ ] Write failing UI tests for dataset versions, label mapping, HOG validation, kernel-dependent controls, start/cancel/retry, progress, result metrics, and duplicate prevention.
- [ ] Implement controls that update only manifest-declared parameters.
- [ ] Use the shared job client/panel; do not place HOG/SVC behavior in TypeScript.
- [ ] Render confusion matrix/report summaries with accessible text fallback.
- [ ] Run plugin/NodeInspector tests, typecheck, build, and accessibility audit when available.

### Task 4.5: Prove workflow-to-Research SVM integration

**Files:** Add integration tests across workflow, training API, SVM node, artifact store, and Research UI fixtures.

**Interfaces:**
- Produces: configure -> launch -> progress -> complete -> inspect run/artifacts flow.

- [ ] Write a failing end-to-end integration test with immutable synthetic datasets and authenticated user.
- [ ] Run and confirm the first broken boundary.
- [ ] Implement only missing adapters; do not duplicate node logic in backend.
- [ ] Assert run lineage, metrics, artifact checksum, confusion schema, and reproducibility manifest.
- [ ] Test cancellation/failure in the same boundary.
- [ ] Run focused E2E plus all Phase 4 suites.

### Phase 4 checkpoint

- [ ] SVM training matches the intent of `tests/nodes/svm_cat_dog.py` without hard-coded paths/classes.
- [ ] Artifact reload/inference and workflow-to-Research vertical slice pass.
- [ ] Run node/core/backend integration, frontend full suite/typecheck/build, benchmark, docs checks.
- [ ] Update state and change detection.
- [ ] Ask: **“Phase 4 has reached its checkpoint. Continue to Phase 5?”** and stop.

---

## Phase 5 — Structured 2D and table visualization

### Task 5.1: Define viewer payload schemas and artifact endpoint

**Files:** Create core/backend visualization schemas/tests; extend artifact read API without exposing storage paths; update frontend viewer types/tests.

**Interfaces:**
- Produces: `aoi.confusion-matrix.v1`, `aoi.table.v1`, `aoi.plot-series.v1`, typed descriptor, authenticated artifact endpoint.

- [ ] Impact-analyze artifact/viewer selection symbols.
- [ ] Write failing round-trip/security tests for schemas, dimensions, labels, finite values, media fallback, and unauthorized access.
- [ ] Implement strict schemas and safe artifact response.
- [ ] Preserve current image/heightmap compatibility.
- [ ] Run core/backend/frontend contract tests.

### Task 5.2: Add plot-2d-output and table-output nodes

**Files:** Create complete bilingual node packages and runtime/registry/documentation tests.

**Interfaces:**
- Produces: explicit capabilities `plot-2d-preview` and `table-preview`; pass-through/validation behavior for accepted schemas.

- [ ] Add failing manifest/runtime tests for accepted and rejected payloads.
- [ ] Implement independent nodes with no imports from other nodes.
- [ ] Add documentation and artifact contracts.
- [ ] Run registry, documentation, and runtime tests.

### Task 5.3: Render structured viewers on Dashboard

**Files:** Modify viewer selector, Dashboard, preview service, preferences/styles/tests; create plot/table renderer components/tests.

**Interfaces:**
- Produces: one keyed viewer per explicit node; accessible SVG/HTML table; static image fallback; no viewer from generic output pin.

- [ ] Impact-analyze selector, Dashboard, and preference helpers.
- [ ] Add failing tests for zero/one/multiple plot/table/image outputs, fallback, malformed payload, and independent size preferences.
- [ ] Implement renderers with existing React/SVG/HTML only.
- [ ] Keep 3D selection explicit and do not claim interactive 3D.
- [ ] Run focused tests, full frontend suite/typecheck/build, accessibility/performance audits when available.

### Task 5.4: Connect SVM result artifacts to explicit output nodes

**Files:** Modify SVM manifest/runtime adapters and integration tests; add example workflow fixture only if repository conventions support it.

**Interfaces:**
- Produces: SVM confusion matrix -> `plot-2d-output`; classification report -> `table-output`; optional Matplotlib PNG fallback.

- [ ] Write failing integration tests for typed connection compatibility and rendered artifacts.
- [ ] Implement output projection in the SVM node, not Dashboard-specific SVM code.
- [ ] If Matplotlib is unavailable, omit static generation and retain typed rendering; do not install it.
- [ ] Run SVM, workflow type, artifact, and frontend viewer tests.

### Phase 5 checkpoint

- [ ] Explicit output nodes control image/plot/table viewer presence and multiple viewers.
- [ ] SVM results render with accessible structured and fallback output.
- [ ] Run full relevant suites/build/audits and update state/change detection.
- [ ] Ask: **“Phase 5 has reached its checkpoint. Continue to Phase 6?”** and stop.

---

## Phase 6 — Model registration and production lifecycle acceptance

### Task 6.1: Create model and version registration UI

**Files:** Modify Models/Research pages and services/types/tests; backend v1 models API/tests.

**Interfaces:**
- Produces: completed validated run -> create/select model -> select verified run artifact -> immutable version.

- [ ] Impact-analyze model endpoints/pages and payload helpers.
- [ ] Write failing authorization, lineage, integrity, validation, duplicate-name, and UI state tests.
- [ ] Implement creation and registration flows with source-run navigation.
- [ ] Reject artifacts from another run or non-completed/failed validation.
- [ ] Run focused frontend/backend tests.

### Task 6.2: Complete promotion, rollback, and event acceptance

**Files:** Modify lifecycle API/service/pages/tests only as gaps remain after Phase 1.

**Interfaces:**
- Produces: register -> candidate -> champion -> rollback with immutable append-only events and stable preview.

- [ ] Add failing transaction/concurrency and complete UI journey tests.
- [ ] Implement missing locking/revalidation/audit behavior.
- [ ] Assert reason, actor, current/target, timestamps, and no `rollback` alias.
- [ ] Run lifecycle API/UI suites.

### Task 6.3: Prove immutable production binding and inference

**Files:** Modify production resolver/execution only if tests expose gaps; integration tests across model registry, workflow publication/execution, SVM artifact inference.

**Interfaces:**
- Produces: `{modelName, alias}` resolves before execution to `{modelName, modelVersion, artifactSha256}`; runtime verifies exact binding.

- [ ] Impact-analyze production resolver, inspection runtime, and workflow execution symbols; warn if HIGH/CRITICAL.
- [ ] Write failing E2E cases for valid champion, missing alias, changed alias after publication, checksum mismatch, missing artifact, and successful SVM inference.
- [ ] Implement only missing immutable-resolution and verification behavior.
- [ ] Assert past run lineage remains unchanged after later promotion/rollback.
- [ ] Run production execution/integration tests and release validation regressions.

### Task 6.4: Final end-to-end acceptance

**Files:** Create/update bilingual acceptance evidence document and automated journey tests; update state files.

**Interfaces:**
- Produces: dataset -> workflow SVM training -> Research -> model version -> champion -> immutable binding -> inference -> output viewer evidence.

- [ ] Execute the complete journey with deterministic local fixtures and record IDs/checksums/test counts.
- [ ] Execute failure/cancel/rollback journeys.
- [ ] Run full frontend, backend, core, node, integration, contract, documentation, benchmark, typecheck, and build suites.
- [ ] Record unrelated failures separately; do not label the phase complete if acceptance-critical failures remain.
- [ ] Run change detection and compare all implementation scope to this spec.

### Phase 6 checkpoint

- [ ] The complete vertical slice and lifecycle acceptance criteria pass with evidence.
- [ ] No production claim exceeds tested target/runtime/data.
- [ ] Update state and change detection.
- [ ] Ask: **“Phase 6 has reached its checkpoint. Continue to Phase 7?”** and stop.

---

## Phase 7 — Optional interactive 3D evaluation (separate approval scope)

### Task 7.1: Evaluate renderer choices without installing

**Files:** Create bilingual decision record under `docs/superpowers/specs/`; no package change.

**Interfaces:**
- Produces: comparison of existing Canvas/WebGL, Plotly, Three.js, and React Three Fiber for heightmap/point-cloud/mesh, including licenses, bundle, accessibility, performance, testing, and hardware support.

- [ ] Inventory current frontend dependency/bundle and browser/WebGL targets.
- [ ] Fetch official documentation/security/license information for candidates.
- [ ] Define benchmark datasets and acceptance budgets before recommendation.
- [ ] Recommend one option or recommend remaining static-only.
- [ ] Ask for explicit dependency/implementation approval and stop.

### Task 7.2: Implement an approved 3D renderer only after approval

**Files:** Determined by the approved decision record; package files change only with explicit approval.

**Interfaces:**
- Produces: typed heightmap/point-cloud/mesh renderer, fallback image/table, keyboard alternatives, bounded resources.

- [ ] Run impact and dependency security/license gates.
- [ ] Write failing schema, interaction, fallback, malformed/oversized data, performance, and no-WebGL tests.
- [ ] Install exactly the approved pinned dependency non-interactively, or use approved existing APIs.
- [ ] Implement the smallest renderer meeting the recorded budgets.
- [ ] Run full frontend tests/typecheck/build, audits, bundle comparison, and hardware/browser acceptance.

### Final Phase 7 checkpoint

- [ ] Interactive 3D is either accepted with evidence or explicitly deferred; static fallback remains functional.
- [ ] Final state, full verification, and change detection are recorded.
- [ ] Ask: **“Phase 7 has reached its checkpoint. Do you want to close this implementation series or plan another expansion?”** and stop.