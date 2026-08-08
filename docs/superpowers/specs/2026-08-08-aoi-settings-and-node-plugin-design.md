# AOI Settings, Node Plugin, and Research Lifecycle Design

## 1. Goal

Define a safe, extensible configuration architecture for AOI Studio that starts as a research platform, grows into a PCB/PCBA industrial pilot, and can later become a commercial multi-site product.

This design completes the Settings information architecture, separates persistent configuration from live machine control, defines per-node inspector extensibility, and establishes traceability boundaries for experiments, models, recipes, calibration, and inspection results.

## 2. Approved Product Direction

- Follow a staged path: research foundation, industrial pilot, then commercial scale.
- Keep the domain architecture general, but use PCB/PCBA as the first reference recipe.
- Keep live camera, motion, and commissioning commands in the Hardware workspace.
- Use Settings for persistent profiles, policies, defaults, validation, version history, apply, and rollback.
- Let each workflow node own its runtime contract and node-specific configuration contract.
- Use a hybrid inspector: generic schema controls for common parameters and custom React panels for complex nodes.
- Use a Research workspace for cross-node experiment and model management; custom node panels deep-link to the relevant experiment or model context.
- Use one Administrator account initially. Do not build role-management UI in the first Settings milestone.
- Store settings, versions, audit records, and lineage metadata in PostgreSQL. Store large images, datasets, models, and artifacts in filesystem or object storage with immutable hashes.

## 3. Current-State Review

### 3.1 Verified Baseline

- CodeGraph index: 250 files, 1,918 nodes, and 4,565 edges; index up to date.
- GitNexus index: current at commit `9435c9a`.
- Backend tests: 34 passed.
- Core tests: 21 passed.
- Integration tests: 24 passed.
- Device contract tests: 16 passed.
- Simulator tests: 19 passed.
- Frontend tests: 22 passed.
- Frontend TypeScript check passed.
- Frontend production build passed.
- Production dependency audit reported zero npm vulnerabilities.

### 3.2 Existing Strengths

- React communicates only with the authenticated FastAPI control plane.
- Device adapters use shared, versioned camera and motion contracts.
- Hardware mode does not silently fall back to simulation.
- Camera artifacts are checked for media type, size, byte length, and SHA-256.
- Workflow and workstation file writes use revision checks and atomic replacement.
- Hardware drafts are protected from one-second polling overwrites while dirty.
- Workflows already have typed ports, cycle validation, stable ordering, and explicit runtime packages.
- User preferences and workflow recipes already have optimistic concurrency concepts that can be preserved when moving to PostgreSQL.

### 3.3 Critical Gaps

#### P0: Product integrity and traceability

1. Public registration creates another authenticated account with the same effective mutation access as the seeded account. This conflicts with the approved single-Administrator MVP.
2. Dataset, workflow, device configuration, inspection review, and other mutations have no durable audit trail.
3. All 58 node runtimes are configuration placeholders; no persisted inspection orchestrator executes the workflow.
4. Inspection detail loads defect and image relationships but returns empty `defects` and `images` arrays.
5. Inspection results do not record complete lineage: workflow revision, node package versions, model version/hash, calibration revision, workstation profile revision, and parameter snapshot.

#### P1: Settings and operational reliability

1. Six of seven Settings sections are disabled.
2. Language, region, units, and clock values exist only in React state. They are not persisted and do not mark the form dirty.
3. Changing Workstation ID mutates the current draft identity instead of loading the destination station profile. A revision from the original station may then cause a conflict or incorrect save behavior.
4. Camera and motion adapter configurations are held in process memory and disappear after adapter restart.
5. Device polling runs every second regardless of active workspace.
6. `readDeviceSnapshot` returns no camera configuration when motion is unavailable, and no motion configuration when camera is unavailable. One degraded adapter hides the usable adapter.
7. `SettingsPage` has no direct component tests.
8. Dataset API and filesystem service have little or no coverage in the main test runner despite broad mutation and upload behavior.
9. Node parameter values support only scalar booleans, numbers, and strings. Complex ROI, model references, dataset selectors, matrices, nested hyperparameters, and artifact policies are unsupported.

#### P2: Scale and maintainability

1. Active recipe and workstation are hardcoded.
2. Password reset is a demo response without a delivery or reset-token lifecycle.
3. File locks protect only one Python process and are not sufficient for multi-worker deployment.
4. API routes are not versioned.
5. Backup, restore, retention enforcement, integration health, signed updates, and drift monitoring are absent.
6. Some existing Markdown files do not have required `.md.vn` companions.

## 4. Domain Boundaries

AOI Studio must not use one Settings document for unrelated ownership scopes.

| Scope | Owner | Examples | Change behavior |
|---|---|---|---|
| User preference | User | locale, units, time format, UI behavior, notification preference | Save immediately or as one user draft |
| Workstation profile | Station administrator | station identity, acquisition profile, calibration references, motion limits, storage and compute limits | Validate, version, apply, audit, rollback |
| Recipe configuration | Process/research owner | workflow graph, node parameters, thresholds, approved model aliases, defect taxonomy | Draft, validate, publish, approve, activate |
| System policy | System administrator | runtime mode, integrations, backup, update, audit, global retention | Validate, version, privileged apply, audit |

Large binary artifacts never live inside setting rows. Database records store artifact IDs, immutable hashes, media metadata, and storage locations.

## 5. Workspace Boundaries

### 5.1 Settings

Settings manages persistent desired state. It supports drafts, validation, version history, apply, conflict detection, and rollback.

### 5.2 Hardware

Hardware manages observed live state and commissioning actions:

- health and capabilities;
- live preview;
- connection diagnostics;
- Home, Move, Stop, and Clear fault;
- test capture;
- calibration acquisition runs;
- profile apply verification.

Settings may link to Hardware but must not embed safety-critical live commands.

### 5.3 Workflow Editor

Workflow Editor owns recipe topology, node instances, port connections, execution order, and node-specific parameters. Global Settings must not duplicate node parameters.

### 5.4 Research

Research owns experiments, training/fine-tuning jobs, evaluations, comparisons, datasets, model registry operations, and promotion decisions. Settings only defines default compute, storage, retention, and registry policies.

### 5.5 Inspection Database

Inspection Database owns immutable run evidence, result search, defect review, review override, and full lineage display.

## 6. Settings Information Architecture

### 6.1 Overview and Station

- Station ID and display name.
- Deployment mode: research, simulation, hardware pilot, or production.
- Active workstation profile and revision.
- Active recipe and published revision.
- Camera, motion, calibration, storage, database, and integration health summary.
- Pending unapplied changes and last successful apply.
- Links to Hardware diagnostics and relevant audit events.

### 6.2 Appearance and Locale

- Display language.
- Region and timezone.
- Metric or imperial units.
- Date and time format.
- Numeric formatting precision.
- Reduced motion and density preferences.

English remains the initial complete UI locale. Adding a locale requires a complete translation catalog, not isolated hardcoded strings.

### 6.3 Acquisition and Calibration

- Camera profile selection and profile version.
- Camera ID, sensor mode, pixel format, ROI, trigger source, exposure, gain, frame rate, white-balance policy, and synchronization options when capability-supported.
- Light-controller profile, channel mapping, intensity limits, sequence timing, and photometric geometry.
- Lens and geometric calibration reference.
- Calibration date, operator, method, residual/error metrics, validity interval, environment, and artifact hash.
- Expiry warning and policy for blocking production when calibration is missing or invalid.
- Link to Hardware for live preview, test capture, and calibration acquisition.

Settings must capability-gate fields. Unsupported controls are omitted or read-only with an explanation; they are not sent to an adapter.

### 6.4 Motion and I/O Profiles

- Motion profile name and revision.
- Maximum velocity, acceleration, settle time, pose tolerance, and axis limits.
- Home policy and safe inspection positions.
- Input/output signal mapping.
- Trigger handshake and timeout policy.
- Door, emergency-stop, communication, and other interlock policy.
- Link to Hardware for Home, Move, Stop, and profile verification.

Physical safety remains enforced by the MCU and hardware layer. Browser settings cannot disable physical safety controls.

### 6.5 Inspection Defaults

- Default active recipe policy.
- Serial and lot input requirements.
- Run timeout and retry policy.
- PASS, REVIEW, and FAIL decision policy.
- Review queue behavior and evidence requirements.
- Result export defaults.
- Defect taxonomy selection.

Algorithm thresholds and model-specific hyperparameters stay in node configuration.

### 6.6 Compute and Performance

- Default execution target per capability: CPU, CUDA GPU, Jetson, or remote worker.
- Maximum concurrent inspections and research jobs.
- Memory and GPU-memory limits.
- Cache location, quota, and eviction policy.
- Worker health and queue limits.
- Determinism policy, random seed policy, and timeout defaults.

Each node declares supported execution targets. A recipe cannot publish when its selected target is unsupported.

### 6.7 Research and Model Defaults

- Dataset storage root and artifact storage policy.
- Experiment tracking backend.
- Model registry backend.
- Default metrics and acceptance templates.
- Checkpoint retention.
- Approved alias naming, including `candidate`, `champion`, and `rollback`.
- Required validation evidence before production promotion.
- Model-signature and input/output contract policy.

This section configures infrastructure and defaults. It does not start jobs.

### 6.8 Data, Retention, Backup, and Restore

- Retention by artifact class: preview, raw capture, canonical image, intermediate evidence, result evidence, dataset, model, and audit.
- Storage quota and disk-pressure thresholds.
- Export format and checksum manifest.
- Scheduled backup target and status.
- Restore validation and dry-run report.
- Legal/quality hold that prevents deletion.

Production deletion must be asynchronous, audited, bounded, and blocked for artifacts referenced by retained inspection or model lineage.

### 6.9 Integrations

- PLC transport and signal mapping.
- MES endpoint and work-order/serial/lot mappings.
- IPC-CFX connection settings for future plug-and-play manufacturing exchange.
- OPC UA endpoint, identity, certificate, namespace, and mapping settings when implemented.
- Time synchronization health.
- Connection test that does not mutate machine state.
- Secret references, never plaintext secret values returned to the browser.

### 6.10 Notifications

- Machine fault and interlock events.
- Camera or motion degradation.
- Calibration expiry.
- Storage pressure and backup failure.
- Research job completion or failure.
- Model drift and quality threshold breach.
- Delivery channel policy and rate limits.

### 6.11 Security, Audit, and Updates

- Single Administrator identity summary for the MVP.
- Session expiry and forced sign-out controls.
- Audit event viewer and export.
- Configuration history, diff, actor, reason, and rollback.
- Signed application/model update policy.
- Maintenance window and rollback status.

Role-management UI is deferred. Database and service interfaces must preserve room for later permission checks without changing every domain service.

## 7. Settings UX Contract

### 7.1 Layout

Use a responsive two-region layout:

```text
wide container
+----------------------+-----------------------------------------+
| scope-aware section  | section title, status, version          |
| navigation           | grouped fields and validation           |
|                      |                                         |
| dirty/apply summary  | sticky-in-container action summary      |
+----------------------+-----------------------------------------+

narrow container
+---------------------------------------------------------------+
| horizontal scrollable section selector                        |
+---------------------------------------------------------------+
| section title, status, version                                 |
| grouped fields                                                 |
| validation and normal-flow actions                             |
+---------------------------------------------------------------+
```

No document-level horizontal overflow. Verify at 390, 768, 1280, and 1920 pixels.

### 7.2 Change Lifecycle

```text
stored version -> draft -> client validation -> server validation
               -> dry-run/apply precheck -> applied version
               -> observed verification -> active
```

- Every draft shows scope, current revision, dirty state, and validation state.
- Navigating away from a dirty section requires explicit discard or save.
- Server conflict returns the latest revision and a structured diff summary.
- Hardware-affecting settings support dry-run and apply verification.
- Failed apply does not mark the desired version active.
- Rollback creates a new version referencing the prior version; history is never rewritten.
- Destructive restore, retention, update, and integration actions require confirmation and a reason.

### 7.3 Status Language

Use explicit labels with icons or shapes: Draft, Valid, Invalid, Applying, Active, Degraded, Failed, Superseded. Never communicate state by color alone.

## 8. Persistence Model

### 8.1 Core Tables

Recommended logical tables:

- `settings_documents`: current identity by scope and subject.
- `settings_versions`: immutable JSONB payload, schema version, revision, status, checksum, creator, reason, and timestamps.
- `settings_activations`: requested version, apply status, observed target revision, diagnostics, and timestamps.
- `audit_events`: actor, action, resource type/ID, request ID, before/after checksums, result, reason, client metadata, and timestamp.
- `recipes`: recipe identity and lifecycle state.
- `recipe_versions`: immutable workflow and node-parameter snapshots.
- `calibrations`: metadata, validity, quality metrics, and artifact references.
- `artifacts`: immutable hash, media type, byte length, storage URI, category, and lifecycle state.
- `experiments`, `experiment_runs`, `run_metrics`, `run_parameters`, and `run_artifacts`.
- `registered_models`, `model_versions`, and `model_aliases`.
- `inspection_runs`, `inspection_node_runs`, `defects`, `inspection_images`, and `review_events`.

### 8.2 Concurrency

- Mutations require an expected revision or ETag.
- PostgreSQL transaction and row-level concurrency replace process-local file locks.
- Immutable version rows are inserted; mutable identity rows point to draft, published, and active versions.
- Apply operations use idempotency keys.
- Audit write occurs in the same transaction as metadata mutation when possible.

### 8.3 Artifact Integrity

- Content-address or uniquely identify artifacts and record SHA-256.
- Verify uploaded size, media type, and checksum before marking ready.
- Never overwrite a ready immutable artifact.
- Persist references before retention cleanup.
- Export includes metadata plus a checksum manifest.

## 9. API Boundaries

Use versioned routes for new contracts. Example resource design:

```text
GET    /api/v1/settings/{scope}/{subjectId}
POST   /api/v1/settings/{scope}/{subjectId}/versions
POST   /api/v1/settings/{scope}/{subjectId}/validate
POST   /api/v1/settings/{scope}/{subjectId}/activations
GET    /api/v1/settings/{scope}/{subjectId}/history
POST   /api/v1/settings/{scope}/{subjectId}/rollback

GET    /api/v1/audit-events
GET    /api/v1/calibrations
POST   /api/v1/calibrations

GET    /api/v1/experiments
POST   /api/v1/experiments/{experimentId}/runs
GET    /api/v1/models
POST   /api/v1/models/{modelId}/versions/{versionId}/promotions
```

API responses use explicit schemas and structured error codes. Frontend never submits arbitrary adapter URLs, filesystem paths, commands, or executable code.

## 10. Hybrid Node Plugin Architecture

### 10.1 Ownership

Each node package owns runtime and configuration metadata:

```text
core/nodes/<category>/<node-id>/
  __init__.py
  node.py
  manifest.py or manifest.json
  optional validation.py
  optional migrations.py

frontend/src/node-plugins/<node-id>/
  inspector.tsx
  inspector.test.tsx
  optional preview.tsx
```

Both trees use the same stable `nodeId`. Colocation is logical rather than mixing JSX into the Python runtime tree. This preserves Python packaging, Vite boundaries, frontend layering, and independent testing.

### 10.2 Node Manifest

A manifest declares:

- node ID, name, category, package version, and schema version;
- input and output ports;
- parameter schema and defaults;
- execution capabilities: configure, infer, train, evaluate, visualize, or export;
- supported execution targets;
- determinism and resource hints;
- artifact input/output types;
- optional custom inspector key;
- migration hooks for older persisted parameters.

The central catalog becomes a registry projection assembled from node manifests rather than the primary owner of every node definition.

### 10.3 Generic Inspector

Generic controls support common values such as:

- boolean, integer, number, text, select;
- multiline text and code-free expression fields;
- range and paired range;
- file artifact reference and dataset reference;
- model/version/alias reference;
- ROI and geometry references;
- color, matrix, and structured object editors when schema-supported;
- conditional visibility and read-only derived values.

Backend validation remains authoritative. Generic frontend validation exists for fast feedback only.

### 10.4 Custom Inspector

Complex nodes may register a custom React panel for ROI drawing, image comparison, training curves, checkpoint selection, feature visualization, or calibration views.

Custom panels:

- receive typed node draft, manifest, capability, validation, and context props;
- update only declared node configuration through provided callbacks;
- call only authenticated backend services;
- never open local files directly by path;
- never control hardware directly;
- never execute arbitrary Python or shell commands;
- preserve generic display-name and port management outside custom algorithm content.

If a node declares neither parameter schema nor custom inspector, the inspector content area is empty as requested. Selection metadata may remain in the shared inspector header.

### 10.5 Registry Integrity

Build and test gates enforce:

- one runtime package per manifest;
- unique node IDs;
- port parity between manifest and runtime;
- parameter key parity between persisted schemas and runtime validation;
- custom inspector registrations reference existing manifests;
- schema migrations cover persisted older versions;
- no production recipe uses a `test` or unsupported runtime;
- no node can publish without declared artifact and execution contracts.

## 11. Research and Model Lifecycle

### 11.1 Research Workspace

The Research workspace provides:

- experiment creation and tagging;
- dataset/version selection;
- parent runs and child runs;
- parameter, metric, system metric, and artifact logging;
- run comparison and filtering;
- checkpoint and model evaluation;
- reproducibility manifest export;
- model registration, versioning, aliases, notes, and lineage;
- candidate validation and controlled promotion.

### 11.2 Node Integration

A trainable node inspector can:

- choose or create an experiment context;
- create a run configuration from node parameters;
- show active and historical jobs for that node type;
- compare candidate metrics;
- bind a recipe node to a model alias or immutable model version;
- open the complete run in Research.

The node inspector does not become the only place to manage experiments. Research provides cross-node and cross-recipe visibility.

### 11.3 Promotion

```text
experiment run -> evaluated model version -> candidate
               -> validation gates -> champion
               -> monitored deployment -> rollback when required
```

Promotion records dataset version, code/node version, parameters, metrics, model signature, artifact hash, approver, reason, and target. A recipe intended for production resolves mutable aliases to immutable model versions when published so past inspections remain reproducible.

## 12. Inspection Traceability Contract

Every completed inspection records:

- station and workstation profile version;
- recipe and workflow version;
- node manifest/package versions;
- complete effective node parameters;
- calibration IDs and hashes;
- camera, light, motion, and I/O profile revisions;
- model versions, aliases at execution time, and artifact hashes;
- input, canonical, intermediate retained evidence, and output hashes;
- per-node start/end time, target, status, metrics, and errors;
- initial decision, review override, actor, reason, and timestamp.

Past evidence is immutable. Review appends an event; it does not erase the original decision.

## 13. Security and Industrial Constraints

- Disable public registration for the single-Administrator MVP; bootstrap or explicit local administration creates the account.
- Keep authentication on every protected read and mutation.
- Log every configuration, recipe, model promotion, review, integration, backup, restore, and update mutation.
- Use least-privilege service credentials and secret references.
- Keep adapters loopback-only unless a later authenticated transport design explicitly changes the boundary.
- Preserve physical interlocks outside browser control.
- Require reason and confirmation for safety-relevant apply, rollback, restore, retention, and update actions.
- Support offline industrial operation; cloud services must not be required for machine safety or basic inspection unless explicitly deployed that way.

## 14. Delivery Decomposition

This design spans independent subsystems and must not be implemented as one large change. Produce separate implementation plans in this order:

1. Foundation repair and audit baseline.
2. PostgreSQL settings/version platform.
3. Complete Settings UI and workstation profile application.
4. Hybrid node manifest and inspector plugin platform.
5. Research experiment tracking and model registry.
6. Persistent inspection orchestrator and node execution.
7. Industrial calibration, integration, retention, backup, and recovery.
8. Commercial fleet, permissions, SSO, licensing, updates, and remote support.

Each plan must use test-driven changes, include GitNexus impact analysis before editing symbols, and end with CodeGraph/GitNexus change detection plus full verification.

## 15. Acceptance Criteria

- All Settings sections are functional or intentionally absent; no disabled milestone navigation remains.
- Every visible setting persists in its correct scope and marks drafts dirty.
- Hardware commands remain outside Settings.
- PostgreSQL provides immutable versions, concurrency checks, audit, activation status, and rollback.
- One unavailable adapter does not hide the other adapter's usable state.
- Node definitions are owned by node manifests and validated against runtimes.
- Generic and custom inspectors coexist; nodes with no inspector contract show an empty content area.
- Research runs record parameters, metrics, artifacts, datasets, code/node versions, and lineage.
- Published recipes resolve all required profiles, calibration, and model versions.
- Completed inspections are reproducible from immutable versions and hashes.
- Responsive Settings and inspector layouts pass at 390, 768, 1280, and 1920 pixels without document overflow.
- Backend, core, integration, contract, simulator, frontend, typecheck, build, and security checks pass.

## 16. External Design References

- NIST SP 800-82 Rev. 3 for OT security that respects safety, reliability, and performance constraints.
- OPC UA role and permission concepts for future resource-level authorization.
- IPC-2591 CFX for interoperable manufacturing data exchange using standard messages.
- MLflow Tracking concepts for experiments, runs, parameters, metrics, models, datasets, and artifacts.
- MLflow Model Registry concepts for model versions, aliases, lineage, tags, promotion, and rollback.