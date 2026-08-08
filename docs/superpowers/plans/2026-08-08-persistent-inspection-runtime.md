# Persistent Inspection Runtime — Phase 5 Record

**Status:** implemented and simulator-accepted on 2026-08-08.

## Scope and Constraints

- PostgreSQL is the source of truth for run state; worker threads are execution mechanisms only.
- Application restart never resumes physical motion. Startup changes every non-terminal run to
  `faulted` or `cancelled` without calling a device adapter.
- Capture is allowed only after fresh, homed, in-position motion state and closed safety interlocks.
- Inspection artifacts are lossless, SHA-256 verified, atomically written, and content addressed.
- Corrupt, blurred, unregistered, stale-pose, interlock-invalid, or checksum-invalid input cannot PASS.
- Existing manifest nodes remain configuration-only unless separately promoted. Phase 5 executes
  one bounded deterministic PCB reference node after the verified camera/motion boundary.

## Data Model

Migration `0004_create_inspection_runtime` adds:

- `inspection_runs`: persisted state, workflow snapshot/hash, effective versions, parameters,
  artifact manifest, decision, evidence hash, errors, timing, cancellation intent, result link.
- `inspection_node_runs`: ordered node version/target, parameters, resources, inputs, outputs,
  evidence, status, timing, and normalized errors.
- `inspection_review_events`: append-only actor, decision, reason, and timestamp history.

Existing `inspection_results`, `defects`, and `inspection_images` remain query-compatible.

## State and Recovery

```text
queued → precheck → capturing → executing → completed
   │         │           │           │
   └─────────┴───────────┴───────────┴→ cancelled | faulted
```

Each transition commits before external work. Cancellation persists intent and takes effect at the
next safe checkpoint. Adapter timeout cannot override an already-persisted cancellation intent.
Startup recovery maps `queued/precheck` to cancelled and `capturing/executing` to faulted.

## API and UI

- `POST /api/inspection-runs`
- `GET /api/inspection-runs/active`
- `GET /api/inspection-runs/latest`
- `GET /api/inspection-runs/{run_id}`
- `POST /api/inspection-runs/{run_id}/cancel`
- `POST /api/inspection-runs/{run_id}/replay`

AOI Studio Run/Stop controls use these persisted endpoints. Dashboard shows run ID, board serial,
physical stage, progress, terminal decision, fault detail, and immutable evidence hash.

## Versioned Replay

- `deterministic-reference@1.0.0`: legacy digest-derived score; retained for exact old-run replay.
- `deterministic-reference@2.0.0`: decoded-pixel reference score plus explicit algorithm version in evidence.

Runs pin an effective version. Replay dispatches that immutable implementation and verifies artifact
SHA-256 and byte length before execution. Unsupported versions fail closed.

## Acceptance Evidence

- 1,000 deterministic in-process runs: identical decision and evidence hash; no deadlock.
- Focused safety matrix: corrupt, blurred, unregistered, stale pose, invalid checksum, motion not in position.
- PostgreSQL integration: completed evidence, append-only review, cancellation, restart recovery, replay.
- Live simulator:
  - stale pose persisted FAULT before capture;
  - normal run persisted PASS with node evidence;
  - cancellation persisted terminal `cancelled` with no result/node execution;
  - both reference versions replayed exact original evidence hashes.
- Responsive AOI Studio: no horizontal document overflow at CSS widths 390, 768, 1280, and 1920.

## Deferred Work

- Broad release-node execution and validated ML inference remain later phases.
- Jetson CSI/UART hardware acceptance remains device-dependent.
- Multi-station distributed scheduling requires a durable external worker/lease design; current scope is one AOI workstation.