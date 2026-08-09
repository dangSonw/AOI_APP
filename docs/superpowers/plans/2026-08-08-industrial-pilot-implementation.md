# Industrial Pilot Implementation — Phase 6 Foundation

**Status:** software foundation implemented; real pilot acceptance blocked pending factory contracts and target hardware.

## Known Contracts

- Camera: Jetson CSI through a bounded GStreamer argv, lossless PNG output, atomic publish, SHA-256 evidence.
- Motion transport: UART frame version 1 with magic, sequence, frame type, bounded payload, and CRC-32.
- Calibration: immutable artifact checksum, acquisition metrics, validity, expiry, station/camera lineage.
- Commissioning: versioned station profile, deployment mode, typed PLC signal map, typed PLC/MES outage policy.
- Integration: durable idempotent outbox for completed inspection result exchange.
- Operations: disk/quota preflight, legal-hold-aware retention plan, backup manifest, restore catalog dry-run.
- Acceptance: typed target-hardware measurements for cycle time, false-call rate, escape rate, uptime, and recovery time.

## Fail-Closed Rules

1. Hardware camera reports ready only when GStreamer is available; no simulation fallback.
2. Hardware-pilot/production profile activation requires valid unexpired calibration.
3. Every run pins commissioning, calibration, signal mapping, and integration policy snapshots.
4. Calibration expiry blocks execution before physical capture.
5. Integration outage behavior is explicit: PLC `block|fail-safe`, MES `queue|block`.
6. Deployment preflight exits blocked without a valid measured pilot acceptance report.
7. Restore dry-run verifies checksums and PostgreSQL archive catalog without overwriting a database.

## Delivered Files

- `hardware/camera/csi_capture.py`
- `hardware/mcu/uart_protocol.py`
- `hardware/mcu/uart_transport.py`
- `database/migrations/versions/0005_create_pilot_foundation.py`
- `backend/app/models/pilot.py`
- `backend/app/services/pilot_service.py`
- `backend/app/services/pilot_operations.py`
- `backend/app/services/pilot_acceptance.py`
- `backend/app/api/pilot.py`
- `scripts/operations/pilot-backup.py`
- `scripts/operations/pilot-restore-dry-run.py`
- `scripts/operations/verify-pilot-acceptance.py`

## Blocked Target-Hardware Work

These items cannot be truthfully completed from the repository alone:

- MCU command/ACK/state payload mapping and watchdog acceptance: firmware contract required.
- PLC electrical signal names, polarity, timing, debounce, and handshake: PLC I/O contract required.
- MES authentication, work-order schema, serial ownership, retry SLA: factory MES contract required.
- Optional IPC-CFX/OPC UA endpoint profiles: factory integration requirements required.
- CSI sensor mode/exposure acceptance: Jetson + selected sensor required.
- Safety, cycle time, false-call, escape, uptime, and recovery acceptance: production fixture and labeled PCB set required.
- Backup restore into an isolated target database: pilot operations window and approved target required.

## Acceptance Workflow

1. Place calibration JSON under `data/calibration` through authenticated API.
2. Create calibration record and versioned commissioning profile; activate only after quality gates pass.
3. Run labeled pilot boards and collect measured report using schema enforced by `pilot_acceptance.py`.
4. Create backup and run restore dry-run.
5. Set `AOI_PILOT_ACCEPTANCE_REPORT` and run `bash scripts/deploy/deploy.sh`.
6. Deployment remains blocked until every typed gate is passed.