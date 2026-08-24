# Phase 6 model lifecycle acceptance evidence

**Date:** 2026-08-24  
**Scope:** Model registration, candidate/champion lifecycle, stable rollback, immutable production binding, and SVM inference.  
**Environment:** Python 3.12 `aoi-app` environment, PostgreSQL-backed FastAPI integration tests, React 18/Vitest, local CPU execution.

## Deterministic vertical slice

The automated journey `tests/integration/test_phase6_model_lifecycle_acceptance.py` executes:

1. deterministic cats/dogs fixtures with immutable dataset versions;
2. HOG/SVM training and evaluation;
3. checksum-backed model artifact persistence in a completed Research run;
4. authenticated v1 model creation and validated immutable version registration;
5. champion promotion with actor, reason, previous/next version, and timestamp evidence;
6. portable `{modelName, alias}` resolution to exact `{modelName, modelVersion, artifactSha256}`;
7. contextual SVM inference through a byte-length/checksum/media-bound artifact resolver;
8. `aoi.table.v1` report and `aoi.confusion-matrix.v1` visualization evidence.

The reusable deterministic fixture produced:

| Field | Evidence |
|---|---|
| Experiment ID | `animals-svm` |
| Run ID | `run-svm` |
| Node ID | `svm-image-classifier` |
| Package version | `1.0.0` |
| Model SHA-256 | `19f2a5cb7291a933f4e06b539ca5d7aeb24bc36148e3b9398e8a34edfcfc2cbe` |
| Model bytes | `586373` |
| Accuracy | `1.0` |
| Predictions | `0,0,0,1,1,1` |

Runtime database identifiers in the API journey include a UUID suffix to avoid collisions. The model bytes and SHA-256 remain deterministic for the recorded environment.

## Lifecycle and failure evidence

- Registration rejects anonymous requests, duplicate names, non-completed runs, failed validation, cross-run artifacts, missing artifacts, and integrity failures.
- Promotion supports only `candidate` and `champion`, revalidates passing evidence and artifact integrity, locks the alias row, and appends immutable audit events.
- Rollback requires a target-visible preview, rejects stale previews, locks and revalidates the target artifact before mutation, and appends a rollback event without creating a `rollback` alias.
- Training cancellation is observed at bounded node checkpoints and persists no partial artifact.
- Training failure returns a safe message and persists no partial artifact.
- Production rejects missing aliases, versions, artifacts, mismatched checksums, portable aliases inside the core executor, and execution-context mismatches.
- A resolved context remains pinned to its original version and artifact bytes after a later alias update.

## Verification results

- Phase 6 acceptance-critical Python matrix: **PASS, 200 tests** before adding the aggregate journey; the aggregate journey then passed independently (**1 test**).
- Full frontend: **PASS, 47 files / 133 tests**.
- Frontend typecheck: **PASS**.
- Frontend production build: **PASS**; the existing non-fatal chunk warning above 500 kB remains.
- Production Python compile (`backend`, `core`): **PASS**.
- Full Python test tree after stale Phase 3/4 assertions were synchronized: **525 passed, 11 unrelated failures, 2 dependency warnings**.

The 11 non-acceptance failures are recorded separately and do not touch the Phase 6 model lifecycle path:

1. three known DEBUG KNN/documentation generator failures;
2. one legacy KNN deterministic validation-accuracy expectation;
3. six legacy CSV dataset API preparation/artifact failures;
4. one legacy settings-backup checksum fixture failure.

Compiling the entire test tree additionally exposes the pre-existing invalid demonstration script `tests/nodes/knn_cat_dog.py` (`import scikit-learn as sklearn`). Production `backend` and `core` compile successfully.

## Claim boundary

This evidence supports deterministic local-CPU inference for the exact Python/OpenCV/NumPy/scikit-learn runtime recorded and verified inside the signed SVM artifact envelope. It does not claim GPU support, cross-runtime pickle portability, factory accuracy, target-hardware cycle time, production uptime, or physical pilot acceptance.
