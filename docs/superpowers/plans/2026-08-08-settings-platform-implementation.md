# AOI PostgreSQL Settings Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace file-backed workstation preferences with a reusable PostgreSQL settings/version platform providing immutable history, optimistic concurrency, validation, activation, rollback, migration, and portable import/export.

**Architecture:** Alembic becomes the only schema migration mechanism; startup verifies database revision before seeding. Generic `settings_documents`, immutable `settings_versions`, and append-only `settings_activations` store User, Workstation, Recipe, and System state, while a schema registry validates each document key. Existing `/api/workstation-preferences` contracts remain compatible through a PostgreSQL adapter; `/api/v1/settings` exposes generic contracts.

**Tech Stack:** Python 3.12, FastAPI 0.115.2, Pydantic 2.9.2, SQLAlchemy 2.0.36, PostgreSQL 16, psycopg 3.2.3, Alembic 1.14.0, pytest 8.3.4, React 18.3, TypeScript 5.6, Vite 8.2, Vitest 4.1.

## Global Constraints

- Use red-green-refactor for every production behavior change.
- Run GitNexus upstream impact before editing every existing function, class, or method; warn before HIGH or CRITICAL changes.
- Run GitNexus `detect-changes` before every commit.
- Keep code, UI text, API payloads, logs, tests, and repository documentation in English; maintain complete `.md.vn` companions.
- PostgreSQL is settings source of truth. JSON is migration/interchange only.
- Use PostgreSQL transactions and row locks, never process-local locks, for concurrency.
- Never mutate a `settings_versions` row. Rollback inserts a new version.
- Require authenticated actor and expected revision for mutation; require idempotency key for activation.
- Never return secrets, arbitrary filesystem paths, adapter URLs, commands, or executable code.
- Keep live Home, Move, Stop, Clear fault, preview, test capture, and commissioning outside Settings.

## Fixed Contracts

```python
SettingsScope = Literal['user', 'workstation', 'recipe', 'system']

# Unique identity; PostgreSQL uses NULLS NOT DISTINCT.
(scope, subject_id, document_key, owner_user_id)

# Existing preference identity mapping.
scope = 'workstation'
subject_id = workstation_id
document_key = 'workstation-preferences'
owner_user_id = user_id
```

- Missing document revision: `0`; first persisted revision: `1`.
- Version creation locks document with `SELECT ... FOR UPDATE`, checks `expectedRevision`, inserts `current + 1`, and advances `current_version_id` in one transaction.
- SHA-256 input: `json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')`.
- Stale write: HTTP `409`, `detail.code == 'settings_revision_conflict'`, current revision/checksum, and sorted JSON-path differences.
- Rollback copies old payload into a new version and records `source_version_id`.
- Activation replay key: `(document_id, idempotency_key)`. Same request returns original row; changed request returns `409/idempotency_key_reused`.
- Phase 1 activation changes metadata only and never calls hardware adapters.

---

### Task 1: Alembic Baseline and Revision Verification

**Files:**
- Modify: `backend/requirements.txt`, `backend/app/database/bootstrap.py`, `scripts/install/setup-postgresql.sh`, `scripts/install/verify-environment.sh`
- Create: `alembic.ini`, `database/migrations/env.py`, `database/migrations/script.py.mako`, `database/migrations/versions/0001_existing_schema_baseline.py`, `backend/app/database/migrations.py`
- Test: `tests/backend/test_database_migrations.py`, `tests/integration/test_database_migrations.py`

**Interfaces:** Produces `build_alembic_config(database_url: str) -> Config`, `upgrade_database(database_url: str) -> None`, and `verify_database_revision(connection: Connection) -> None`. Keeps `initialize_database()`, now revision verification plus seeding only.

- [ ] **Step 1: Impact existing startup symbol**

```bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin GITNEXUS_INVOCATION=npx node .gitnexus/run.cjs impact initialize_database --direction upstream
```

Record direct caller, startup flows, and risk. Stop and warn for HIGH or CRITICAL.

- [ ] **Step 2: Add failing migration tests**

Use a unique temporary PostgreSQL schema and URL `options=-csearch_path=<schema>`; drop schema with `CASCADE` in `finally`. Verify upgrade from empty creates `alembic_version`, `users`, `recipes`, `inspection_results`, `defects`, `inspection_images`, and `audit_events`.

- [ ] **Step 3: Verify RED**

```bash
PYTHONPATH=backend conda run -n aoi-app python -m pytest tests/backend/test_database_migrations.py tests/integration/test_database_migrations.py -v
```

- [ ] **Step 4: Add Alembic baseline**

Pin `alembic==1.14.0`. Configure `target_metadata = Base.metadata`, runtime URL, online/offline modes, and `compare_type=True`. Revision `0001_existing_schema_baseline` must create/downgrade every table, key, check, and index represented by `database/schema/001_create_users.sql` through `006_create_audit_events.sql` using Alembic operations.

- [ ] **Step 5: Add strict migration commands**

`upgrade_database` runs `upgrade head`. `verify_database_revision` compares `MigrationContext` current revision with Alembic head and raises a clear error on mismatch. Remove `Base.metadata.create_all()` from startup. Startup must never stamp or upgrade automatically.

- [ ] **Step 6: Migrate installer safely**

Replace SQL-file loop with `python -m app.database.migrations upgrade`. Add `baseline-existing`: inspect exact baseline tables/columns, reject incompatible schemas, stamp `0001_existing_schema_baseline` only after verification, then upgrade head. Installer uses it only when `users` exists and `alembic_version` does not.

- [ ] **Step 7: Verify and commit**

```bash
PYTHONPATH=backend conda run -n aoi-app python -m pytest tests/backend/test_database_migrations.py tests/integration/test_database_migrations.py -v
bash -n scripts/install/setup-postgresql.sh && bash -n scripts/install/verify-environment.sh
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin GITNEXUS_INVOCATION=npx node .gitnexus/run.cjs detect-changes
git add backend/requirements.txt alembic.ini database/migrations backend/app/database/migrations.py backend/app/database/bootstrap.py scripts/install/setup-postgresql.sh scripts/install/verify-environment.sh tests/backend/test_database_migrations.py tests/integration/test_database_migrations.py
git commit -m "build(database): add managed schema migrations"
```

---

### Task 2: Settings Tables, Models, and Schema Registry

**Files:**
- Create: `database/migrations/versions/0002_create_settings_platform.py`, `backend/app/models/settings_document.py`, `backend/app/models/settings_version.py`, `backend/app/models/settings_activation.py`, `backend/app/schemas/settings.py`, `backend/app/services/settings_schema_registry.py`
- Modify: `backend/app/models/audit_event.py`, `backend/app/schemas/workstation_preferences.py`, `backend/app/database/bootstrap.py`
- Test: `tests/backend/test_settings_schemas.py`, `tests/integration/test_settings_migration.py`

**Interfaces:** Produces three ORM models, generic request/response schemas, `WorkstationPreferenceContentSchema`, and `validate_settings_payload(document_key, schema_version, payload)`.

- [ ] **Step 1: Impact `AuditEvent` and `WorkstationPreferencesSchema`**

```bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin GITNEXUS_INVOCATION=npx node .gitnexus/run.cjs impact AuditEvent --direction upstream
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin GITNEXUS_INVOCATION=npx node .gitnexus/run.cjs impact WorkstationPreferencesSchema --direction upstream
```

- [ ] **Step 2: Add RED schema/migration tests**

Verify registry camel-case normalization, metadata exclusion, unknown key/version rejection, table columns, JSONB payload, unique constraints, foreign keys, checks, and audit metadata columns.

- [ ] **Step 3: Create revision `0002_create_settings_platform`**

`settings_documents` holds identity, `current_revision`, current/active pointers, timestamps, and `UNIQUE NULLS NOT DISTINCT (scope, subject_id, document_key, owner_user_id)`. `settings_versions` holds document FK, revision, schema version, JSONB payload, checksum, creator, reason, source version, timestamp, and unique document/revision. `settings_activations` holds document/version FKs, idempotency key, request checksum, `active|failed` status, observed revision, JSONB diagnostics, actor, reason, timestamps, and unique document/key.

Extend `audit_events` with `before_checksum`, `after_checksum`, `reason`, and JSONB `client_metadata`. Never store body, token, credentials, secrets, image bytes, or arbitrary headers.

- [ ] **Step 4: Implement content schema and registry**

```python
SETTINGS_SCHEMA_REGISTRY = {('workstation-preferences', 1): WorkstationPreferenceContentSchema}
```

Validate through Pydantic and dump normalized camel-case JSON. Keep `WorkstationPreferencesSchema` as compatibility envelope.

- [ ] **Step 5: Verify downgrade/upgrade and commit**

At revision `0001`, startup revision check must fail; at head it must pass. Downgrade to `0001` must remove settings tables while preserving baseline data; re-upgrade must pass.

```bash
PYTHONPATH=backend conda run -n aoi-app python -m pytest tests/backend/test_settings_schemas.py tests/integration/test_settings_migration.py tests/integration/test_database_migrations.py -v
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin GITNEXUS_INVOCATION=npx node .gitnexus/run.cjs detect-changes
git add database/migrations/versions/0002_create_settings_platform.py backend/app/models backend/app/schemas/settings.py backend/app/schemas/workstation_preferences.py backend/app/services/settings_schema_registry.py backend/app/database/bootstrap.py tests/backend/test_settings_schemas.py tests/integration/test_settings_migration.py tests/integration/test_database_migrations.py
git commit -m "feat(settings): add versioned persistence model"
```

---

### Task 3: Transactional Version, History, Conflict, and Rollback Service

**Files:**
- Create: `backend/app/services/settings_service.py`, `backend/app/services/settings_diff.py`
- Modify: `backend/app/services/audit_service.py`
- Test: `tests/backend/test_settings_diff.py`, `tests/integration/test_settings_service.py`

**Interfaces:** Produces frozen `SettingsIdentity`; `get_current_settings`, `create_settings_version`, `list_settings_history`, and `rollback_settings`; `SettingsRevisionConflict`; and `record_audit_event(..., commit: bool = True)`.

- [ ] **Step 1: Impact audit persistence**

```bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin GITNEXUS_INVOCATION=npx node .gitnexus/run.cjs impact record_audit_event --direction upstream
```

- [ ] **Step 2: Add RED checksum/diff tests**

```python
def test_checksum_ignores_mapping_order() -> None:
    assert settings_checksum({'b': 2, 'a': 1}) == settings_checksum({'a': 1, 'b': 2})

def test_diff_uses_sorted_json_paths() -> None:
    assert settings_diff({'x': 1}, {'x': 2}) == [{'path': '$.x', 'submitted': 1, 'current': 2}]
```

- [ ] **Step 3: Add RED PostgreSQL service tests**

Cover first version, immutable second version, two-session stale race, invalid schema with no writes, newest-first history, rollback creating a source-linked new version, settings/audit committing together, and forced audit failure rolling back both.

- [ ] **Step 4: Implement row-locked service**

Use `SELECT ... FOR UPDATE`; recover a missing-document unique race through a nested transaction and winner reload. Validate before insert. Call `flush()` inside service; API owns final commit/rollback. Do not use `RLock`.

- [ ] **Step 5: Verify and commit**

```bash
PYTHONPATH=backend conda run -n aoi-app python -m pytest tests/backend/test_settings_diff.py tests/integration/test_settings_service.py -v
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin GITNEXUS_INVOCATION=npx node .gitnexus/run.cjs detect-changes
git add backend/app/services/settings_service.py backend/app/services/settings_diff.py backend/app/services/audit_service.py tests/backend/test_settings_diff.py tests/integration/test_settings_service.py
git commit -m "feat(settings): create immutable transactional versions"
```

---

### Task 4: Authenticated Versioned Settings API and Portable JSON

**Files:**
- Create: `backend/app/api/settings.py`
- Modify: `backend/app/main.py`, `backend/app/schemas/settings.py`
- Test: `tests/integration/test_settings_api.py`

**Interfaces:** Adds `GET /api/v1/settings/{scope}/{subject_id}`, `POST .../validate`, `POST .../versions`, `GET .../history`, `POST .../rollback`, `GET .../export`, and `POST .../import`. Uses query `documentKey`. Authenticated user ID is authoritative workstation owner.

- [ ] **Step 1: Impact `app` before router registration**

```bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin GITNEXUS_INVOCATION=npx node .gitnexus/run.cjs impact app --direction upstream
```

- [ ] **Step 2: Add RED API tests**

Cover authentication, scope/key validation, validate-without-write, create/read/history, structured stale conflict, rollback, owner isolation, export checksum, valid import as a new destination revision, tamper rejection, and no implicit activation.

- [ ] **Step 3: Implement routes and errors**

Use one commit after service success and rollback on exception. Missing generic document: `404/settings_document_not_found`. Invalid payload: `422/settings_validation_failed`. Conflict body includes expected/current revision, current checksum, and sorted differences.

Export envelope contains format version, scope, subject ID, document key, owner user ID, revision, schema version, payload, and payload checksum. Import verifies identity, owner, schema, and checksum, then creates a new version using caller `expectedRevision` and reason. Import never activates.

- [ ] **Step 4: Verify and commit**

```bash
PYTHONPATH=backend conda run -n aoi-app python -m pytest tests/integration/test_settings_api.py tests/integration/test_auth_api.py -v
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin GITNEXUS_INVOCATION=npx node .gitnexus/run.cjs detect-changes
git add backend/app/api/settings.py backend/app/main.py backend/app/schemas/settings.py tests/integration/test_settings_api.py
git commit -m "feat(settings): expose versioned settings API"
```

---

### Task 5: Idempotent Activation and Same-Transaction Audit

**Files:**
- Modify: `backend/app/services/settings_service.py`, `backend/app/api/settings.py`, `backend/app/schemas/settings.py`, `backend/app/middleware/audit.py`, `backend/app/services/audit_service.py`, `backend/app/schemas/audit.py`, `tests/integration/test_audit_api.py`
- Test: `tests/integration/test_settings_activation.py`

**Interfaces:** Produces `activate_settings(...) -> SettingsActivation`; adds `POST/GET /api/v1/settings/{scope}/{subject_id}/activations`. Route sets `request.state.audit_recorded = True` only after same-transaction audit flush; middleware skips duplicate success audit but audits failures.

- [ ] **Step 1: Impact middleware/audit symbols**

```bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin GITNEXUS_INVOCATION=npx node .gitnexus/run.cjs impact AuditMiddleware --direction upstream
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin GITNEXUS_INVOCATION=npx node .gitnexus/run.cjs impact record_audit_event --direction upstream
```

- [ ] **Step 2: Add RED activation tests**

Cover missing/invalid key, unknown/non-owned version, first activation, exact replay, changed request with reused key, active pointer, history, audit checksums/reason, duplicate suppression, failed audit, and audit failure rolling back activation.

- [ ] **Step 3: Implement activation transaction**

Validate `Idempotency-Key` with `[A-Za-z0-9][A-Za-z0-9._-]{0,127}`. Request checksum covers document ID, requested version ID, and reason. Lock document, resolve version, insert activation, update active pointer, flush enriched audit, and commit once. Unique-race loser loads and compares existing activation. Store safe client metadata `{}` unless an explicit parser exists; never copy arbitrary headers.

- [ ] **Step 4: Verify and commit**

```bash
PYTHONPATH=backend conda run -n aoi-app python -m pytest tests/integration/test_settings_activation.py tests/integration/test_settings_api.py tests/integration/test_audit_api.py -v
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin GITNEXUS_INVOCATION=npx node .gitnexus/run.cjs detect-changes
git add backend/app/services/settings_service.py backend/app/api/settings.py backend/app/schemas/settings.py backend/app/middleware/audit.py backend/app/services/audit_service.py backend/app/schemas/audit.py tests/integration/test_settings_activation.py tests/integration/test_audit_api.py
git commit -m "feat(settings): activate versions idempotently"
```

---

### Task 6: Existing Preference File Migration

**Files:**
- Create: `backend/app/services/settings_file_migration.py`, `scripts/database/migrate-preferences.py`
- Test: `tests/backend/test_settings_file_migration.py`, `tests/integration/test_settings_file_migration.py`

**Interfaces:** Produces `discover_preference_files(root: Path)` and `migrate_preference_files(session, root, actor_id, apply=False)`. CLI requires `--actor-id`, defaults to dry-run, and persists only with `--apply`. Source files remain unchanged.

- [ ] **Step 1: Add RED migration tests**

Cover sorted discovery, identity mapping, defaults for old files, malformed/invalid content, path/payload identity mismatch, missing user, dry-run, apply, checksum no-op rerun, divergent destination conflict, and mixed-batch all-or-nothing behavior.

- [ ] **Step 2: Implement deterministic migration**

Accept only `users/<positive-user-id>/<valid-workstation-id>.json`. Parse compatibility schema, verify embedded identity, extract content, and validate registry. Build complete report before writes. Any invalid/conflicting candidate makes apply nonzero and writes nothing. Missing destination creates revision `1`; equal checksum is unchanged; different checksum is conflict. Report source-relative paths only.

- [ ] **Step 3: Verify and commit**

```bash
PYTHONPATH=backend conda run -n aoi-app python -m pytest tests/backend/test_settings_file_migration.py tests/integration/test_settings_file_migration.py -v
PYTHONPATH=backend conda run -n aoi-app python scripts/database/migrate-preferences.py --root data/preferences --actor-id 1
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin GITNEXUS_INVOCATION=npx node .gitnexus/run.cjs detect-changes
git add backend/app/services/settings_file_migration.py scripts/database/migrate-preferences.py tests/backend/test_settings_file_migration.py tests/integration/test_settings_file_migration.py
git commit -m "feat(settings): migrate legacy preference files"
```

---

### Task 7: Legacy Workstation Preference API Cutover

**Files:**
- Modify: `backend/app/services/workstation_preference_repository.py`, `backend/app/api/workstation_preferences.py`, `tests/backend/test_workstation_preference_repository.py`, `tests/integration/test_workstation_preference_api.py`, `tests/integration/test_audit_api.py`

**Interfaces:** Keeps `WorkstationPreferencesSchema` payload. Repository becomes `WorkstationPreferenceRepository(session: Session)`. Missing read returns unpersisted revision-0 default. Save creates one settings version and same-transaction audit. Removes filesystem writes and `_write_lock`.

- [ ] **Step 1: Run mandatory impact analysis**

```bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin GITNEXUS_INVOCATION=npx node .gitnexus/run.cjs impact WorkstationPreferenceRepository --direction upstream
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin GITNEXUS_INVOCATION=npx node .gitnexus/run.cjs impact get_preference_repository --direction upstream
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin GITNEXUS_INVOCATION=npx node .gitnexus/run.cjs impact update_preferences --direction upstream
```

Known current risk: LOW, one direct API importer and `main.py` transitively. Reassess before edits.

- [ ] **Step 2: Rewrite compatibility tests first**

Preserve defaults/revision 0, save/revision 1, locale/photometric round-trip, stale `409`, unsafe ID `422`, identity mismatch `422`, no file writes, and exactly one success audit.

- [ ] **Step 3: Implement PostgreSQL adapter**

Map generic payload/version metadata into compatibility envelope. API reads request ID assigned by middleware, commits once, sets `request.state.audit_recorded`, and maps generic conflict to legacy safe message.

- [ ] **Step 4: Verify and commit**

```bash
PYTHONPATH=backend conda run -n aoi-app python -m pytest tests/backend/test_workstation_preference_repository.py tests/integration/test_workstation_preference_api.py tests/integration/test_audit_api.py -v
cd frontend && npm run test && npm run typecheck && cd ..
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin GITNEXUS_INVOCATION=npx node .gitnexus/run.cjs detect-changes
git add backend/app/services/workstation_preference_repository.py backend/app/api/workstation_preferences.py tests/backend/test_workstation_preference_repository.py tests/integration/test_workstation_preference_api.py tests/integration/test_audit_api.py
git commit -m "refactor(settings): store workstation preferences in PostgreSQL"
```

---

### Task 8: Backup Export, Verification, and Documentation

**Files:**
- Create: `scripts/database/export-settings.py`, `scripts/database/verify-settings-export.py`, `tests/integration/test_settings_backup.py`
- Modify: `README.md`, `README.md.vn`, `.agents/experience/memory.md`, `.agents/experience/memory.md.vn`

**Interfaces:** Export writes deterministic JSON plus SHA-256 manifest without secrets. Offline verifier checks format version, count, checksums, manifest, and schema registry compatibility without DB mutation. Ordering: scope, subject, key, owner, revision.

- [ ] **Step 1: Add RED export tests**

Cover deterministic bytes, version/history/activation metadata, no password/token/secret fields, manifest verification, one-byte tamper rejection, unknown schema rejection, and empty database.

- [ ] **Step 2: Implement safe export/verification**

Write temporary sibling, flush, `fsync`, then `os.replace`. Refuse symlink output and parent traversal. Document that portable export is not a PostgreSQL disaster-recovery backup; native backup remains Phase 6.

- [ ] **Step 3: Update English/Vietnamese operations docs**

Document Alembic upgrade/current/check, stale-schema startup refusal, one-time baseline, preference dry-run/apply migration, PostgreSQL source of truth, version/conflict/rollback/activation contracts, portable export limits, and GitNexus WSL workaround.

- [ ] **Step 4: Run full verification**

```bash
bash scripts/test/test.sh
bash scripts/build/build.sh
bash -n scripts/run_dev.sh
bash -n scripts/install/setup-postgresql.sh
bash -n scripts/install/verify-environment.sh
cd frontend && npm audit --omit=dev --audit-level=moderate && cd ..
PYTHONPATH=backend conda run -n aoi-app python -m app.database.migrations current
PYTHONPATH=backend conda run -n aoi-app python -m app.database.migrations check
git diff --check
```

Manual acceptance: race two sessions at revision N; rollback and prove a new immutable row; replay/change activation key; repeat concurrency with two backend workers; dry-run/apply/rerun legacy migration in a disposable database.

- [ ] **Step 5: Detect, sync, and commit**

```bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin GITNEXUS_INVOCATION=npx node .gitnexus/run.cjs detect-changes
codegraph sync . && codegraph status .
git add scripts/database/export-settings.py scripts/database/verify-settings-export.py tests/integration/test_settings_backup.py README.md README.md.vn .agents/experience/memory.md .agents/experience/memory.md.vn
git commit -m "docs(settings): record version platform operations"
```

## Phase 1 Exit Gate

- Alembic owns schema evolution; startup rejects stale/unversioned databases.
- Settings documents, immutable versions, append-only activations, and enriched audit metadata live in PostgreSQL.
- Scope contracts cover User, Workstation, Recipe, and System identities.
- Concurrent edits cannot overwrite silently across workers.
- Rollback creates a source-linked new version.
- Activation is idempotent and failed/reused keys cannot move active pointer.
- Settings metadata and success audit commit atomically; failed requests remain middleware-audited.
- Legacy file migration preserves identity and supports dry-run, all-or-nothing apply, conflict reporting, and no-op rerun.
- Existing frontend preference calls remain compatible while PostgreSQL is source of truth.
- Portable JSON validates schema and SHA-256 and is not described as database backup replacement.
- Full tests, build, security audit, migrations, GitNexus, CodeGraph, and diff checks pass.