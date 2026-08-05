# Workflow Editor Design

**Date:** 2026-08-05

**Status:** Approved

**Companion translation:** `2026-08-05-workflow-editor-design.md.vn`

## 1. Purpose

AOI Studio needs an editable inspection workflow without claiming that image-processing or anomaly-detection runtimes are already installed. This milestone adds:

- a collapsible Inspection flow panel on the dashboard;
- a settings action that opens a dedicated Workflow editor workspace;
- a typed, directed acyclic graph editor with a free-position canvas and a separate execution-order list;
- an algorithm catalog owned by `core/`;
- authenticated REST endpoints that expose the catalog and persist recipe workflows as atomic JSON files with revision checks.

This milestone is configuration-only. It does not install OpenCV, PyTorch, Anomalib, model weights, training data, or inference implementations.

## 2. Approved Scope

### 2.1 Dashboard Inspection flow

- The panel starts expanded and can be collapsed or expanded like Project explorer.
- A settings button opens the dedicated Workflow editor workspace.
- When collapsed on a wide workspace, the panel becomes a narrow action rail and releases its former width to the dashboard.
- At narrow workspace widths, the panel remains in normal document flow and collapses to a compact header rather than creating horizontal document overflow.
- Collapse and settings controls have accessible names, visible keyboard focus, and a minimum accessible control height.
- The panel reads the saved active workflow instead of using a hard-coded frontend step list.
- Because runtime execution is outside this milestone, configured nodes use an explicit `Configuration only` state. Existing simulated production status must not imply that an algorithm implementation is available.

### 2.2 Dedicated Workflow editor

- The editor is a first-class `workflow-editor` workspace view.
- It is reachable from the Inspection flow settings button and the Project explorer Workflow item.
- The header provides Back to workspace, recipe identity, revision, validation/dirty state, Auto order, and Save changes controls.
- The editor has four coordinated regions:
  1. searchable and categorized algorithm catalog;
  2. node graph canvas;
  3. selected-node inspector;
  4. execution-order list.
- `@xyflow/react` provides node positioning, handles, edges, zoom, pan, fit view, controls, and a desktop minimap.
- React Flow is an interaction layer only. Persisted workflow data uses AOI-owned schemas and does not expose React Flow internal types through the API.

### 2.3 Graph editing

- Users can drag a catalog item onto the canvas or use an Add button.
- Users can move nodes freely on the canvas. Canvas coordinates are presentation metadata and do not determine execution order.
- Users can connect an output handle to an input handle by dragging an edge.
- A connection is accepted only when:
  - source and target nodes both exist;
  - source and target ports exist;
  - the source is an output and the target is an input;
  - both ports have the same standard data type;
  - a non-variadic input does not already have a connection;
  - the edge is not a duplicate or self-loop;
  - adding it does not create a cycle.
- Users can select and remove edges. Removing an edge leaves the target port unconnected.
- Users can remove nodes. If dependent edges exist, the UI identifies the affected connections and requires explicit confirmation before removing the node and those edges.
- Selecting a node opens its inspector. Users can edit the node display name, algorithm parameters, and port display labels.
- Standard port types and required algorithm ports are catalog-owned and cannot be changed or removed in the editor.
- Only catalog ports marked `variadic` can create or remove additional port instances. Decision fusion uses variadic score inputs.
- Every pointer-based action has a keyboard/form alternative:
  - Add button for catalog drag;
  - source-output combobox for edge drag;
  - Move up and Move down buttons for execution-order drag;
  - explicit Delete connection and Delete node buttons.

### 2.4 Execution order

- Execution order is stored separately from canvas position.
- The list supports drag reordering and Move up/Move down buttons.
- Draft order may temporarily be invalid while editing.
- Save is disabled until every source dependency appears before its consumer.
- Auto order applies a stable topological sort. When multiple nodes are independent, their current relative order is preserved.
- Graph cycles are blocked when an edge is proposed and are also rejected by core validation on save.

### 2.5 Persistence and concurrency

- The active recipe slug for this milestone is `rev-c-mainboard`.
- Workflows are stored below `data/projects/<recipe-slug>/workflow.json` using project-relative path resolution.
- Writes use a temporary sibling file, flush and `fsync`, then atomic replacement.
- The workflow has a non-negative integer `revision`.
- A successful update requires the submitted revision to equal the stored revision, increments it by one, and returns the updated workflow.
- A stale update returns HTTP `409 Conflict` with a meaningful message. The frontend keeps the unsaved draft and offers reload; it never silently overwrites newer server data.
- Missing workflow storage creates the defined default workflow in memory and persists it on the first successful update.
- Invalid or unreadable workflow storage returns HTTP `503 Service Unavailable` without exposing filesystem paths.

## 3. Architecture and Ownership

```text
frontend/src/
  pages + components      UI state, React Flow interactions, forms
  services                authenticated API calls
  types                    camelCase API contracts
          |
          | JSON over authenticated REST
          v
backend/app/
  api                     request/response/auth/status codes
  schemas                 Pydantic transport validation
  services                atomic workflow repository adapter
          |
          | imports catalog and graph rules
          v
core/
  algorithms              algorithm and typed-port catalog
  pipeline                workflow domain models, validation, stable topological sort
          |
          v
data/projects/<slug>/workflow.json
```

### 3.1 `core/`

`core/` is the source of truth for algorithm metadata and pipeline correctness. It must not import FastAPI, React, database modules, or filesystem-specific repository adapters.

Core responsibilities:

- define standard data types, port definitions, parameter definitions, algorithm definitions, nodes, connections, and workflows;
- return the immutable algorithm catalog;
- validate workflow structure, typed connections, parameters, cycles, required inputs, and execution order;
- produce a stable topological order;
- provide the default workflow.

### 3.2 Backend

Backend responsibilities:

- authenticate all workflow endpoints;
- map core domain objects to camelCase API schemas;
- validate recipe slugs against `^[a-z0-9]+(?:-[a-z0-9]+)*$` and reject traversal-like values;
- read and atomically write recipe workflow JSON;
- enforce optimistic revision concurrency;
- convert core validation failures to HTTP `422 Unprocessable Entity` and stale revisions to HTTP `409 Conflict`.

### 3.3 Frontend

Frontend responsibilities:

- render catalog and workflow data received from the API;
- manage an unsaved local draft;
- provide immediate interaction feedback using shared API data types and frontend graph helpers;
- submit the complete workflow to backend validation;
- never define an independent business algorithm catalog;
- never claim an algorithm runtime is installed based only on catalog presence.

## 4. Domain Model

### 4.1 Standard port data types

The initial closed type set is:

| Type | Meaning |
|---|---|
| `image` | Single 2D image tensor or matrix |
| `image-set` | Ordered or grouped image collection |
| `mask` | Binary or labeled spatial mask |
| `roi-set` | Named regions of interest |
| `keypoints` | Feature points and descriptors |
| `contours` | Vector contour collection |
| `features` | Learned or handcrafted feature tensor |
| `detections` | Component/object instances |
| `anomaly-map` | Spatial anomaly score map |
| `score` | Scalar or named score set |
| `transform` | Geometric transform or calibration mapping |
| `decision` | `PASS`, `REVIEW`, or `FAIL` evidence/result |

Connections require exact type equality in this milestone. Implicit conversion is not supported.

### 4.2 Algorithm definition

Each catalog entry contains:

- stable kebab-case `id`;
- English `name` and concise operator-facing `description`;
- `category` and documentation group;
- `availability: "configuration-only"`;
- ordered input and output port templates;
- typed parameter definitions with default values, bounds/options, and required flags;
- optional reference label for the source algorithm family described in `docs/algorithm/README.md/algo.md`.

### 4.3 Workflow node

Each node contains:

- unique UUID `id`;
- catalog `algorithmId`;
- editable `displayName`;
- finite canvas `position: { x, y }`;
- parameter values;
- port instances containing stable IDs, catalog template keys, standard types, editable display labels, required state, and variadic-instance metadata.

### 4.4 Connection

Each connection contains:

- unique UUID `id`;
- `sourceNodeId` and `sourcePortId`;
- `targetNodeId` and `targetPortId`.

### 4.5 Workflow

Each workflow contains:

- `recipeSlug`, `recipeName`, `version`, and `revision`;
- `updatedAt` in UTC ISO 8601 format;
- `nodes`;
- `connections`;
- `executionOrder`, containing every node ID exactly once.

## 5. Algorithm Catalog

The catalog is configuration metadata, not runtime registration. Initial entries are grouped as follows.

### 5.1 Acquisition and pipeline components

- Image input
- Camera capture
- ROI extraction
- Global/local stream split
- Score normalization
- Connected-component evidence filter
- Decision fusion
- Decision output

### 5.2 OpenCV-supported configurable tools

- Color conversion
- Resize
- Normalize
- CLAHE
- Gaussian blur
- Median blur
- Bilateral filter
- Global threshold
- Otsu threshold
- Adaptive threshold
- Erode
- Dilate
- Morphology operation
- Canny edges
- Sobel gradient
- Scharr gradient
- Laplacian
- Find contours
- Connected components
- Hough lines
- Hough circles
- Feature detection and matching
- Camera undistortion
- Homography registration
- ECC registration

### 5.3 Group A — Golden/reference comparison

- Absolute difference
- Median–MAD robust difference
- SSIM
- Normalized cross-correlation
- Edge difference
- Gradient difference
- Binary XOR
- Template matching
- Per-pixel Mahalanobis distance
- Golden score fusion

### 5.4 Group B — Feature distribution

- SPADE
- PaDiM
- PatchCore
- AnomalyDINO

### 5.5 Group C — Student–teacher and distillation

- STFPM
- RD4AD
- EfficientAD

### 5.6 Group E — Normalizing flow

- DifferNet
- FastFlow
- CFLOW-AD

### 5.7 Group F — Component and logical inspection

- Golden component matching
- ComAD
- Component relation graph
- UniAD
- Polarity and orientation inspection

The catalog may grow through new core definitions. A new entry must include complete typed ports, parameter constraints, availability, tests, and an English operator description.

## 6. Default Workflow

The default `Rev C · Mainboard` graph demonstrates a valid branch and merge without implying runtime execution:

```text
Image input
  -> ECC registration
      -> Median–MAD robust difference --score--\
      -> PatchCore --------------------score--- Decision fusion -> Decision output
      -> Golden component matching ----score--/
```

The default execution order follows the displayed dependencies. All nodes are labeled `Configuration only`.

## 7. REST API

All endpoints require the existing bearer authentication dependency.

### `GET /api/algorithms`

Returns the catalog as an ordered array. Response: `200 OK`.

### `GET /api/recipes/{recipeSlug}/workflow`

Returns the persisted workflow or the default workflow when no file exists. Responses:

- `200 OK`;
- `422 Unprocessable Entity` for an invalid recipe slug;
- `503 Service Unavailable` for invalid/unreadable persisted data.

### `PUT /api/recipes/{recipeSlug}/workflow`

Accepts the complete workflow draft. Responses:

- `200 OK` with incremented revision;
- `409 Conflict` for a stale revision;
- `422 Unprocessable Entity` with structured graph validation issues;
- `503 Service Unavailable` when persistence fails.

Validation issues contain a stable `code`, an English `message`, and optional `nodeId`, `portId`, or `connectionId`. Initial codes include `unknown-algorithm`, `unknown-node`, `unknown-port`, `duplicate-id`, `duplicate-connection`, `self-loop`, `type-mismatch`, `input-already-connected`, `missing-required-input`, `invalid-parameter`, `cycle`, `execution-order-mismatch`, and `dependency-order`.

## 8. Frontend Interaction and State

- `WorkspacePage` owns the active view and loads workflow data for dashboard/editor consumers.
- Entering the editor fetches catalog and workflow in parallel.
- The editor keeps `savedWorkflow` and `draftWorkflow`; dirty state is derived by comparing their serializable AOI schema values.
- Save is disabled while loading, saving, unchanged, or invalid.
- On successful save, both saved and draft state use the returned incremented workflow.
- Navigating away with unsaved changes requires an in-app confirmation before changing workspace view.
- API and validation failures remain in normal document flow and are announced through `aria-live`.
- Catalog search matches name, description, category, and algorithm ID without case sensitivity.
- Catalog items expose `Configuration only` in text, not color alone.
- The dashboard settings button has the stable label `Configure inspection workflow`.

## 9. Visual and Responsive Design

### 9.1 Tokens and identity

The editor extends the existing light industrial AOI Studio identity:

- Ink `#0B1F33` for primary text;
- Blueprint `#1769E0` for selected nodes and primary actions;
- Signal green `#149B68` for valid state paired with text/icon;
- Warning amber `#B66A00` for draft and validation warnings paired with text/icon;
- Panel `#FFFFFF` for application surfaces;
- Grid `#EEF3F8` for technical canvas structure.

Existing typography remains in use. Utility labels use uppercase tracked text; data and execution indices use Space Grotesk. The distinctive visual element is an execution spine that connects the free-position graph to its deterministic execution-order rail.

### 9.2 Layout behavior

- Wide container: catalog, canvas, and inspector form three columns; execution order spans below them.
- Medium container: catalog becomes a horizontal rail; canvas and inspector form two columns; execution order remains below.
- Narrow container: catalog, bounded canvas, inspector, and execution order stack in normal flow.
- React Flow canvas is a bounded technical region. Its internal node positioning is exempt from application-layout coordinate restrictions; surrounding application components remain in Grid/Flex normal flow.
- The minimap appears only where the canvas has sufficient room.
- The document must not gain unintended horizontal overflow at 390, 768, 1280, or 1920 pixel viewport widths.
- Reduced-motion preferences disable nonessential transitions.

## 10. Error Handling

- Empty catalog: explain that no algorithm definitions are available and provide a retry action.
- Empty workflow: show an invitation to add Image input from the catalog.
- Invalid draft: list actionable graph issues and associate them with nodes/ports where possible.
- Stale revision: preserve the draft and provide Reload server version; do not auto-merge.
- Failed save: preserve the draft and return Save changes to an enabled retry state.
- Unknown algorithm in persisted data: backend rejects the workflow as invalid persisted data instead of dropping the node.

## 11. Testing and Verification

### Core tests

- catalog IDs and port template keys are unique;
- all entries are `configuration-only` and have complete typed metadata;
- valid branched graphs pass;
- type mismatches, missing required inputs, duplicates, self-loops, and cycles fail with stable codes;
- stable topological sorting preserves relative order where possible;
- execution order must contain every node exactly once and place dependencies first.

### Backend tests

- workflow JSON round-trips and writes atomically;
- stale revisions are rejected;
- recipe slug traversal is rejected;
- protected endpoints reject anonymous requests;
- catalog and default workflow contracts are camelCase;
- invalid graphs return structured `422` responses.

### Frontend tests

- graph helpers reject incompatible connections and cycles;
- adding a catalog definition creates a node with catalog defaults;
- reordering and Auto order update execution order deterministically;
- catalog filtering is case-insensitive across all intended fields;
- dirty and save eligibility state reflects validation and revisions.

### Manual browser verification

- dashboard panel expand/collapse and settings navigation;
- catalog-to-canvas drag, node move, edge creation/removal, zoom/pan/fit view;
- execution drag reorder and keyboard alternatives;
- node inspector parameter and port-label editing;
- save success, validation failure, stale-revision handling, and unsaved-navigation confirmation;
- no unintended horizontal overflow at 390, 768, 1280, and 1920 pixels, including a short 390x600 viewport;
- keyboard focus visibility and reduced-motion behavior.

Project verification commands remain:

```bash
bash scripts/test/test.sh
bash scripts/build/build.sh
```

## 12. Explicit Non-Goals

- Running image processing or model inference.
- Installing or importing OpenCV, PyTorch, Anomalib, CUDA, model repositories, or model weights.
- Training, dataset management, threshold calibration, benchmarking, or live runtime telemetry.
- Multi-user collaborative editing, automatic conflict merging, workflow version history, or database persistence.
- Executing the configured graph from Run or Single step controls.
- Arbitrary user-authored Python, scripts, plugins, or unrestricted parameter expressions.

## 13. Future Evolution

When algorithm runtimes are implemented, catalog availability can evolve from `configuration-only` to explicit runtime capability records supplied by core. Runtime work must separately define installation, model artifact provenance, preprocessing contracts, hardware requirements, execution isolation, telemetry, and end-to-end validation against PCB data. The AOI-owned workflow schema and typed ports are intentionally independent of React Flow so that runtime execution or a future editor library does not require replacing persisted recipes.