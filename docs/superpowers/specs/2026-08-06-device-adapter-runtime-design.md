# AOI Device Adapter and Inspection Runtime Design

## Goal

Complete AOI Studio as a hardware-independent inspection system for an NVIDIA Jetson Orin Nano Super 8GB, one CSI camera, and an external three-axis MCU motion controller connected through UART. The same core application must run against reliable local simulators before physical hardware is available.

## Decisions

- Use custom Python services without ROS 2.
- Keep the React/FastAPI/PostgreSQL control plane.
- Isolate camera and MCU access behind HTTP services bound only to `127.0.0.1`.
- Use HTTP request/response for camera capture and motion commands.
- Use Server-Sent Events for motion state and fault notifications; always confirm safety-critical state through `GET /state`.
- Start hardware adapters by default. Start simulator adapters only with an explicit simulation mode.
- Never silently fall back from hardware to simulation.
- Keep mirrored `hardware/camera`, `hardware/mcu`, `simulator/camera`, and `simulator/mcu` boundaries while sharing protocol contracts from `core/devices`.

## Runtime Topology

```text
React HMI :5173
    |
FastAPI control plane :8000
    |-- HTTP --> camera adapter :9101
    `-- HTTP + SSE --> motion adapter :9102

hardware mode:
  camera adapter -> Jetson Argus/GStreamer -> CSI camera
  motion adapter -> UART protocol -> MCU -> X/Y/Z motors

simulation mode:
  camera adapter -> deterministic dataset replay
  motion adapter -> deterministic virtual X/Y/Z state machine
```

The browser never calls adapter services directly. The main backend owns authentication, orchestration, persistence, and user-facing errors.

## Common Service Contract

Every adapter exposes:

- `GET /health`
- `GET /version`
- `GET /capabilities`

The protocol version is explicit. The main backend rejects an incompatible adapter.

## Camera Contract

The camera service exposes configuration and idempotent capture transactions:

- `GET /configuration`
- `PUT /configuration`
- `POST /captures`
- `GET /captures/{captureId}`
- `GET /captures/{captureId}/inspection-image`
- optional `GET /captures/{captureId}/raw`
- `GET /preview`

Inspection images are lossless PNG or TIFF and are never embedded as base64 JSON. Raw Bayer is optional and capability-gated because CSI sensor and Jetson driver support differs. Preview frames are explicitly non-inspection artifacts.

Each capture records request ID, frame ID, UTC and monotonic timestamps, sensor identity and mode, exposure, gain, white-balance state, expected XYZ position, calibration ID, processing profile, byte length, media type, and SHA-256.

The camera service writes artifacts through a temporary sibling, flushes and synchronizes the file, atomically replaces the destination, computes the checksum, and only then returns `ready`. Repeating a request ID returns the same completed transaction instead of capturing again.

## Motion Contract

The motion service exposes:

- `GET /state`
- `GET /events` as `text/event-stream`
- `POST /commands/home`
- `POST /commands/move-absolute`
- `POST /commands/stop`
- `POST /commands/clear-fault`
- `GET /commands/{commandId}`

Motion states are `boot`, `not-homed`, `homing`, `idle`, `moving`, `stopping`, `fault`, and `emergency-stop`. Absolute moves are the default because duplicate handling is safer than relative moves. Commands use client-generated IDs and are idempotent.

The main runtime captures only after receiving an `in-position` event, confirming `GET /state`, checking pose tolerance, and waiting the recipe settle duration.

## UART Boundary

Only `hardware/mcu` accesses UART. The wire protocol is independent of STM32, ESP32, Arduino, or RP2040:

- bounded binary frames;
- explicit protocol version and message type;
- sequence number and payload length;
- fixed-width integers in declared byte order;
- XYZ and rates represented in integer micrometers;
- CRC-32;
- escaped or COBS-delimited frame boundary;
- heartbeat and watchdog;
- duplicate-sequence handling.

The MCU owns homing, trajectories, step generation, acceleration, hard/soft limits, emergency stop, and communication-loss behavior. The Jetson sends high-level commands only.

## Directory Ownership

```text
core/devices/             shared domain and protocol contracts
hardware/camera/          Jetson CSI adapter
hardware/mcu/             UART motion adapter
simulator/camera/         replay/synthetic camera adapter
simulator/mcu/            virtual motion adapter
backend/app/clients/      adapter HTTP clients
backend/app/services/     inspection orchestration
backend/app/api/          authenticated control-plane endpoints
data/captures/            immutable capture artifacts
data/inspections/         run evidence and intermediate artifacts
data/calibration/         versioned calibration documents
data/models/              versioned model/golden artifacts
```

## Inspection Lifecycle

```text
created -> precheck -> homing -> moving -> settling -> capturing
        -> quality-gate -> registering -> inspecting -> deciding
        -> persisting -> completed
```

Any active state may transition to `cancelled` or `faulted`. State transitions are persisted. After restart, the software never resumes motion automatically.

## Initial Release Pipeline

Only a tested vertical slice becomes runnable:

1. replay or CSI capture;
2. camera undistortion when calibration is configured;
3. image quality gate;
4. registration;
5. golden median/MAD comparison;
6. absolute difference and gradient evidence;
7. connected-component evidence filtering;
8. score normalization and `PASS` / `REVIEW` / `FAIL` decision.

PatchCore is a benchmark candidate after the deterministic OpenCV baseline. Paper benchmark results are not acceptance evidence for PCB data.

## Persistence and Traceability

PostgreSQL stores inspection metadata and references; large image artifacts remain on NVMe-backed files. A result records recipe/workflow revision, calibration version, model or golden artifact hash, camera configuration, XYZ pose, raw/canonical image hashes, node parameters, thresholds, timings, initial decision, and any review override.

Database schema changes use migrations before inspection tables are introduced. Runtime evidence has explicit retention and disk-space preflight checks.

## Launcher

Supported commands:

```bash
bash scripts/run_dev.sh
bash scripts/run_dev.sh start
bash scripts/run_dev.sh start --mode simulation
bash scripts/run_dev.sh simulation
bash scripts/run_dev.sh status
bash scripts/run_dev.sh stop
```

Hardware is the default. The launcher owns camera, motion, backend, and frontend process groups; reserves ports 9101, 9102, 8000, and 5173; waits for every health endpoint; and stops all owned groups on exit.

## Acceptance Gates

- Hardware and simulator implementations pass the same contract tests.
- One thousand deterministic simulated runs complete without deadlock or artifact mismatch.
- Adapter timeout, stale pose, checksum mismatch, camera failure, motion fault, UART loss, disk-full, and backend restart paths are tested.
- Every completed run is reproducible from persisted versions and checksums.
- No UI or FastAPI handler generates motor pulses or opens the CSI device directly.
- Hardware mode never falls back to simulation without an explicit restart command.
- All existing backend, core, integration, frontend, typecheck, and build checks remain green.

## External References

- NVIDIA Jetson camera architecture: libargus, `nvarguscamerasrc`, GStreamer, V4L2, and CSI driver guidance.
- EMVA GenICam for future vendor-neutral camera capability design.
- EMVA 1288 / ISO 24942 for objective camera characterization.
- OPC UA Machine Vision Part 1 as a semantic reference for state, recipe, and result management, without requiring OPC UA in this milestone.
- OpenCV calibration and registration practices.
- PatchCore, CVPR 2022, and Anomalib for anomaly benchmark methodology.