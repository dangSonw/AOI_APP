# AOI Studio Product Completion Roadmap

> **For agentic workers:** Each phase requires its own detailed implementation plan. Use `superpowers:writing-plans` after the corresponding design scope is approved, then use `superpowers:subagent-driven-development` or `superpowers:executing-plans` task-by-task. Every behavior change follows red-green-refactor.

**Goal:** Turn the current authenticated AOI prototype into a traceable research platform, then a safe PCB/PCBA industrial pilot, then a commercially scalable product.

**Architecture:** PostgreSQL becomes the source of truth for versioned configuration, recipes, experiments, models, audit, and inspection lineage. Filesystem or object storage retains immutable large artifacts. Hardware, Settings, Workflow, Research, and Inspection Database remain separate workspaces with explicit ownership boundaries.

**Tech Stack:** Python 3.12, FastAPI, Pydantic 2, SQLAlchemy 2, PostgreSQL 16, HTTPX, pytest, React 18, TypeScript 5.6, Vite 8, Vitest, shared device contracts, and optional node-specific computer-vision/ML dependencies introduced only by approved node plans.

## Global Constraints

- Keep all code, UI text, API payloads, logs, tests, and repository documentation in English; maintain a `.md.vn` companion for every Markdown file.
- Use relative project paths only.
- Keep live Home, Move, Stop, Clear fault, preview, and commissioning actions in Hardware, not Settings.
- Keep browser access behind the authenticated FastAPI control plane.
- Keep hardware adapters loopback-only and never silently fall back to simulation.
- Store settings/version/audit/lineage metadata in PostgreSQL; store large artifacts outside database rows and verify SHA-256.
- Use one Administrator account initially; defer role-management UI.
- Run GitNexus impact analysis before editing every existing symbol and warn before HIGH or CRITICAL changes.
- Run GitNexus `detect_changes` before every commit and synchronize CodeGraph after each milestone.
- Verify responsive UI at 390, 768, 1280, and 1920 pixels without document-level horizontal overflow.

---

## Phase 0: Foundation Repair and Truthful Baseline

**Outcome:** Remove immediate integrity gaps before building more configuration surfaces.

**Scope:**

1. Disable public registration in single-Administrator mode while keeping a tested bootstrap path.
2. Correct seeded account naming and documentation to Administrator semantics.
3. Return real defect and image evidence in inspection detail.
4. Make camera and motion snapshot loading independent so one unavailable adapter does not hide the other.
5. Fix Settings regional fields so every visible value persists and participates in dirty detection.
6. Replace Workstation ID draft mutation with explicit station-profile selection and load behavior.
7. Add direct `SettingsPage` tests.
8. Add Dataset API/service tests for validation, upload limits, magic bytes, traversal, rename, move, delete, import, and export.
9. Add an audit-event foundation and instrument all existing mutation endpoints.
10. Inventory and add missing `.md.vn` companions in a documentation-only change.

**Exit gates:**

- Single-Administrator mode has no public account creation path.
- Existing mutation APIs emit durable actor/action/result audit events.
- Settings controls shown to users round-trip through backend persistence.
- Inspection details show stored evidence.
- One degraded adapter leaves the other adapter operational.
- Full existing test/build/security suite remains green.

**Required next document:** `docs/superpowers/plans/2026-08-08-foundation-repair-implementation.md`.

---

## Phase 1: PostgreSQL Settings and Version Platform

**Outcome:** Provide one reusable transactional platform for User, Workstation, Recipe, and System scopes.

**Scope:**

1. Add migration tooling compatible with the existing schema bootstrap.
2. Create `settings_documents`, `settings_versions`, `settings_activations`, and `audit_events` tables.
3. Define scope-aware Pydantic schemas with explicit schema versions.
4. Implement immutable version creation, expected-revision conflicts, validation, history, activation, and rollback.
5. Migrate current workstation preferences from file storage without losing user/station identity.
6. Keep JSON import/export as a portable interchange format, not the source of truth.
7. Add structured conflict responses and idempotency keys for apply actions.
8. Add backup/export and migration verification tests.

**Exit gates:**

- Concurrent edits cannot silently overwrite each other.
- Rollback creates a new immutable version.
- Audit and metadata mutation are transactionally consistent where possible.
- Multi-worker backend operation does not depend on process-local locks.
- Existing saved preferences have a documented migration path.

**Required next document:** `docs/superpowers/plans/2026-08-08-settings-platform-implementation.md`.

---

## Phase 2: Complete Settings Workspace

**Outcome:** Deliver all approved Settings sections with safe apply semantics and responsive UX.

**Scope:**

1. Split `SettingsPage` into focused section components and scope-aware hooks/services.
2. Build Overview and Station, Appearance and Locale, Acquisition and Calibration, Motion and I/O Profiles, Inspection Defaults, Compute and Performance, Research and Model Defaults, Data and Retention, Integrations, Notifications, and Security/Audit/Updates.
3. Capability-gate camera and motion fields.
4. Add server validation, dry-run, apply, observed verification, conflict diff, history, and rollback UI.
5. Persist adapter desired profiles and reapply/verify them after restart.
6. Poll only relevant observed status and preserve all dirty drafts.
7. Link live diagnostics and commissioning to Hardware.
8. Add keyboard, accessibility, reduced-motion, loading, empty, error, degraded, and conflict states.

**Exit gates:**

- No disabled milestone Settings navigation remains.
- Every visible setting has a defined scope, persistence contract, validation, and test.
- Failed hardware apply does not mark a version active.
- Settings contains no live motion commands.
- Responsive browser verification passes at all required widths.

**Required next document:** `docs/superpowers/plans/2026-08-08-settings-workspace-implementation.md`.

---

## Phase 3: Hybrid Node Manifest and Inspector Plugin Platform

**Outcome:** Let every node own its runtime/configuration contract while supporting generic and specialized inspector UI.

**Scope:**

1. Define versioned node manifests, capabilities, resource hints, execution targets, artifact contracts, parameter schemas, and migration hooks.
2. Move catalog ownership from the monolithic catalog into node packages; generate the catalog projection from the registry.
3. Extend parameter values beyond scalars with bounded JSON-compatible schema types.
4. Build generic inspector controls for common fields and references.
5. Add a typed custom inspector registry under `frontend/src/node-plugins`.
6. Define custom inspector props and safe authenticated service boundaries.
7. Preserve shared display-name and port management outside custom algorithm panels.
8. Render an empty inspector content area for nodes with no schema and no custom panel.
9. Add registry integrity, migration, backend validation, and frontend plugin tests.

**Exit gates:**

- Exactly one manifest and runtime exist for every registered node.
- Manifest/runtime ports and parameters cannot drift unnoticed.
- Generic and custom inspectors coexist.
- No custom panel directly accesses filesystem paths, adapters, Python, or shell execution.
- Production recipes reject `test` or unsupported node runtimes.

**Required next document:** `docs/superpowers/plans/2026-08-08-node-plugin-platform-implementation.md`.

---

## Phase 4: Research Workspace and Model Registry

**Outcome:** Make AOI experiments reproducible and model promotion controlled.

**Scope:**

1. Define experiment, run, parameter, metric, dataset version, artifact, model, model version, and alias records.
2. Build background job boundaries without committing every node to one execution location.
3. Record code revision, node package version, environment, random seeds, resources, input dataset hashes, parameters, metrics, and outputs.
4. Build Research workspace run search, comparison, charts, artifact browsing, and failure diagnostics.
5. Add model registration, `candidate`, `champion`, and `rollback` aliases.
6. Add validation gates and immutable promotion events.
7. Let trainable custom node inspectors create/open node-context runs and bind model versions.
8. Export reproducibility manifests.

**Exit gates:**

- A run can be reproduced from recorded code/node versions, environment, data hashes, parameters, and seeds.
- A model version has complete experiment and artifact lineage.
- Promotion is auditable and reversible.
- Publishing a production recipe resolves mutable aliases to immutable model versions.

**Required next document:** `docs/superpowers/plans/2026-08-08-research-model-lifecycle-implementation.md`.

---

## Phase 5: Persistent Inspection Orchestrator and Node Execution

**Outcome:** Execute validated workflows safely and persist complete per-node evidence.

**Scope:**

1. Implement the persisted inspection state machine from precheck through completion/fault/cancel.
2. Confirm motion in-position state before capture and verify camera artifacts.
3. Implement a typed node execution context, artifact store, cancellation, timeout, resource allocation, and error contract.
4. Promote a deterministic PCB/PCBA reference vertical slice before broad ML nodes.
5. Persist `inspection_runs` and `inspection_node_runs` with effective versions, parameters, timings, outputs, and errors.
6. Persist real defects, images, evidence, initial decision, and append-only review events.
7. Connect Run control, progress, cancellation, and restart recovery.
8. Add deterministic replay, fault matrix, and soak tests.

**Exit gates:**

- Restart never resumes physical motion automatically.
- Every completed inspection is reproducible from immutable versions and hashes.
- Corrupt, blurred, unregistered, stale-pose, or checksum-invalid input never produces PASS.
- One thousand deterministic simulated runs complete without deadlock or artifact mismatch.

**Required next document:** update or replace the unfinished inspection-runtime portion of `docs/superpowers/plans/2026-08-06-device-adapter-runtime-implementation.md` with a current dedicated plan.

---

## Phase 6: Industrial Pilot Hardening

**Outcome:** Operate one real PCB/PCBA machine or line with commissioning, traceability, integration, and recovery controls.

**Scope:**

1. Implement hardware CSI and UART transports plus acceptance tooling.
2. Implement calibration acquisition, quality metrics, validity, expiry, and production blocking policy.
3. Add PLC handshake and signal mapping.
4. Add MES work-order, serial, lot, recipe, and result exchange.
5. Add optional IPC-CFX and OPC UA integration behind versioned adapters.
6. Enforce retention, quotas, disk preflight, backup, restore dry-run, and disaster recovery.
7. Add time synchronization, health monitoring, notifications, and maintenance windows.
8. Execute performance, reliability, safety, and recovery acceptance on target hardware.

**Exit gates:**

- Hardware interlocks and MCU safety remain authoritative.
- Calibration and profile lineage appears in every inspection.
- Integration outage follows a documented queue/fail-safe policy.
- Backup restore is tested, not only configured.
- Pilot acceptance includes measured cycle time, false-call rate, escape rate, uptime, and recovery time.

**Required next document:** `docs/superpowers/plans/2026-08-08-industrial-pilot-implementation.md` after hardware and factory contracts are known.

---

## Phase 7: Commercial Scale

**Outcome:** Extend the proven pilot into a supportable multi-site product.

**Scope:**

1. Add Operator, Quality Reviewer, Process Engineer, Administrator, and service identities with resource-level permissions.
2. Add SSO and enterprise identity integration where required.
3. Add fleet/site/workstation inventory and centralized health.
4. Add signed application, node, model, and configuration bundles with staged rollout and rollback.
5. Add licensing and entitlement boundaries without blocking machine safety.
6. Add secure, explicit, audited remote-support sessions.
7. Add tenant/site isolation, centralized backup policy, and regional retention.
8. Add commercial observability, service-level objectives, support bundles, and upgrade compatibility tests.

**Exit gates:**

- Permissions follow least privilege and are tested at API boundaries.
- Updates are signed, staged, observable, and reversible.
- A central service outage does not make a safe local station unusable.
- Site data and secrets remain isolated.
- Upgrade tests cover database, settings schemas, node manifests, recipes, models, and artifacts.

**Required next document:** Commercial design begins only after industrial pilot acceptance data is available.

---

## Verification Required After Every Phase

```bash
bash scripts/test/test.sh
bash scripts/build/build.sh
bash -n scripts/run_dev.sh
codegraph sync .
codegraph status .
node .gitnexus/run.cjs detect-changes
git diff --check
```

Run browser verification for changed workspaces at 390, 768, 1280, and 1920 pixels. Run security checks appropriate to introduced dependencies and services. Do not claim phase completion from unit tests alone; verify phase exit gates with end-to-end evidence.