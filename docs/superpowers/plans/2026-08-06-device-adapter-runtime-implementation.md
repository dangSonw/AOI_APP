# AOI Device Adapter and Inspection Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans task-by-task. Every behavior change follows red-green-refactor.

**Goal:** Deliver a hardware-default AOI runtime with mirrored camera/motion simulators, reliable loopback APIs, persistent inspection runs, a deterministic vision baseline, and Jetson CSI/UART adapter boundaries.

**Architecture:** Shared device contracts live in `core/devices`. Four isolated FastAPI adapter processes implement camera and motion contracts in hardware and simulation modes. The authenticated main backend orchestrates adapters and persists traceable inspection records while the browser communicates only with the main backend.

**Tech Stack:** Python 3.12, FastAPI, Pydantic 2, SQLAlchemy 2, HTTPX, pytest, OpenCV headless, NumPy, pySerial, React 18, TypeScript 5.6, Vitest, Jetson Argus/GStreamer.

## Global Constraints

- Hardware mode is the default and never silently falls back to simulation.
- Adapter ports bind only to `127.0.0.1`.
- Camera inspection artifacts are lossless and checksum-verified; preview is never an inspection input.
- MCU firmware owns motor timing, homing, limits, emergency stop, and watchdog behavior.
- Existing uncommitted login changes must not be reset or overwritten.
- Every changed Markdown file has a `.md.vn` companion.
- Run CodeGraph impact before editing an existing symbol and synchronize CodeGraph after each milestone.

---

## Task 1: Shared Device Contracts

**Files:**
- Create: `core/devices/models.py`
- Create: `core/devices/camera.py`
- Create: `core/devices/motion.py`
- Create: `core/devices/errors.py`
- Test: `tests/core/test_device_contracts.py`

**Deliverable:** Versioned health, capability, camera capture, XYZ position, command, state, and fault models with strict bounded validation and camelCase API serialization.

**Verification:** `python -m pytest tests/core/test_device_contracts.py -v`

## Task 2: Mirrored Adapter Service Skeletons

**Files:**
- Create matching modules under `hardware/camera`, `hardware/mcu`, `simulator/camera`, and `simulator/mcu`.
- Test: `tests/contract/test_adapter_contracts.py`

**Deliverable:** All four services expose compatible `/health`, `/version`, and `/capabilities`; simulator services report ready, hardware services report unavailable with actionable diagnostics when a device is absent.

**Verification:** contract tests instantiate every FastAPI app without requiring Jetson or UART hardware.

## Task 3: Deterministic Motion Simulator and SSE

**Files:**
- Create: `simulator/mcu/motion_service.py`
- Create: `simulator/mcu/app.py`
- Test: `tests/simulator/test_motion_service.py`

**Deliverable:** Idempotent home/move/stop/clear-fault commands, bounded XYZ workspace, deterministic clock support, command records, state revisions, and SSE event serialization.

**Verification:** duplicate absolute move does not execute twice; capture preconditions can distinguish moving, stale, faulted, and in-position states.

## Task 4: UART Codec and Hardware Motion Adapter

**Files:**
- Create: `hardware/mcu/uart_protocol.py`
- Create: `hardware/mcu/uart_transport.py`
- Create: `hardware/mcu/motion_service.py`
- Test: `tests/hardware/test_uart_protocol.py`
- Test: `tests/hardware/test_uart_motion_service.py`

**Deliverable:** Bounded binary frames with version, sequence, type, payload length, integer-micrometer payloads, CRC-32, framing, duplicate handling, heartbeat, timeout, and lazy pySerial access.

**Verification:** corrupted/truncated/oversized frames are rejected and pseudo-terminal tests exercise handshake, move, event, and watchdog paths.

## Task 5: Camera Replay and Artifact Integrity

**Files:**
- Create: `simulator/camera/replay_camera.py`
- Create: `simulator/camera/capture_service.py`
- Create: `simulator/camera/app.py`
- Test: `tests/simulator/test_camera_service.py`

**Deliverable:** Idempotent capture transactions, deterministic dataset lookup, lossless artifacts, atomic writes, SHA-256 verification, metadata, and controlled timeout/corruption/blur/exposure fault injection.

**Verification:** repeated request IDs return one artifact; content hash and pose metadata match; incomplete artifacts are never visible as ready.

## Task 6: Jetson CSI Camera Adapter

**Files:**
- Create: `hardware/camera/jetson_csi_camera.py`
- Create: `hardware/camera/capture_service.py`
- Create: `hardware/camera/app.py`
- Test: `tests/hardware/test_jetson_camera_configuration.py`

**Deliverable:** Lazy GStreamer/Argus pipeline construction, capability discovery, locked recipe settings, lossless output, optional raw capability, health diagnostics, and no Jetson import requirement on x86.

**Verification:** pipeline/configuration tests pass on x86; hardware acceptance script validates actual sensor modes later on Jetson.

## Task 7: Launcher Modes and Four-Process Lifecycle

**Files:**
- Modify: `scripts/run_dev.sh`
- Modify: `scripts/run-dev-wsl.ps1`
- Modify: `.env.example`
- Modify: `backend/app/config/settings.py`
- Test: `tests/integration/test_developer_launcher.py`

**Deliverable:** `start|stop|status`, hardware default, `start --mode simulation`, `simulation` alias, ports 9101/9102, four process groups, full health wait, and no fallback.

**Verification:** shell syntax check, launcher parsing tests, simulated stack startup/stop/status test, and existing stack duplicate detection.

## Task 8: Adapter Clients and Authenticated Gateway

**Files:**
- Create: `backend/app/clients/camera_client.py`
- Create: `backend/app/clients/motion_client.py`
- Create: `backend/app/api/camera.py`
- Create: `backend/app/api/motion.py`
- Modify: `backend/app/main.py`
- Test: `tests/backend/test_device_clients.py`
- Test: `tests/integration/test_device_gateway_api.py`

**Deliverable:** Typed HTTPX clients with separate connect/read/write timeouts, protocol checks, hash verification, normalized errors, and protected gateway endpoints.

## Task 9: Persistent Inspection Orchestrator

**Files:**
- Create: `core/inspection/models.py`
- Create: `core/inspection/state_machine.py`
- Create: `backend/app/models/inspection.py`
- Create: `backend/app/services/inspection_service.py`
- Create: `backend/app/api/inspections.py`
- Add database migration tooling and first migration.
- Test: `tests/core/test_inspection_state_machine.py`
- Test: `tests/integration/test_inspection_api.py`

**Deliverable:** Move-settle-capture-inspect-persist lifecycle, cancellation, fault persistence, restart-safe recovery that never resumes motion, and status/event APIs.

## Task 10: Deterministic Vision Baseline

**Files:**
- Create focused modules under `core/vision` and `core/inspection`.
- Promote only selected acquisition, undistortion, registration, golden, evidence, and decision node runtimes.
- Add OpenCV/NumPy dependencies.
- Test: `tests/core/vision/*`
- Test: `tests/integration/test_replay_inspection.py`

**Deliverable:** Quality gate, optional undistortion, registration, median/MAD golden model, absolute/gradient evidence, connected components, score normalization, and three-state decision with versioned artifacts.

**Verification:** golden fixture images produce deterministic scores and hashes; corrupted/blurred/unregistered images never produce PASS.

## Task 11: Inspection Records and Evidence UI

**Files:**
- Create backend schemas/services/API for records, evidence, review, and metrics.
- Replace hard-coded `INSPECTION_RECORDS` usage in `DatabasePage` with a frontend service.
- Connect Run control to inspection API and stream status.
- Test backend APIs and frontend service/utilities/components.

**Deliverable:** Searchable real records, evidence metadata/download, review override with actor/timestamp, and truthful metrics.

## Task 12: Operations, Documentation, and Acceptance

**Files:**
- Modify: `README.md`, `README.md.vn`, script docs, setup/test/deploy scripts.
- Update experience memory in both languages.
- Add Jetson hardware acceptance and simulator soak scripts.

**Deliverable:** Current architecture, modes, ports, data layout, Jetson setup, CSI/UART acceptance, backups, retention, diagnostics, and limitations documented accurately.

**Final Verification:**

```bash
bash scripts/test/test.sh
bash scripts/build/build.sh
bash -n scripts/run_dev.sh
codegraph sync .
codegraph status .
git diff --check
```

Run simulation end-to-end, fault matrix, restart recovery, and a 1,000-run deterministic soak before declaring pre-hardware readiness.