# Workflow Training, Research, Model Registry, and Visualization Design

**Status:** Approved direction, pending phased implementation
**Companion translation:** `2026-08-24-workflow-training-research-model-visualization-design.md.vn`
**Implementation plan:** `../plans/2026-08-24-workflow-training-research-model-visualization-implementation.md`

## 1. Purpose

Define the boundaries that let an AOI workflow configure trainable nodes, preserve reproducible research runs, govern immutable model versions, and render explicit 2D or 3D outputs. The first complete vertical slice converts `tests/nodes/svm_cat_dog.py` from a standalone script into a reusable HOG plus SVM image-classification node.

The approved strategy is incremental: correct Research and Models first, establish shared contracts second, prove them with one end-to-end SVM node third, and generalize only after evidence exists.

## 2. Goals

1. Make Research an experiment/run workspace rather than a duplicate model registry.
2. Make Models the single model lifecycle and governance workspace.
3. Keep every `core/nodes/**/node.py` independent and replaceable.
4. Keep node-specific UI in a matching frontend plugin folder.
5. Start, monitor, cancel, inspect, and reproduce training from a selected workflow node.
6. Store immutable dataset, run, artifact, and model lineage.
7. Render viewers only when explicit visualization output nodes exist.
8. Prove the design with an operational SVM image classifier.
9. Stop after every phase and require explicit user approval before continuing.

## 3. Non-goals

- Arbitrary Python, shell, notebook, or filesystem execution from the browser.
- A universal node containing unrelated SVM, KNN, CNN, and anomaly implementations.
- Making node inspectors the only experiment-management UI.
- Training during normal production inspection execution.
- Adding Plotly, Three.js, React Three Fiber, ONNX Runtime, or another dependency without a separate approval gate.
- Deleting legacy node IDs without impact analysis and persisted-workflow migration.
- Claiming interactive 3D before renderer and hardware acceptance evidence exists.

## 4. Mandatory constraints

- Follow `.agents/rules/RULE.md` and `AGENTS.md`.
- Code, UI text, API keys, logs, tests, comments, and English documents use English.
- Every created or modified Markdown document has a `.md.vn` translation.
- Frontend renders UI and calls authenticated services; it contains no training business logic.
- Backend owns validation, persistence, authorization, orchestration, and lifecycle policy.
- Core node packages own algorithm-specific behavior.
- Nodes communicate only through documented contracts and never import another node implementation.
- Existing dependencies are used unless the user explicitly approves a change.
- Run GitNexus upstream impact before changing any function, class, or method. HIGH/CRITICAL risk requires a warning and user decision.
- Run GitNexus change detection before commit or phase-completion claims.

## 5. Current-state review

### 5.1 Research

Research can search runs, select runs, show metrics, lineage, raw parameters/environment, artifacts, and failures. Backend persistence includes experiments, runs, content-addressed artifacts, and reproducibility manifests.

Gaps:

- Search promises code-revision matching, but backend searches only run ID and experiment name.
- `Compare selected` has no click behavior; comparison appears implicitly.
- Research duplicates the Models registry.
- Reproducibility service exists but has no UI action.
- Experiment creation, immutable dataset selection, job submission, cancellation, progress, evaluation, and model registration are not connected.
- `POST /api/research/runs` accepts client-authored status, metrics, and artifacts; it records a ledger entry but does not execute training.

### 5.2 Models

Models shows versions, source runs, integrity, compatibility, aliases, promotion, rollback, reason capture, and the latest event. Workflow inspectors can select validated promoted models.

Gaps:

- Model/version creation has APIs but no complete UI flow.
- Validation and compatibility are mostly raw JSON.
- Rollback confirmation does not identify the target version.
- `rollback` is incorrectly represented as an alias; it is an action on `candidate` or `champion`.
- Complete append-only lifecycle history is absent.

### 5.3 Plugins and visualization

Hybrid manifests and inspectors exist, but custom inspectors are flat files in a central registry and lack dataset/job/result contexts. `image-output` and `heightmap-output` correctly drive explicit viewer selection through capabilities. Runtime payloads remain too narrow for plots, tables, point clouds, meshes, and interactive 3D.

## 6. Ownership boundaries

### Workflow Editor

- Compose and configure nodes.
- Select immutable dataset/model references.
- Launch a declared node capability such as training.
- Show active/recent jobs for the selected node instance.
- Add explicit visualization output nodes.
- Persist portable configuration, not mutable runtime results.

### Research

- Create/inspect experiments; search/filter/compare runs.
- Show progress, lineage, metrics, resources, parameters, datasets, artifacts, and failures.
- Export reproducibility manifests.
- Navigate to source workflow/node.
- Start model registration from a completed validated run.

Research does not own alias promotion or duplicate the model registry.

### Models

- Create model records and immutable versions from verified run artifacts.
- Show compatibility and validation evidence.
- Maintain only `candidate` and `champion` aliases.
- Preview/execute promotion and rollback with a reason.
- Show append-only lifecycle history and source-run links.
- Provide workflow model references.

### Node runtime and plugin

The runtime package owns algorithm validation, preprocessing, training, evaluation, inference, export, and output formatting. A matching frontend plugin owns algorithm-specific configuration/results UI, calls authenticated APIs, and updates only declared configuration. It never loads host paths or executes code.

### Shared platform

The platform owns authentication, immutable-reference resolution, job state, cancellation, resource limits, progress delivery, artifact storage/checksums, research persistence, and model lifecycle policy. It does not contain SVM/HOG-specific behavior.

## 7. Package structure

```text
core/nodes/<category>/<node-id>/
  __init__.py
  node.py
  manifest.json
  documentation.json
  README.md
  README.md.vn

frontend/src/node-plugins/<node-id>/
  index.ts
  inspector.tsx
  inspector.test.tsx
  services.ts
  types.ts
  optional result-view.tsx
  optional preview.tsx
```

Both trees share a stable `nodeId` while preserving Python/Vite boundaries.

## 8. Manifest and plugin contracts

Manifest version 1 remains readable. Version 2 adds optional action and typed artifact contracts:

```json
{
  "manifestVersion": 2,
  "id": "svm-image-classifier",
  "capabilities": ["configure", "train", "evaluate", "infer", "export"],
  "actions": {
    "train": {
      "datasetInputs": ["training-dataset", "test-dataset"],
      "executionTargets": ["local-cpu"],
      "cancellable": true
    }
  },
  "artifactContracts": {
    "outputs": [
      {"key": "model", "schema": "aoi.sklearn-pipeline.v1"},
      {"key": "metrics", "schema": "aoi.classification-metrics.v1"},
      {"key": "confusion-matrix", "schema": "aoi.confusion-matrix.v1"}
    ]
  },
  "inspector": {"kind": "custom", "customKey": "svm-image-classifier"}
}
```

```ts
interface NodePluginDescriptor {
  nodeId: string;
  Inspector?: NodeInspectorPlugin;
  ResultView?: NodeResultPlugin;
  Preview?: NodePreviewPlugin;
}
```

Plugin context includes node/manifest, parameter callback, authenticated dataset and job clients, recipe/revision/node-instance identity, and navigation callbacks. Build-time discovery may replace the central registry only after duplicate/missing registration tests pass. Common display-name and port editing remains outside plugins.

## 9. Training contract and state machine

The browser submits intent, not results:

```json
{
  "experimentId": "cat-dog-svm",
  "recipeSlug": "rev-c-mainboard",
  "workflowRevision": 4,
  "nodeInstanceId": "node-svm-01",
  "nodeId": "svm-image-classifier",
  "nodePackageVersion": "1.0.0",
  "executionTarget": "local-cpu",
  "datasetBindings": {
    "training-dataset": {"datasetId": "cat-dog", "version": "sha256:..."},
    "test-dataset": {"datasetId": "cat-dog-test", "version": "sha256:..."}
  },
  "parameters": {},
  "randomSeeds": {"python": 42, "numpy": 42}
}
```

The server captures code revision, environment, resources, timestamps, metrics, artifacts, and errors. It rejects unknown nodes/actions/targets, mutable or missing datasets, invalid parameters, and unauthorized requests.

```text
queued -> preparing-dataset -> validating -> training
       -> evaluating -> persisting-artifacts -> completed

queued -> cancelled
safe running state -> cancelling -> cancelled
any non-terminal state -> failed
```

Terminal states never transition. Cancellation is checked at bounded safe checkpoints. Retry creates a new run referencing its parent. Initial progress delivery may use bounded polling; SSE/WebSocket is a later optimization.

## 10. API direction

New contracts use `/api/v1`; existing routes remain until migration tests pass.

```text
POST /api/v1/research/experiments
GET  /api/v1/research/experiments
POST /api/v1/research/training-jobs
GET  /api/v1/research/training-jobs/{runId}
POST /api/v1/research/training-jobs/{runId}/cancellations
GET  /api/v1/research/runs
GET  /api/v1/research/runs/{runId}/reproducibility-manifest

POST /api/v1/models
GET  /api/v1/models
POST /api/v1/models/{modelName}/versions
GET  /api/v1/models/{modelName}/events
POST /api/v1/models/{modelName}/aliases/{alias}/promotions
GET  /api/v1/models/{modelName}/aliases/{alias}/rollback-preview
POST /api/v1/models/{modelName}/aliases/{alias}/rollback
```

Only `candidate` and `champion` are aliases. Promotion requires passed validation and a verified artifact. Rollback preview/execution uses transactional history so the displayed target cannot be silently replaced.

## 11. Dataset and artifact integrity

A node receives immutable dataset handles resolved by the platform, never browser-supplied filesystem paths. A dataset version records ID, hash/version, split metadata, class mapping, item count, and integrity metadata.

Artifacts store SHA-256, media type, byte length, schema, source run, and internal storage URI. Host storage paths are not exposed to the browser. Model versions reference only verified artifacts belonging to their completed source run.

## 12. SVM vertical slice

Node ID: `svm-image-classifier`; category: `classification`. It uses configurable HOG features, optional StandardScaler, and scikit-learn SVC. Cats/Dogs are dataset labels, not the node identity.

Dataset settings include immutable train/test versions or deterministic validation split, class mapping, allowed image extensions, invalid-image policy, and sample/dimension limits. Feature settings include `128 x 128` default images, grayscale, and validated HOG window/block/stride/cell/bin values. Model settings include scaler, kernel, `C=10`, `gamma=scale`, degree, class weight, probability, and supported seeds.

Outputs include a reloadable fitted pipeline, class/preprocessing signature, accuracy, classification-report table, structured confusion matrix, failed-image report, timings, and optional PNG/SVG fallback. The artifact preserves framework/node/dataset/parameter/checksum lineage and must reload for inference.

## 13. Visualization contract

A generic output pin never creates a viewer. Initial explicit output nodes are:

- `image-output`: image tensor or PNG/JPEG;
- `plot-2d-output`: line/scatter/histogram/confusion matrix or static fallback;
- `table-output`: typed rows and columns;
- `heightmap-output`: height grid, axes, units, and fallback image;
- later after approval: point-cloud, mesh, and volume outputs.

A viewer descriptor contains node instance, title, kind, schemas, artifact endpoint, dimensions, axes/labels/units, interactions, and fallback media type. Matplotlib runs in Python and emits PNG/SVG; interactive renderers consume typed data, never Python figure objects. The SVM slice uses a structured confusion matrix, report table, and optional static plot. Interactive 3D remains dependency-gated.

## 14. Security, errors, and UX

- Server validation is authoritative; plugin validation is fast feedback.
- Errors expose stable codes and safe messages, not stack traces or host paths.
- Resource limits bound files, bytes, dimensions, samples, runtime, memory, and artifact size.
- Artifact reads re-verify checksum and byte length.
- Audit events append actor, reason, action, previous/next version, and timestamp.
- Production resolves portable aliases to immutable version plus SHA-256 before execution.
- Research/Models use responsive light-theme layouts, semantic headings, keyboard controls, text status, and loading/empty/error states.
- Structured fields are primary; raw JSON is restricted to advanced details.
- Training sections are Dataset, Feature extraction, Model, Training, and Results; actions prevent duplicate submission and expose pending/success/error state.

## 15. Migration and reproducibility

- Manifest v1 and existing inspector keys remain compatible during migration.
- Old API routes remain until caller migration and contract tests pass.
- Persisted `rollback` aliases require explicit migration/rejection, never silent reinterpretation.
- `image-output` and `heightmap-output` IDs remain stable.
- No persisted node ID is removed without impact and migration evidence.
- Every run records experiment, recipe/workflow revision, node instance/package, code revision, immutable datasets, effective parameters, seeds, environment, resources, state times, metrics, warnings, artifacts, terminal error, and actor.
- Downloaded reproducibility JSON contains no secret or host path.

## 16. Delivery phases and mandatory stops

1. Phase 0 — Tooling and baseline safety.
2. Phase 1 — Research/Models ownership correction.
3. Phase 2 — Per-node plugin folders and contracts.
4. Phase 3 — Training-job, dataset, artifact, and progress platform.
5. Phase 4 — SVM image-classifier vertical slice.
6. Phase 5 — Structured 2D/table visualization.
7. Phase 6 — Model registration, promotion, rollback, and production-binding acceptance.
8. Phase 7 — Optional interactive-3D dependency and renderer evaluation.

Every small task ends in a task checkpoint. Every phase ends in a full phase checkpoint, state-document update, and mandatory user question. No worker starts the next phase without an explicit affirmative response.

## 17. Acceptance criteria

- Research contains experiment/run functionality and no duplicate registry.
- Models is the sole lifecycle UI and supports model/version creation, candidate/champion promotion, target-visible rollback, and history.
- Search matches its UI promise; comparison is explicit and accessible.
- Reproducibility manifests are viewable/downloadable.
- A workflow SVM node selects immutable datasets, launches/cancels training, shows progress, and opens its run.
- SVM training produces verified reloadable artifacts, metrics, report, and confusion matrix.
- A validated run becomes an immutable model version and champion binding.
- Production resolves aliases to immutable version plus SHA-256.
- Explicit output nodes control viewer presence.
- Node/plugin independence and manifest-integrity tests pass.
- Relevant frontend, backend, core, integration, build, diff, and GitNexus gates pass.
- No phase proceeds without recorded user approval after the preceding phase checkpoint.