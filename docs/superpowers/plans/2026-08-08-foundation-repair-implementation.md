# AOI Foundation Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Make AOI Studio's current baseline truthful and safe by enforcing single-Administrator access, returning inspection evidence, preserving partial device availability, persisting visible Settings fields, testing dataset filesystem behavior, and recording durable audit events.

**Architecture:** Keep existing React/FastAPI/PostgreSQL boundaries. Add no role-management system. Extend current workstation preference documents only for visible user locale fields; Phase 1 will migrate them to PostgreSQL. Add a PostgreSQL audit model and request middleware so protected mutations receive actor/action/result records without coupling audit logic to every route.

**Tech Stack:** Python 3.12, FastAPI 0.115.2, Pydantic 2.9.2, SQLAlchemy 2.0.36, PostgreSQL 16, pytest 8.3.4, React 18.3, TypeScript 5.6, Vite 8.2, Vitest 4.1.

## Global Constraints

- All production changes use test-first red-green-refactor.
- All code, UI text, API payload keys, logs, and test names remain English.
- Every Markdown change has a `.md.vn` companion.
- Project paths in code and docs remain relative.
- Browser calls only authenticated FastAPI routes; adapters remain loopback-only.
- Live Home, Move, Stop, Clear fault, and preview stay outside Settings.
- Run GitNexus impact analysis before editing each existing symbol.
- Run GitNexus `detect_changes` before each commit. If local GitNexus remains blocked, do not commit; report the blocker with exact output.
- Preserve light-theme, WCAG AA, normal-flow, and responsive rules.

---

### Task 1: Single-Administrator Authentication Mode

**Files:**
- Modify: `backend/app/config/settings.py`
- Modify: `backend/app/api/auth.py`
- Modify: `backend/app/database/bootstrap.py`
- Modify: `frontend/src/pages/AuthPage.tsx`
- Modify: `frontend/src/pages/AuthPage.test.tsx`
- Modify: `frontend/src/services/auth-service.ts`
- Modify: `frontend/src/types/auth.ts`
- Modify: `.env.example`
- Test: `tests/backend/test_device_settings.py`
- Test: `tests/integration/test_auth_api.py`

**Interfaces:**
- Produces: `Settings.allow_public_registration: bool = False`.
- Keeps: `POST /api/auth/login` and local bootstrap account creation.
- Changes: `POST /api/auth/register` returns `403` with `Public account registration is disabled.` when registration is disabled.

- [x] **Step 1: Add failing backend configuration and API tests**

```python
def test_public_registration_defaults_to_disabled() -> None:
    settings = Settings(**settings_payload())
    assert settings.allow_public_registration is False

def test_public_registration_is_disabled() -> None:
    with TestClient(app) as client:
        response = client.post('/api/auth/register', json={
            'email': 'other@example.com',
            'fullName': 'Other User',
            'password': 'secure-password',
        })
    assert response.status_code == 403
    assert response.json()['detail'] == 'Public account registration is disabled.'
```

- [x] **Step 2: Run tests and verify RED**

Run: `PYTHONPATH=backend conda run -n aoi-app python -m pytest tests/backend/test_device_settings.py tests/integration/test_auth_api.py -v`

Expected: configuration attribute missing and registration returns `201` instead of `403`.

- [x] **Step 3: Add registration policy and guard**

```python
class Settings(BaseSettings):
    allow_public_registration: bool = False

@router.post('/register', response_model=AuthSessionResponse, status_code=status.HTTP_201_CREATED)
def register(account: RegisterRequest, session: DatabaseSession) -> AuthSessionResponse:
    if not get_settings().allow_public_registration:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Public account registration is disabled.')
```

- [x] **Step 4: Add failing frontend test that sign-up is absent**

```tsx
it('does not expose public account registration', () => {
  const markup = renderToStaticMarkup(<AuthPage onAuthenticated={vi.fn()} />);
  expect(markup).not.toContain('Create account');
  expect(markup).not.toContain('Create an account');
});
```

- [x] **Step 5: Run frontend test and verify RED**

Run: `cd frontend && npm test -- src/pages/AuthPage.test.tsx`

Expected: rendered markup contains `Create account`.

- [x] **Step 6: Remove sign-up UI and unused frontend registration client/types**

Keep only `sign-in | forgot-password` modes. Remove `submitSignUp`, full-name/confirm-password state, `createAccount`, and `RegisterRequest`.

- [x] **Step 7: Rename seed defaults to Administrator semantics**

Use `admin@aoi.local` and `AOI Administrator` in code defaults, `.env.example`, and tests. Do not modify ignored local `.env` automatically.

- [x] **Step 8: Verify GREEN**

Run backend target tests, frontend `AuthPage` tests, and frontend typecheck.

- [x] **Step 9: Run change detection and commit**

```bash
node .gitnexus/run.cjs detect-changes
git add backend/app/config/settings.py backend/app/api/auth.py backend/app/database/bootstrap.py frontend/src/pages/AuthPage.tsx frontend/src/pages/AuthPage.test.tsx frontend/src/services/auth-service.ts frontend/src/types/auth.ts tests/backend/test_device_settings.py tests/integration/test_auth_api.py .env.example
git commit -m "fix(auth): enforce single administrator mode"
```

---

### Task 2: Real Inspection Evidence Responses

**Files:**
- Modify: `backend/app/api/inspections.py`
- Test: `tests/integration/test_inspection_api.py`

**Interfaces:**
- Produces: `build_inspection_detail_response(inspection: InspectionResult) -> InspectionDetailResponse`.
- Uses existing `DefectResponse` and `InspectionImageResponse` schemas through Pydantic model validation.
- Changes both GET detail and POST create responses to include loaded relationships.

- [x] **Step 1: Add failing serializer test with one defect and image**

Construct `SimpleNamespace` objects matching inspection, recipe, operator, reviewer, defect, and image attributes. Assert returned camelCase JSON contains real defect/image IDs and hashes.

```python
response = build_inspection_detail_response(inspection)
payload = response.model_dump(mode='json', by_alias=True)
assert payload['defects'][0]['defectType'] == 'missing-component'
assert payload['images'][0]['sha256Hash'] == 'a' * 64
```

- [x] **Step 2: Run test and verify RED**

Run: `PYTHONPATH=backend conda run -n aoi-app python -m pytest tests/integration/test_inspection_api.py -v`

Expected: helper import fails because it does not exist.

- [x] **Step 3: Implement one response builder**

```python
def build_inspection_detail_response(inspection: InspectionResult) -> InspectionDetailResponse:
    return InspectionDetailResponse(
        # scalar fields copied from inspection
        defects=[DefectResponse.model_validate(defect) for defect in inspection.defects],
        images=[InspectionImageResponse.model_validate(image) for image in inspection.images],
    )
```

Replace duplicate GET/POST response construction with this helper.

- [x] **Step 4: Verify GREEN and regression suite**

Run target test and existing inspection/database tests.

- [x] **Step 5: Detect and commit**

```bash
node .gitnexus/run.cjs detect-changes
git add backend/app/api/inspections.py tests/integration/test_inspection_api.py
git commit -m "fix(inspections): return stored evidence"
```

---

### Task 3: Independent Device Snapshot Loading

**Files:**
- Modify: `frontend/src/services/device-service.ts`
- Modify: `frontend/src/services/device-service.test.ts`

**Interfaces:**
- Keeps: `readDeviceSnapshot(accessToken: string): Promise<DeviceSnapshot>`.
- Changes: fetch camera configuration whenever camera is ready; fetch motion configuration/state whenever motion is ready.
- Failure of an operational read for one ready adapter propagates normally; an unavailable adapter causes only its fields to be null.

- [x] **Step 1: Add failing partial-availability tests**

```typescript
it('keeps camera configuration when motion is unavailable', async () => {
  // overview: camera ready, motion unavailable; then camera configuration
  const snapshot = await readDeviceSnapshot('token');
  expect(snapshot.cameraConfiguration?.cameraId).toBe('top-camera');
  expect(snapshot.motionConfiguration).toBeNull();
  expect(snapshot.motionState).toBeNull();
});
```

Add inverse case for motion ready/camera unavailable.

- [x] **Step 2: Run test and verify RED**

Run: `cd frontend && npm test -- src/services/device-service.test.ts`

Expected: current early return leaves all operational fields null.

- [x] **Step 3: Implement capability-aware request groups**

Initialize null fields, request camera data only when camera status is ready, request motion data only when motion status is ready, then return one snapshot.

- [x] **Step 4: Verify GREEN and typecheck**

Run service tests and `npm run typecheck`.

- [x] **Step 5: Detect and commit**

```bash
node .gitnexus/run.cjs detect-changes
git add frontend/src/services/device-service.ts frontend/src/services/device-service.test.ts
git commit -m "fix(devices): preserve partial adapter state"
```

---

### Task 4: Persist Visible Locale Settings

**Files:**
- Modify: `backend/app/schemas/workstation_preferences.py`
- Modify: `frontend/src/types/workstation-preferences.ts`
- Modify: `frontend/src/utils/workstation-preferences.ts`
- Modify: `frontend/src/utils/workstation-preferences.test.ts`
- Modify: `frontend/src/pages/SettingsPage.tsx`
- Create: `frontend/src/pages/SettingsPage.test.tsx`
- Modify: `frontend/src/pages/WorkspacePage.tsx`
- Test: `tests/backend/test_workstation_preference_repository.py`
- Test: `tests/integration/test_workstation_preference_api.py`

**Interfaces:**
- Produces `LocalePreferencesSchema` and frontend `LocalePreferences` with:
  - `language: 'en-US' | 'en-GB'`
  - `region: 'vi-VN' | 'en-SG' | 'de-DE'`
  - `timezone: 'Asia/Ho_Chi_Minh' | 'Asia/Singapore' | 'Europe/Berlin'`
  - `measurementSystem: 'metric' | 'imperial'`
  - `clockFormat: '24-hour' | '12-hour'`
- Adds `locale` to `WorkstationPreferences`.
- Produces `onPreferencesChange(preferences: WorkstationPreferences): void` in `SettingsPageProps`.

- [x] **Step 1: Add failing backend default/round-trip tests**

Assert default locale values and API persistence after changing `language` and `measurementSystem`.

- [x] **Step 2: Verify backend RED**

Expected: `locale` does not exist.

- [x] **Step 3: Add backend locale schema and defaults**

Use `Literal` values so unsupported locale identifiers fail server validation.

- [x] **Step 4: Add failing frontend helper and Settings render tests**

Assert default locale object exists. Render `SettingsPage`, verify selects use persisted values, and verify each select calls `onPreferencesChange` with an updated `locale` object.

- [x] **Step 5: Verify frontend RED**

Expected: local component state prevents persisted values and callback contract does not exist.

- [x] **Step 6: Move locale state into `WorkstationPreferences`**

Remove local `language`, `region`, `units`, and `clock` state. Bind selects to `preferences.locale` and call `onPreferencesChange`.

- [x] **Step 7: Wire workspace draft updates**

Pass `onPreferencesChange={setDraftPreferences}`. Dirty detection continues comparing saved and draft preference documents.

- [x] **Step 8: Verify GREEN**

Run backend preference tests, frontend preference/Settings tests, and typecheck.

- [x] **Step 9: Detect and commit**

```bash
node .gitnexus/run.cjs detect-changes
git add backend/app/schemas/workstation_preferences.py frontend/src/types/workstation-preferences.ts frontend/src/utils/workstation-preferences.ts frontend/src/utils/workstation-preferences.test.ts frontend/src/pages/SettingsPage.tsx frontend/src/pages/SettingsPage.test.tsx frontend/src/pages/WorkspacePage.tsx tests/backend/test_workstation_preference_repository.py tests/integration/test_workstation_preference_api.py
git commit -m "feat(settings): persist locale preferences"
```

---

### Task 5: Explicit Workstation Profile Selection

**Files:**
- Modify: `frontend/src/pages/SettingsPage.tsx`
- Modify: `frontend/src/pages/SettingsPage.test.tsx`
- Modify: `frontend/src/pages/WorkspacePage.tsx`
- Modify: `frontend/src/pages/CameraManagerPage.tsx`

**Interfaces:**
- Replaces `onWorkstationIdChange` with `onWorkstationSelect(workstationId: string): Promise<void>`.
- `SettingsPage` owns only an unpersisted selector text draft initialized from the loaded profile.
- Workspace loads destination profile before replacing saved/draft state.
- Camera Manager shows Workstation ID read-only.

- [x] **Step 1: Add failing Settings selector tests**

Test that typing does not mutate preferences and `Load station profile` calls `onWorkstationSelect('station-02')`.

- [x] **Step 2: Verify RED**

Expected: current input immediately calls `onWorkstationIdChange`.

- [x] **Step 3: Implement selector draft and load action**

Disable load when ID is unchanged or invalid. Surface load errors through existing preference error state.

- [x] **Step 4: Add workspace loader**

```typescript
const selectWorkstation = async (workstationId: string) => {
  const next = await readWorkstationPreferences(session.accessToken, workstationId);
  setSavedPreferences(next);
  setDraftPreferences(structuredClone(next));
};
```

- [x] **Step 5: Make Camera Manager station identity read-only**

Retain photometric edits but remove direct identity mutation and revision reset.

- [x] **Step 6: Verify GREEN and typecheck**

- [x] **Step 7: Detect and commit**

```bash
node .gitnexus/run.cjs detect-changes
git add frontend/src/pages/SettingsPage.tsx frontend/src/pages/SettingsPage.test.tsx frontend/src/pages/WorkspacePage.tsx frontend/src/pages/CameraManagerPage.tsx
git commit -m "fix(settings): load workstation profiles explicitly"
```

---

### Task 6: Dataset Filesystem Characterization and Safety Tests

**Files:**
- Create: `tests/backend/test_dataset_service.py`
- Create: `tests/integration/test_dataset_api.py`
- Modify only when a failing safety test proves a defect: `backend/app/services/dataset_service.py`
- Modify only when a failing contract test proves a defect: `backend/app/api/datasets.py`

**Interfaces:**
- No new production API planned.
- Tests override dataset/capture roots with `tmp_path`.
- Tests use generated valid PNG bytes and bounded fake uploads.

- [x] **Step 1: Add service tests**

Cover create/update/delete dataset, category create/rename/delete, upload magic bytes, batch count, 50 MiB limit, safe filename, rename, move, delete, capture traversal rejection, duplicate import naming, and ZIP export paths.

- [x] **Step 2: Run tests and classify failures**

Expected: characterization cases may pass. Any safety-contract failure becomes RED evidence for minimal production repair.

- [x] **Step 3: Add authenticated API tests**

Cover anonymous `401`, invalid names `422`, create/list/detail, category operations, image upload/list/rename/move/delete, capture import, and export response.

- [x] **Step 4: Implement only proven fixes**

Do not refactor broad dataset code when tests already pass. For each failing behavior, rerun its single test RED, make minimal change, then rerun GREEN.

- [x] **Step 5: Run dataset suites**

Run: `PYTHONPATH=backend conda run -n aoi-app python -m pytest tests/backend/test_dataset_service.py tests/integration/test_dataset_api.py -v`

- [x] **Step 6: Detect and commit**

```bash
node .gitnexus/run.cjs detect-changes
git add tests/backend/test_dataset_service.py tests/integration/test_dataset_api.py backend/app/services/dataset_service.py backend/app/api/datasets.py
git commit -m "test(datasets): cover filesystem safety contracts"
```

---

### Task 7: Durable Audit Baseline

**Files:**
- Create: `backend/app/models/audit_event.py`
- Create: `backend/app/services/audit_service.py`
- Create: `backend/app/middleware/audit.py`
- Create: `backend/app/api/audit_events.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/database/bootstrap.py`
- Create: `database/schema/006_create_audit_events.sql`
- Create: `tests/backend/test_audit_service.py`
- Create: `tests/integration/test_audit_api.py`

**Interfaces:**
- Produces `AuditEvent` with actor ID, action, method, path, resource type/ID, request ID, status code, result, and timestamp.
- Produces `record_audit_event(session, event_data) -> AuditEvent`.
- Produces `AuditMiddleware` for `POST`, `PUT`, `PATCH`, and `DELETE`.
- Produces protected `GET /api/audit-events` with bounded pagination.

- [x] **Step 1: Add failing model/service tests**

Use an isolated SQLAlchemy test session and assert an audit event persists with actor/action/result.

- [x] **Step 2: Verify RED**

Expected: audit modules do not exist.

- [x] **Step 3: Add audit model, schema SQL, and service**

Do not store request bodies, credentials, bearer tokens, secrets, or image bytes.

- [x] **Step 4: Add failing integration tests**

Authenticate as seeded Administrator, mutate a workstation preference, then query audit events. Assert actor ID, method `PUT`, protected path, success result, and request ID. Assert anonymous audit reads return `401`.

- [x] **Step 5: Verify integration RED**

Expected: no middleware or audit endpoint.

- [x] **Step 6: Implement middleware and protected query API**

Verify bearer JWT using configured algorithm before assigning actor ID. Audit even failed mutations, but never let an audit persistence failure replace the original response; emit a server log and expose health diagnostics in later phases.

- [x] **Step 7: Verify GREEN**

Run audit tests plus auth, workflow, preference, device, dataset, inspection, and physical-I/O integration tests.

- [x] **Step 8: Detect and commit**

```bash
node .gitnexus/run.cjs detect-changes
git add backend/app/models/audit_event.py backend/app/services/audit_service.py backend/app/middleware/audit.py backend/app/api/audit_events.py backend/app/main.py backend/app/database/bootstrap.py database/schema/006_create_audit_events.sql tests/backend/test_audit_service.py tests/integration/test_audit_api.py
git commit -m "feat(audit): record authenticated mutations"
```

---

### Task 8: Documentation, Memory, and Phase Verification

**Files:**
- Modify: `README.md`
- Modify: `README.md.vn`
- Modify: `.agents/experience/memory.md`
- Modify: `.agents/experience/memory.md.vn`
- Add missing `.md.vn` companions identified by a deterministic inventory.

**Interfaces:**
- Documents single-Administrator mode, evidence responses, partial adapters, persisted locale preferences, workstation profile selection, dataset safety coverage, and audit behavior.

- [x] **Step 1: Inventory Markdown companion gaps**

Use a Python script that excludes `.git`, `.gitnexus`, `.codegraph`, `node_modules`, and generated build directories. Record exact missing companions.

- [x] **Step 2: Add complete Vietnamese companions**

Do not create placeholder translations.

- [x] **Step 3: Update README and memory pairs**

Record operationally important behavior and any discovered defects/fixes.

- [x] **Step 4: Run full verification**

```bash
bash scripts/test/test.sh
bash scripts/build/build.sh
bash -n scripts/run_dev.sh
cd frontend && npm audit --omit=dev --audit-level=moderate
codegraph sync .
codegraph status .
node .gitnexus/run.cjs detect-changes
git diff --check
```

- [x] **Step 5: Run browser verification**

Verify sign-in, Settings locale changes, station profile loading, Hardware partial diagnostics, and audit visibility. Check 390, 768, 1280, and 1920 pixel widths with no document overflow.

- [x] **Step 6: Commit documentation only after change detection**

```bash
git add README.md README.md.vn .agents/experience/memory.md .agents/experience/memory.md.vn docs
git commit -m "docs: record foundation repair behavior"
```

## Phase 0 Exit Gate

- Public registration disabled; bootstrap Administrator login works.
- Protected mutations emit durable audit records.
- Inspection details return persisted defects and images.
- One degraded adapter does not hide the other adapter.
- Visible locale settings round-trip through persistence and dirty detection.
- Workstation selection loads destination state before editing.
- Dataset filesystem safety contracts have backend and API coverage.
- Full tests, build, audit, CodeGraph, GitNexus change detection, diff checks, and responsive browser checks pass.