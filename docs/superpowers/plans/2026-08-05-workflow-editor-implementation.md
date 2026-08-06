# Workflow Editor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a revision-safe, configuration-only AOI workflow catalog and typed DAG editor connected to the dashboard.

**Architecture:** Pure Python modules in `core/` own catalog metadata, workflow domain values, validation, and stable ordering. FastAPI maps those values to camelCase schemas and stores one atomic JSON document per validated recipe slug. React owns an unsaved AOI-schema draft and adapts it to `@xyflow/react` only at the canvas boundary.

**Tech Stack:** Python 3.11, dataclasses/enums, Pydantic 2, FastAPI, pytest, React 18, TypeScript 5.6, `@xyflow/react` 12.x, Vitest, CSS Grid/Flex.

## Global Constraints

- Configuration only: do not install or import OpenCV, PyTorch, Anomalib, CUDA, model weights, or inference code.
- Preserve `docs/algorithm/algo.md` and all user algorithm documentation.
- Connections require exact standard-type equality; self-loops, duplicates, occupied non-variadic inputs, and cycles are invalid.
- Persist AOI-owned camelCase JSON under `data/projects/<recipe-slug>/workflow.json`; never persist React Flow internal objects.
- Writes use a sibling temporary file, flush, `fsync`, and atomic replacement.
- Updates require an exact non-negative `revision`; stale updates return HTTP `409` and never overwrite storage.
- All catalog and workflow APIs require the existing bearer authentication dependency.
- UI errors remain in document flow with `aria-live`; controls have visible keyboard focus and text labels.
- Avoid unintended document overflow at 390, 768, 1280, and 1920 px; honor reduced motion.
- Run `bash scripts/test/test.sh` and `bash scripts/build/build.sh` before completion.

## File Map

- `core/algorithms/models.py`: immutable catalog types and parameter/port definitions.
- `core/algorithms/catalog.py`: ordered configuration-only catalog.
- `core/pipeline/models.py`: workflow domain values and validation issues.
- `core/pipeline/validation.py`: graph and parameter validation.
- `core/pipeline/ordering.py`: stable topological ordering.
- `core/pipeline/defaults.py`: valid Rev C · Mainboard default workflow.
- `backend/app/schemas/workflow.py`: camelCase transport schemas and core conversion.
- `backend/app/services/workflow_repository.py`: slug safety, read, revision check, atomic write.
- `backend/app/api/workflows.py`: authenticated catalog/workflow endpoints and status mapping.
- `frontend/src/types/workflow.ts`: API contract types.
- `frontend/src/services/workflow-service.ts`: authenticated workflow requests.
- `frontend/src/utils/workflow-graph.ts`: local graph validation, node construction, ordering, filtering, dirty state.
- `frontend/src/components/workflow/*`: catalog, node, canvas, inspector, and execution rail.
- `frontend/src/pages/WorkflowEditorPage.tsx`: draft lifecycle, save/conflict/navigation orchestration.
- `frontend/src/pages/DashboardPage.tsx`: collapsible saved workflow summary.
- `frontend/src/pages/WorkspacePage.tsx`: active recipe workflow loading and workspace integration.

---

### Task 1: Core Catalog Domain and Definitions

**Files:**
- Create: `core/algorithms/__init__.py`
- Create: `core/algorithms/models.py`
- Create: `core/algorithms/catalog.py`
- Create: `tests/core/test_algorithm_catalog.py`

**Interfaces:**
- Produces: `DataType`, `PortDirection`, `ParameterKind`, `PortDefinition`, `ParameterDefinition`, `AlgorithmDefinition`, `get_algorithm_catalog() -> tuple[AlgorithmDefinition, ...]`, and `get_algorithm_definition(algorithm_id: str) -> AlgorithmDefinition | None`.
- Catalog order follows specification sections 5.1–5.7 and every entry has `availability='configuration-only'`.

- [ ] **Step 1: Write failing catalog contract tests**

```python
def test_catalog_identifiers_and_port_keys_are_unique() -> None:
    catalog = get_algorithm_catalog()
    assert len(catalog) >= 50
    assert len({item.id for item in catalog}) == len(catalog)
    for item in catalog:
        keys = [port.key for port in (*item.inputs, *item.outputs)]
        assert len(keys) == len(set(keys))
        assert item.availability == 'configuration-only'

def test_decision_fusion_accepts_variadic_scores() -> None:
    definition = get_algorithm_definition('decision-fusion')
    assert definition is not None
    assert definition.inputs[0].data_type is DataType.SCORE
    assert definition.inputs[0].variadic is True
```

- [ ] **Step 2: Run the test and verify the missing modules fail**

Run: `conda run -n aoi-app python -m pytest tests/core/test_algorithm_catalog.py -v`

- [ ] **Step 3: Implement frozen domain records and the complete documented catalog**

Use `@dataclass(frozen=True, slots=True)`, tuple collections, kebab-case IDs, bounded numeric parameters, explicit select options, required/default metadata, typed ordered ports, English operator descriptions, and documentation references. Acquisition and pipeline records are included alongside every algorithm named in design section 5.

- [ ] **Step 4: Run catalog tests**

Run: `conda run -n aoi-app python -m pytest tests/core/test_algorithm_catalog.py -v`
Expected: all catalog contract tests pass without importing runtime libraries.

- [ ] **Step 5: Commit**

```bash
git add core/algorithms tests/core/test_algorithm_catalog.py
git commit -m "feat(core): add configuration algorithm catalog"
```

### Task 2: Core Workflow Models, Validation, and Stable Ordering

**Files:**
- Create: `core/pipeline/__init__.py`
- Create: `core/pipeline/models.py`
- Create: `core/pipeline/validation.py`
- Create: `core/pipeline/ordering.py`
- Create: `core/pipeline/defaults.py`
- Create: `tests/core/test_pipeline_validation.py`
- Create: `tests/core/test_pipeline_ordering.py`
- Create: `tests/core/test_default_workflow.py`

**Interfaces:**
- Produces: `Point`, `PortInstance`, `WorkflowNode`, `Connection`, `Workflow`, `ValidationIssue`.
- Produces: `validate_workflow(workflow: Workflow) -> tuple[ValidationIssue, ...]` and `stable_topological_order(workflow: Workflow, preferred_order: tuple[str, ...] | None = None) -> tuple[str, ...]`.
- Produces: `create_default_workflow(recipe_slug='rev-c-mainboard', recipe_name='Rev C · Mainboard') -> Workflow`.

- [ ] **Step 1: Write failing validation and ordering tests**

```python
def test_cycle_and_type_mismatch_have_stable_codes() -> None:
    assert 'type-mismatch' in issue_codes(type_mismatch_workflow())
    assert 'cycle' in issue_codes(cyclic_workflow())

def test_stable_order_preserves_preference_between_ready_nodes() -> None:
    workflow = branched_workflow()
    assert stable_topological_order(workflow, ('source', 'right', 'left', 'merge')) == (
        'source', 'right', 'left', 'merge'
    )

def test_execution_order_contains_every_dependency_first() -> None:
    assert validate_workflow(branched_workflow()) == ()
    assert 'dependency-order' in issue_codes(dependency_after_consumer_workflow())
```

- [ ] **Step 2: Run focused core tests and observe failures**

Run: `conda run -n aoi-app python -m pytest tests/core/test_pipeline_validation.py tests/core/test_pipeline_ordering.py tests/core/test_default_workflow.py -v`

- [ ] **Step 3: Implement complete deterministic validation**

Validate finite positions, UUID-shaped unique IDs, known algorithms and ports, parameter kinds/ranges/options, endpoint existence/direction, exact types, duplicate connections, self-loops, input cardinality, required inputs, cycles, execution-order membership/uniqueness, and dependency ordering. Return issues in deterministic node/connection/rule order using the exact codes from design section 7.

- [ ] **Step 4: Implement Kahn ordering with preferred-order tie breaking and the branched default graph**

The default graph is `Image input → ECC registration → {Median–MAD, PatchCore, Golden component matching} → Decision fusion → Decision output`, revision `0`, version `1`, UTC `updated_at`, and a valid execution order.

- [ ] **Step 5: Run all core tests and commit**

```bash
conda run -n aoi-app python -m pytest tests/core/ -v
git add core/pipeline tests/core
git commit -m "feat(core): validate and order typed workflows"
```

### Task 3: Backend Schemas and Atomic Repository

**Files:**
- Create: `backend/app/schemas/workflow.py`
- Create: `backend/app/services/workflow_repository.py`
- Modify: `backend/app/config/settings.py`
- Create: `tests/backend/test_workflow_schemas.py`
- Create: `tests/backend/test_workflow_repository.py`

**Interfaces:**
- Produces schema classes mirroring all catalog/workflow values and `WorkflowSchema.from_core(...)`, `WorkflowSchema.to_core()`.
- Produces `InvalidRecipeSlug`, `WorkflowStorageError`, `StaleWorkflowRevision`.
- Produces `WorkflowRepository(root: Path)`, `.read(slug: str) -> Workflow`, `.save(slug: str, submitted: Workflow) -> Workflow`.
- Adds `Settings.projects_data_directory: str = 'data/projects'` and `projects_data_path`.

- [ ] **Step 1: Write failing camelCase round-trip and repository tests**

```python
def test_workflow_schema_round_trip_is_camel_case() -> None:
    schema = WorkflowSchema.from_core(create_default_workflow())
    payload = schema.model_dump(mode='json', by_alias=True)
    assert 'recipeSlug' in payload and 'executionOrder' in payload and 'updatedAt' in payload
    assert schema.to_core() == schema.to_core()

def test_save_increments_revision_and_rejects_stale_write(tmp_path: Path) -> None:
    repository = WorkflowRepository(tmp_path)
    saved = repository.save('rev-c-mainboard', create_default_workflow())
    assert saved.revision == 1
    with pytest.raises(StaleWorkflowRevision):
        repository.save('rev-c-mainboard', create_default_workflow())

@pytest.mark.parametrize('slug', ('../secret', 'Rev-C', 'a/b', ''))
def test_recipe_slug_rejects_traversal(slug: str, tmp_path: Path) -> None:
    with pytest.raises(InvalidRecipeSlug):
        WorkflowRepository(tmp_path).read(slug)
```

- [ ] **Step 2: Run focused backend tests and verify failure**

Run: `PYTHONPATH=backend conda run -n aoi-app python -m pytest tests/backend/test_workflow_schemas.py tests/backend/test_workflow_repository.py -v`

- [ ] **Step 3: Implement conversion, safe path resolution, locking, and durable atomic replacement**

Validate `^[a-z0-9]+(?:-[a-z0-9]+)*$`; resolve only `root/slug/workflow.json`; serialize aliases with a final newline. Guard read-check-write with a process lock, write `.workflow.json.tmp`, flush and `os.fsync`, `os.replace`, then best-effort `fsync` the parent directory. Delete temporary files after errors and expose no absolute path in messages.

- [ ] **Step 4: Run backend unit tests and commit**

```bash
PYTHONPATH=backend conda run -n aoi-app python -m pytest tests/backend/ -v
git add backend/app/config/settings.py backend/app/schemas/workflow.py backend/app/services/workflow_repository.py tests/backend
git commit -m "feat(backend): persist revisioned workflow JSON"
```

### Task 4: Authenticated Workflow REST API

**Files:**
- Create: `backend/app/api/workflows.py`
- Modify: `backend/app/main.py`
- Create: `tests/integration/test_workflow_api.py`

**Interfaces:**
- Produces `GET /api/algorithms`, `GET /api/recipes/{recipeSlug}/workflow`, and `PUT /api/recipes/{recipeSlug}/workflow`.
- Error mapping: slug/graph `422`, stale revision `409`, persisted data/write failure `503`, anonymous `401`.

- [ ] **Step 1: Write failing authenticated API contract tests**

```python
def test_workflow_endpoints_require_authentication(client: TestClient) -> None:
    assert client.get('/api/algorithms').status_code == 401
    assert client.get('/api/recipes/rev-c-mainboard/workflow').status_code == 401

def test_invalid_graph_returns_structured_issues(auth_client: TestClient) -> None:
    payload = default_payload()
    payload['connections'][0]['targetPortId'] = 'missing-port'
    response = auth_client.put('/api/recipes/rev-c-mainboard/workflow', json=payload)
    assert response.status_code == 422
    assert response.json()['detail'][0]['code'] == 'unknown-port'
```

- [ ] **Step 2: Run API tests and verify missing routes fail**

Run: `PYTHONPATH=backend conda run -n aoi-app python -m pytest tests/integration/test_workflow_api.py -v`

- [ ] **Step 3: Implement router and exception mapping**

Inject `CurrentUser` into every handler. Ensure path slug and body `recipeSlug` match. Return ordered catalog schemas, an in-memory default for missing storage, an incremented stored workflow after PUT, and structured `ValidationIssueSchema` values for graph failures.

- [ ] **Step 4: Run backend/integration tests and commit**

```bash
PYTHONPATH=backend conda run -n aoi-app python -m pytest tests/backend tests/integration -v
git add backend/app/api/workflows.py backend/app/main.py tests/integration/test_workflow_api.py
git commit -m "feat(api): expose authenticated workflow endpoints"
```

### Task 5: Frontend Contracts, Service, and Tested Graph Helpers

**Files:**
- Create: `frontend/src/types/workflow.ts`
- Create: `frontend/src/services/workflow-service.ts`
- Modify: `frontend/src/services/api-client.ts`
- Create: `frontend/src/utils/workflow-graph.ts`
- Create: `frontend/src/utils/workflow-graph.test.ts`

**Interfaces:**
- Produces camelCase TypeScript interfaces matching backend JSON exactly.
- Produces `readAlgorithmCatalog(token)`, `readWorkflow(token, slug)`, `saveWorkflow(token, workflow)`.
- Produces `createNodeFromDefinition`, `validateConnection`, `validateDraft`, `stableTopologicalOrder`, `moveExecutionNode`, `filterCatalog`, `isWorkflowDirty`.
- `ApiError` remains inspectable by `status` and parsed `detail` so `409` can be distinguished.

- [ ] **Step 1: Write failing helper tests**

```typescript
it('rejects type mismatches and cycles', () => {
  expect(validateConnection(workflow, mismatchedConnection, catalog).code).toBe('type-mismatch');
  expect(validateConnection(workflow, cycleConnection, catalog).code).toBe('cycle');
});

it('creates defaults and filters every searchable catalog field', () => {
  const node = createNodeFromDefinition(patchCore, { x: 20, y: 40 });
  expect(node.parameters.memoryBankSize).toBe(patchCore.parameters[0].defaultValue);
  expect(filterCatalog(catalog, 'feature distribution')).toContain(patchCore);
});
```

- [ ] **Step 2: Run Vitest and verify missing helpers fail**

Run: `cd frontend && npm run test -- workflow-graph.test.ts`

- [ ] **Step 3: Implement project-owned types and pure deterministic helpers**

Mirror backend issue codes and parameter unions. Generate IDs with `crypto.randomUUID()`. Keep editable labels separate from immutable type/template keys. Reorder by moving one node ID; validate dependency order after each move; Auto order uses the saved preference as the stable tie breaker.

- [ ] **Step 4: Run frontend tests/typecheck and commit**

```bash
cd frontend && npm run test && npm run typecheck
git add frontend/src/types/workflow.ts frontend/src/services frontend/src/utils/workflow-graph.ts frontend/src/utils/workflow-graph.test.ts
git commit -m "feat(frontend): add workflow contracts and graph helpers"
```

### Task 6: React Flow Canvas and Editor Components

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify: `frontend/src/main.tsx`
- Create: `frontend/src/components/workflow/AlgorithmCatalog.tsx`
- Create: `frontend/src/components/workflow/WorkflowNode.tsx`
- Create: `frontend/src/components/workflow/WorkflowCanvas.tsx`
- Create: `frontend/src/components/workflow/NodeInspector.tsx`
- Create: `frontend/src/components/workflow/ExecutionOrderRail.tsx`

**Interfaces:**
- `WorkflowCanvas` receives AOI nodes/connections and emits AOI schema changes; React Flow `Node`/`Edge` values do not escape the component.
- All editor controls accept callbacks from `WorkflowEditorPage`; no component fetches data directly.

- [ ] **Step 1: Install the interaction dependency and base stylesheet**

Run: `cd frontend && npm install @xyflow/react@^12.8.0`

Import `@xyflow/react/dist/style.css` once from `frontend/src/main.tsx` before project styles.

- [ ] **Step 2: Build accessible catalog and custom typed node**

Catalog supports search, category groups, native drag payload `application/x-aoi-algorithm`, and Add buttons. Custom nodes render `Configuration only`, named input/output handles whose IDs equal port instance IDs, data-type text, selection state, and a keyboard-accessible remove action.

- [ ] **Step 3: Build controlled bounded canvas**

Use `ReactFlowProvider`, controlled nodes/edges, `screenToFlowPosition`, `isValidConnection`, `onConnect`, node-position updates, selected-edge deletion, `Background`, `Controls`, fit view, and a responsive `MiniMap`. Confirm node deletion when dependent edges exist before emitting removal.

- [ ] **Step 4: Build typed inspector and execution rail**

Render text/number/boolean/select controls from parameter metadata with inline constraints. Port labels are editable; standard type/required/template fields are read-only. The rail supports native drag reorder plus Move up/Move down buttons, displays dependency errors, and exposes Auto order.

- [ ] **Step 5: Typecheck and commit**

```bash
cd frontend && npm run typecheck && npm run build
git add frontend/package.json frontend/package-lock.json frontend/src/main.tsx frontend/src/components/workflow
git commit -m "feat(frontend): build typed workflow canvas components"
```

### Task 7: Editor State, Revision Conflict, and Workspace Navigation

**Files:**
- Create: `frontend/src/pages/WorkflowEditorPage.tsx`
- Modify: `frontend/src/pages/WorkspacePage.tsx`
- Modify: `frontend/src/types/workspace.ts`
- Modify: `frontend/src/components/StudioChrome.tsx`
- Modify: `frontend/src/components/ProjectExplorer.tsx`

**Interfaces:**
- Adds `WorkspaceView = ... | 'workflow-editor'`.
- `WorkspacePage` owns `savedWorkflow`, reloads active recipe `rev-c-mainboard`, and passes workflow data to dashboard/editor.
- Navigation is routed through `requestViewChange`; dirty editor drafts require `window.confirm` before changing view.

- [ ] **Step 1: Implement load, draft, validation, and save state machine**

Fetch catalog/workflow in parallel when entering the editor. Maintain `savedWorkflow` and `draftWorkflow`; derive dirty state from serializable AOI values. Disable Save while loading, saving, unchanged, or invalid. On success replace both values with the server response.

- [ ] **Step 2: Implement conflict-safe and failure states**

On `ApiError.status === 409`, preserve the draft, show an `aria-live` conflict message, and offer `Reload server version`. On other failures preserve the draft and re-enable retry. Empty catalog and empty workflow have explanatory retry/add states.

- [ ] **Step 3: Wire editor entry and unsaved-navigation confirmation**

Dashboard settings and Project explorer Workflow open `workflow-editor`; Back to workspace uses guarded navigation. Add the editor title mapping and keep current Studio chrome behavior intact.

- [ ] **Step 4: Run tests/typecheck and commit**

```bash
cd frontend && npm run test && npm run typecheck
git add frontend/src/pages/WorkflowEditorPage.tsx frontend/src/pages/WorkspacePage.tsx frontend/src/types/workspace.ts frontend/src/components/StudioChrome.tsx frontend/src/components/ProjectExplorer.tsx
git commit -m "feat(frontend): orchestrate workflow editor state"
```

### Task 8: Dashboard Inspection Flow and Responsive Styling

**Files:**
- Modify: `frontend/src/pages/DashboardPage.tsx`
- Modify: `frontend/src/styles/global.css`

**Interfaces:**
- `DashboardPage` consumes the saved `Workflow | null` and `onConfigureWorkflow`.
- Dashboard order and names come from `workflow.executionOrder`; every node status text is `Configuration only`.

- [ ] **Step 1: Replace hard-coded pipeline data and add accessible collapse/settings controls**

Start expanded. On wide containers collapse to an action rail; on narrow containers collapse to a compact header in normal flow. Settings has the exact label `Configure inspection workflow`; collapse has state-specific `aria-label` and `aria-expanded`.

- [ ] **Step 2: Add editor layout, execution-spine identity, focus, and responsive rules**

Use existing AOI tokens plus Ink `#0B1F33`, Blueprint `#1769E0`, Signal green `#149B68`, Warning amber `#B66A00`, Panel `#FFFFFF`, and Grid `#EEF3F8`. Wide uses catalog/canvas/inspector columns; medium uses catalog rail plus canvas/inspector; narrow stacks bounded regions. Hide minimap without space and disable nonessential transitions under `prefers-reduced-motion`.

- [ ] **Step 3: Build and commit**

```bash
cd frontend && npm run test && npm run typecheck && npm run build
git add frontend/src/pages/DashboardPage.tsx frontend/src/styles/global.css
git commit -m "feat(frontend): connect responsive inspection workflow"
```

### Task 9: End-to-End Verification and Documentation

**Files:**
- Modify: `README.md`
- Modify: `.agents/experience/memory.md`

**Interfaces:**
- Documents workflow storage ownership, API endpoints, revision conflicts, and configuration-only scope.

- [ ] **Step 1: Run complete automated verification**

```bash
bash scripts/test/test.sh
bash scripts/build/build.sh
```

Expected: core/backend/integration/frontend tests, TypeScript checks, Vite build, and native scaffold build all pass.

- [ ] **Step 2: Run authenticated browser verification**

At 390x600, 768x900, 1280x800, and 1920x1080 verify panel collapse/settings, catalog Add and drag/drop, node movement, valid/invalid edges, edge/node deletion, zoom/pan/fit, inspector editing, rail drag and buttons, Auto order, save, stale `409`, retry, reload, unsaved navigation, focus visibility, reduced motion, and `document.documentElement.scrollWidth <= window.innerWidth`.

- [ ] **Step 3: Inspect persisted JSON and runtime claims**

Confirm `data/projects/rev-c-mainboard/workflow.json` is camelCase, revision increments once per save, no `.tmp` remains, and UI/catalog say `Configuration only` without suggesting OpenCV/PyTorch/Anomalib is installed.

- [ ] **Step 4: Document contracts and commit**

```bash
git add README.md .agents/experience/memory.md
git commit -m "docs: record workflow editor contracts"
git status --short
```

Only pre-existing user-owned untracked algorithm documentation may remain.