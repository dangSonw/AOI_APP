# AOI Studio UI, Model Binding, Node Hardening, and Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Complete the approved Phase 6–10 roadmap through independently testable gates without overstating incomplete runtime or production evidence.

**Architecture:** Keep frontend presentation/API calls, backend policy/persistence, and core runtime contracts separated. Use portable references in saved workflows and immutable verified bindings at execution. Implement Phase 6, 7, 9, and 10 in order; implement Phase 8 only after its dependency gate.

**Tech Stack:** React 18, TypeScript, Vite, Vitest, FastAPI, Pydantic, SQLAlchemy, pytest, NumPy, OpenCV, existing GitNexus tooling.

## Global Constraints

- Preserve all pre-existing working-tree changes; never reset or overwrite them.
- All repository code, UI text, tests, comments, commit messages, and English docs use English; every modified Markdown file has a `.md.vn` translation.
- Frontend uses light responsive flow layouts and does not place application components with absolute/fixed coordinates.
- Run Linux commands through the required WSL Ubuntu wrapper.
- Run GitNexus upstream impact before changing every function, class, or method; stop on HIGH/CRITICAL risk.
- Run `detect_changes` before any commit.
- Use test-first changes and do not mark a phase complete without acceptance evidence.

---

### Task 0: Tooling and baseline gate

**Files:** Read `.agents/rules/RULE.md`, `AGENTS.md`, `CLAUDE.md`; modify `docs/superpowers/plans/state.md`.

**Produces:** Inventory of pre-existing changes, GitNexus health, test commands, and phase entry criteria.

- [ ] Record `git status --short` and `git diff --stat` without modifying the tree.
- [ ] Repair or explicitly document the GitNexus Linux native dependency so upstream impact runs.
- [ ] Run baseline frontend typecheck/tests and focused backend/core tests; record exact results.
- [ ] Update `state.md` with evidence and blockers; do not claim completion from static inspection.
- [ ] Re-read state and verify no pre-existing change was removed.

### Task 1: Phase 6 Models workspace

**Files:** Create `frontend/src/pages/ModelsPage.tsx` and its test; modify `WorkspacePage.tsx`, `types/workspace.ts`, `ProjectExplorer.tsx`, research service/types, and backend research files only after impact analysis; test API integration and page behavior.

**Produces:** Models list/detail/version view, compatibility display, promotion/rollback action states, reason validation, and audit rendering.

- [x] Write and pass frontend tests for loading/empty rendering, version detail, compatibility, lineage, integrity, and aliases.
- [x] Add the independent Models workspace route, navigation item, page title, and typed use of the existing model API.
- [x] Implement accessible model/version rendering with text status indicators and responsive-flow-compatible existing layout.
- [x] Add promotion/rollback action form with required reason, pending/success/error states, registry refresh, and latest audit event rendering.
- [x] Add typed frontend service tests for promotion and rollback payloads.
- [x] Add backend action tests for rejected validation, missing artifact/version, reason validation, promotion, rollback, and audit event.
- [x] Run frontend typecheck, full Vitest suite, production build, and `git diff --check`; record evidence in state.

### Task 2: Phase 7 compatibility and Node Inspector binding

**Files:** Modify `NodeInspector.tsx`, research/workflow types, `core/algorithms/models.py`, `core/nodes/models.py`, `core/pipeline/validation.py`, and workflow API/schema/service files as required; test frontend, core, and integration flows.

**Produces:** Compatibility-filtered picker, portable saved reference, immutable execution binding, and blocking validation issues.

- [x] Run upstream impact for `NodeInspector`, `Workflow`, and `validate_workflow`; all inspected risks were LOW. Execution-boundary changes remain deferred.
- [ ] Write and pass tests for compatible/incompatible models, missing alias/artifact, pinned version, workflow round-trip, and production rejection.
- [x] Add pure frontend picker filters for task, framework, status, and alias with explicit no-match messaging.
- [x] Add text warnings for unresolved, unvalidated, or unavailable-artifact references and preserve portable alias messaging.
- [x] Add typed frontend `resolveProductionBindings` service and payload test for portable-reference to immutable-binding API integration.
- [ ] Resolve aliases once at the execution boundary and verify immutable version plus SHA-256 before loading in the workflow execution path.
  - [x] Add the core production gate that rejects portable aliases and verifies immutable version/SHA-256 against `NodeExecutionContext`.
  - [x] Connect the database alias resolver to the production workflow invocation for production inspection runs.
- [x] Run focused core/backend tests and full frontend typecheck/tests/build.
- [x] Resolve the research integration regression by isolating and restoring the content-addressed artifact fixture after corruption testing; production behavior was unchanged.


### Task 3: Phase 9 node decomposition and benchmarks

**Files:** Modify/create node packages under `core/nodes/golden-reference/`, `core/nodes/opencv-tools/`, visualization, evidence, and transform families; reuse `core/vision/image_contract.py`; test `tests/core/`, `tests/nodes/`, and deterministic benchmark tests; update package documentation.

**Produces:** One primary algorithm per package with bounded validation, cancellation, score/anomaly outputs, and deterministic metadata.

- [x] Inventory dispatcher algorithms and map each to one package/file.
- [ ] Run upstream impact for each runtime function before extraction.
- [x] Write failing boundary, cancellation, score-bound, and oversized-input tests family by family for the prioritized SSIM/Watershed baseline.
- [ ] Extract one algorithm per module while preserving manifest IDs and public contracts.
- [ ] Add deterministic benchmark fixtures with image size, timing metric, and resource limit.
- [x] Run focused, benchmark, full core/node, and documentation consistency checks.
  - [ ] Full gate remains blocked by 11 unrelated pre-existing regressions outside the node implementation scope.
- [ ] Mark Phase 9 complete only after all prioritized families meet the gate, not only SSIM/Watershed.

### Task 4: Phase 10 RELEASE vertical slice

**Files:** Modify selected pipeline manifests/release validation configuration; create deterministic, edge-case, integration, benchmark, acceptance tests, and release evidence documentation.

**Produces:** A `RELEASE` manifest with evidence references, resource limits, lineage, and production-validator acceptance.

- [x] Select the smallest candidate pipeline and record the rationale in `docs/releases/release-gate-evidence.md`; real-data acceptance remains blocked.
- [ ] Run upstream impact for every validator/execution symbol that will change.
- [ ] Write failing acceptance tests for manifest status, node contracts, lineage, audit evidence, resource limits, and deployment check.
- [ ] Implement only missing release metadata/validation; never bypass DEBUG/TEST rejection.
- [ ] Run deterministic, edge-case, benchmark, integration, and acceptance suites against real fixtures.
- [ ] Generate evidence and mark Phase 10 complete only when every criterion passes.

### Task 5: Phase 8 ONNX runtime gate

**Files:** Modify `backend/requirements.txt` only after dependency/security approval; create/modify core inference contract/runtime and CNN node according to existing conventions; add tensor, checksum, cancellation, memory, CPU/GPU, and benchmark tests; document the runtime lock and artifact contract.

**Produces:** Verified external ONNX artifacts with explicit preprocessing/postprocessing and bounded logits/probabilities/embedding outputs.

- [x] Confirmed ONNX Runtime is unavailable in the approved environment; Phase 8 remains blocked and no dependency was added.
- [ ] Run upstream impact for all modified execution and resolver symbols.
- [ ] Write failing contract/runtime tests before adding dependency or implementation.
- [ ] Implement secure model validation, tensor schema checks, checksum verification, cancellation, and resource limits.
- [ ] Keep the CNN node outside the Basic catalog until acceptance tests pass.
- [ ] Run CPU acceptance and benchmark tests; record GPU status separately and never imply GPU support without hardware evidence.

## Final verification

- [ ] Read every edited/created file and compare the result against the approved spec.
- [ ] Run frontend `npm run typecheck`, `npm test`, and `npm run build`.
- [ ] Run applicable backend/core/integration pytest suites through WSL.
- [ ] Run `git diff --check`.
- [ ] Run GitNexus `detect_changes` and verify only expected symbols and flows are affected.
- [ ] Update `docs/superpowers/plans/state.md` with exact command results, remaining blockers, and phase status.
- [ ] Do not commit until GitNexus detect changes succeeds and the user reviews the resulting scope.

