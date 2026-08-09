from __future__ import annotations

import hashlib
import json
import logging
import os
import struct
import time
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.clients.camera_client import CameraClient
from app.clients.device_client import DeviceServiceError
from app.clients.motion_client import MotionClient
from app.models.defect import Defect
from app.models.inspection_image import InspectionImage
from app.models.inspection_result import InspectionResult
from app.models.inspection_run import InspectionNodeRun, InspectionRun
from app.models.pilot import CommissioningProfile, IntegrationOutboxEvent
from app.models.recipe import Recipe
from app.schemas.inspection_run import InspectionRunCreateRequest
from app.services.inspection_orchestrator import (
    CancellationToken,
    ExecutionContext,
    InspectionCancelled,
    InspectionInput,
    InspectionOrchestrator,
    recover_interrupted_status,
)
from app.services.pilot_service import commissioning_snapshot
from app.services.workflow_repository import WorkflowRepository
from core.devices.camera import CaptureRequest
from core.nodes import get_node_manifest_registry


TERMINAL_STATUSES = {'completed', 'faulted', 'cancelled'}
ACTIVE_STATUSES = {'queued', 'precheck', 'capturing', 'executing'}
POSE_TOLERANCE_SECONDS = 60.0
POSITION_TOLERANCE_MILLIMETERS = 0.01
INSPECTION_RUN_ADVISORY_LOCK = 0x414F4952554E
LOGGER = logging.getLogger(__name__)


class InspectionRunError(RuntimeError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def _transition(
    session: Session,
    run: InspectionRun,
    status: str,
    step: str,
    progress: int,
) -> None:
    run.status = status
    run.current_step = step
    run.progress_percent = progress
    if run.started_at is None and status != 'queued':
        run.started_at = _now()
    if status in TERMINAL_STATUSES:
        run.completed_at = _now()
    session.commit()


def _load_run(session: Session, run_id: str) -> InspectionRun | None:
    return session.scalar(
        select(InspectionRun)
        .execution_options(populate_existing=True)
        .options(selectinload(InspectionRun.node_runs))
        .where(InspectionRun.id == run_id),
    )


def get_run(session: Session, run_id: str) -> InspectionRun | None:
    return _load_run(session, run_id)


def get_latest_active_run(session: Session) -> InspectionRun | None:
    return session.scalar(
        select(InspectionRun)
        .options(selectinload(InspectionRun.node_runs))
        .where(InspectionRun.status.in_(ACTIVE_STATUSES))
        .order_by(InspectionRun.created_at.desc())
        .limit(1),
    )


def get_latest_run(session: Session) -> InspectionRun | None:
    return session.scalar(
        select(InspectionRun)
        .execution_options(populate_existing=True)
        .options(selectinload(InspectionRun.node_runs))
        .order_by(InspectionRun.created_at.desc())
        .limit(1),
    )


def create_run(
    session: Session,
    request: InspectionRunCreateRequest,
    operator_id: int,
    projects_root: Path,
) -> InspectionRun:
    session.execute(select(func.pg_advisory_xact_lock(INSPECTION_RUN_ADVISORY_LOCK)))
    recipe = session.get(Recipe, request.recipe_id)
    if recipe is None or not recipe.is_active:
        raise InspectionRunError('Active recipe does not exist.')
    existing = get_latest_active_run(session)
    if existing is not None:
        raise InspectionRunError(f'Inspection run {existing.id} is already active.')

    repository = WorkflowRepository(projects_root)
    workflow = repository.read(recipe.slug)
    snapshot = repository.serialize(workflow)
    manifests = get_node_manifest_registry()
    effective_versions = {
        node.algorithm_id: manifests[node.algorithm_id].package_version
        for node in workflow.nodes
        if node.algorithm_id in manifests
    }
    effective_versions['deterministic-reference'] = '2.0.0'
    parameters = request.model_dump(mode='json', by_alias=True)
    try:
        pilot_snapshot = commissioning_snapshot(
            session, request.station_id, projects_root.parent / 'calibration',
        )
    except ValueError as error:
        raise InspectionRunError('Station commissioning calibration evidence is invalid.') from error
    if pilot_snapshot is None:
        has_profile = session.scalar(select(CommissioningProfile.id).where(
            CommissioningProfile.station_id == request.station_id,
        ).limit(1))
        if has_profile is not None:
            raise InspectionRunError('Station commissioning profile is not active or valid.')
        pilot_snapshot = {
            'stationId': request.station_id,
            'deploymentMode': 'simulation-uncommissioned',
            'signalMapping': {},
            'integrationPolicy': {},
            'calibration': None,
        }
    run = InspectionRun(
        id=f'inspection-{uuid4().hex}', board_serial=request.board_serial, lot=request.lot,
        recipe_id=request.recipe_id, operator_id=operator_id, status='queued', current_step='queued',
        workflow_snapshot=snapshot, workflow_sha256=_canonical_sha256(snapshot),
        effective_versions=effective_versions, parameters=parameters,
        station_id=request.station_id, work_order_id=request.work_order_id,
        commissioning_snapshot=pilot_snapshot,
    )
    session.add(run)
    session.commit()
    return _load_run(session, run.id) or run


def request_cancellation(session: Session, run_id: str) -> InspectionRun | None:
    run = session.get(InspectionRun, run_id)
    if run is None:
        return None
    if run.status in TERMINAL_STATUSES:
        return _load_run(session, run_id)
    run.cancel_requested = True
    if run.status in {'queued', 'precheck'}:
        _transition(session, run, 'cancelled', 'cancelled', run.progress_percent)
    else:
        session.commit()
    return _load_run(session, run_id)


def recover_interrupted_runs(session: Session) -> int:
    interrupted = list(session.scalars(select(InspectionRun).where(InspectionRun.status.in_(ACTIVE_STATUSES))))
    recovered = 0
    for run in interrupted:
        next_status, error_code = recover_interrupted_status(run.status)
        run.status = next_status
        run.current_step = 'restart-recovery'
        run.error_code = error_code
        run.error_message = 'Run stopped during application restart; physical motion was not resumed.'
        run.completed_at = _now()
        recovered += 1
    if recovered:
        session.commit()
    return recovered


def _check_cancelled(session: Session, run: InspectionRun) -> None:
    session.refresh(run, attribute_names=['cancel_requested'])
    if run.cancel_requested:
        raise InspectionCancelled(f'Inspection run {run.id} was cancelled.')


def _positions_match(first: object, second: object) -> bool:
    return all(
        abs(getattr(first, field) - getattr(second, field)) <= POSITION_TOLERANCE_MILLIMETERS
        for field in ('x_millimeters', 'y_millimeters', 'z_millimeters')
    )


def _png_pixels(image_bytes: bytes) -> tuple[int, int, bytes]:
    if len(image_bytes) < 33 or image_bytes[:8] != b'\x89PNG\r\n\x1a\n':
        raise InspectionRunError('Captured artifact is corrupt.')
    offset = 8
    width = height = color_type = bit_depth = 0
    compressed = bytearray()
    saw_end = False
    while offset + 12 <= len(image_bytes):
        length = struct.unpack('>I', image_bytes[offset:offset + 4])[0]
        chunk_type = image_bytes[offset + 4:offset + 8]
        end = offset + 12 + length
        if end > len(image_bytes):
            raise InspectionRunError('Captured artifact is corrupt.')
        payload = image_bytes[offset + 8:offset + 8 + length]
        expected_crc = struct.unpack('>I', image_bytes[offset + 8 + length:end])[0]
        if zlib.crc32(chunk_type + payload) & 0xFFFFFFFF != expected_crc:
            raise InspectionRunError('Captured artifact is corrupt.')
        if chunk_type == b'IHDR':
            width, height, bit_depth, color_type = struct.unpack('>IIBB', payload[:10])
        elif chunk_type == b'IDAT':
            compressed.extend(payload)
        elif chunk_type == b'IEND':
            saw_end = True
            break
        offset = end
    if not saw_end or width <= 0 or height <= 0 or bit_depth != 8 or color_type not in {0, 2}:
        raise InspectionRunError('Captured artifact is corrupt or unsupported.')
    channels = 1 if color_type == 0 else 3
    try:
        raw = zlib.decompress(bytes(compressed))
    except zlib.error as error:
        raise InspectionRunError('Captured artifact is corrupt.') from error
    stride = width * channels
    if len(raw) != height * (stride + 1):
        raise InspectionRunError('Captured artifact is corrupt.')
    rows: list[bytearray] = []
    cursor = 0
    for _ in range(height):
        filter_type = raw[cursor]
        cursor += 1
        scanline = bytearray(raw[cursor:cursor + stride])
        cursor += stride
        prior = rows[-1] if rows else bytearray(stride)
        for index in range(stride):
            left = scanline[index - channels] if index >= channels else 0
            above = prior[index]
            upper_left = prior[index - channels] if index >= channels else 0
            if filter_type == 1:
                scanline[index] = (scanline[index] + left) & 255
            elif filter_type == 2:
                scanline[index] = (scanline[index] + above) & 255
            elif filter_type == 3:
                scanline[index] = (scanline[index] + ((left + above) // 2)) & 255
            elif filter_type == 4:
                estimate = left + above - upper_left
                distances = (abs(estimate - left), abs(estimate - above), abs(estimate - upper_left))
                predictor = (left, above, upper_left)[distances.index(min(distances))]
                scanline[index] = (scanline[index] + predictor) & 255
            elif filter_type != 0:
                raise InspectionRunError('Captured artifact uses an unsupported PNG filter.')
        rows.append(scanline)
    return width, height, b''.join(rows)


def _is_blurred(image_bytes: bytes) -> bool:
    width, height, pixels = _png_pixels(image_bytes)
    channels = len(pixels) // (width * height)
    values = [sum(pixels[index:index + channels]) / channels for index in range(0, len(pixels), channels)]
    if len(values) < 2:
        return True
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return variance < 16.0


def _reference_score(image_bytes: bytes) -> float:
    width, height, pixels = _png_pixels(image_bytes)
    channels = len(pixels) // (width * height)
    luminance = [sum(pixels[index:index + channels]) / channels for index in range(0, len(pixels), channels)]
    mean = sum(luminance) / len(luminance)
    return min(abs(mean - 127.5) / 127.5, 1.0)


def _store_artifact(root: Path, content: bytes, sha256: str, media_type: str) -> str:
    extension = '.png' if media_type == 'image/png' else '.tiff'
    relative = Path('inspection-runs') / sha256[:2] / f'{sha256}{extension}'
    destination = root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if hashlib.sha256(destination.read_bytes()).hexdigest() != sha256:
            raise InspectionRunError('Stored artifact checksum is invalid.')
        return relative.as_posix()
    temporary = destination.with_suffix(destination.suffix + '.tmp')
    with temporary.open('wb') as artifact_file:
        artifact_file.write(content)
        artifact_file.flush()
        os.fsync(artifact_file.fileno())
    temporary.replace(destination)
    return relative.as_posix()


def _fault(session: Session, run: InspectionRun, code: str, message: str) -> InspectionRun:
    run.error_code = code
    run.error_message = message[:500]
    run.decision = 'FAULT'
    _transition(session, run, 'faulted', 'faulted', run.progress_percent)
    return _load_run(session, run.id) or run


def execute_run(
    session: Session,
    run_id: str,
    camera: CameraClient,
    motion: MotionClient,
    artifact_root: Path,
) -> InspectionRun:
    run = session.get(InspectionRun, run_id)
    if run is None:
        raise InspectionRunError('Inspection run does not exist.')
    if run.status != 'queued':
        raise InspectionRunError('Only queued inspection runs can execute.')
    request = InspectionRunCreateRequest.model_validate(run.parameters)
    started = time.monotonic()
    try:
        _transition(session, run, 'precheck', 'motion-precheck', 10)
        _check_cancelled(session, run)
        calibration = run.commissioning_snapshot.get('calibration')
        if run.commissioning_snapshot.get('deploymentMode') in {'hardware-pilot', 'production'}:
            if calibration is None or datetime.fromisoformat(calibration['validUntil']) <= _now():
                return _fault(session, run, 'invalid-calibration', 'Production calibration is missing or expired.')
        state = motion.state()
        pose_age = (_now() - state.updated_at).total_seconds()
        if pose_age < 0 or pose_age > POSE_TOLERANCE_SECONDS:
            return _fault(session, run, 'stale-pose', 'Motion pose is stale; refresh or move the stage before capture.')
        if state.emergency_stop or not state.door_closed or not state.communication_connected:
            return _fault(session, run, 'motion-interlock', 'Motion safety interlock or communication state is not ready.')
        if (
            not state.is_homed or not state.is_in_position
            or not _positions_match(state.position, request.expected_position)
        ):
            return _fault(session, run, 'motion-not-in-position', 'Motion precheck did not confirm a safe current pose.')

        _transition(session, run, 'capturing', 'verified-capture', 35)
        _check_cancelled(session, run)
        capture = camera.capture(CaptureRequest(
            request_id=run.id, camera_id=request.camera_id, recipe_id=str(run.recipe_id),
            expected_position=request.expected_position, sensor_mode=request.sensor_mode,
            exposure_microseconds=request.exposure_microseconds, analog_gain=request.analog_gain,
        ))
        image = camera.inspection_image(
            capture.capture_id, expected_sha256=capture.sha256, expected_bytes=capture.byte_length,
        )
        relative_path = _store_artifact(artifact_root, image.content, image.sha256, image.media_type)
        blurred = _is_blurred(image.content)
        registered = _positions_match(capture.position, request.expected_position)
        run.input_artifact = {
            'sha256': image.sha256, 'byteLength': len(image.content), 'mediaType': image.media_type,
            'relativePath': relative_path, 'width': capture.width, 'height': capture.height,
            'capturedAt': capture.captured_at.isoformat(), 'position': capture.position.model_dump(mode='json', by_alias=True),
        }
        session.commit()

        _transition(session, run, 'executing', 'deterministic-reference', 70)
        _check_cancelled(session, run)
        context = ExecutionContext(
            run_id=run.id, node_id='deterministic-reference', deadline=_now() + timedelta(seconds=2),
            cancellation=CancellationToken(run.cancel_requested), resources={'cpuCores': 1, 'memoryMiB': 64},
        )
        context.checkpoint()
        algorithm_version = run.effective_versions['deterministic-reference']
        outcome = InspectionOrchestrator().run_reference_slice(InspectionInput(
            artifact_sha256=capture.sha256, observed_sha256=image.sha256, byte_length=len(image.content),
            is_blurred=blurred, is_registered=registered, motion_in_position=state.is_in_position,
            pose_observed_at=state.updated_at, pose_tolerance_seconds=POSE_TOLERANCE_SECONDS,
            reference_score=_reference_score(image.content),
        ), threshold=request.threshold, algorithm_version=algorithm_version)
        completed = _now()
        for sequence, node in enumerate(outcome.node_runs, start=1):
            session.add(InspectionNodeRun(
                run_id=run.id, sequence=sequence, node_id=node.node_id, node_version=algorithm_version,
                execution_target='local-cpu', status=node.status, parameters=node.parameters,
                inputs={'artifactSha256': image.sha256}, outputs=node.outputs,
                resources=context.resources, evidence_sha256=outcome.evidence_sha256,
                error_code=node.error_code, error_message=node.error_code,
                started_at=run.started_at or completed, completed_at=completed,
                duration_ms=max(0, int((time.monotonic() - started) * 1000)),
            ))
        if outcome.decision == 'FAULT':
            session.commit()
            return _fault(session, run, outcome.error_code or 'execution-fault', 'Inspection safety contract rejected input artifact.')

        recipe = session.get(Recipe, run.recipe_id)
        if recipe is None:
            raise InspectionRunError('Inspection recipe disappeared during execution.')
        result = InspectionResult(
            board_serial=run.board_serial, lot=run.lot, recipe_id=run.recipe_id,
            recipe_name=recipe.name, operator_id=run.operator_id, result=outcome.decision,
            defect_count=1 if outcome.decision == 'FAIL' else 0, score=outcome.score,
            cycle_time_ms=max(0, int((time.monotonic() - started) * 1000)),
            camera_config={
                'cameraId': request.camera_id, 'sensorMode': request.sensor_mode,
                'exposureMicroseconds': request.exposure_microseconds, 'analogGain': request.analog_gain,
            },
        )
        session.add(result)
        session.flush()
        if outcome.decision == 'FAIL':
            session.add(Defect(
                result_id=result.id, defect_type='reference-anomaly', severity='high',
                confidence=outcome.score, description='Deterministic PCB reference score exceeded threshold.',
            ))
        session.add(InspectionImage(
            result_id=result.id, image_type='original', relative_path=relative_path,
            file_size_bytes=len(image.content), width_px=capture.width, height_px=capture.height,
            sha256_hash=image.sha256, media_type=image.media_type, captured_at=capture.captured_at,
        ))
        run.result_id = result.id
        run.decision = outcome.decision
        run.evidence_sha256 = outcome.evidence_sha256
        _enqueue_integration_events(session, run, result.id)
        _transition(session, run, 'completed', 'completed', 100)
        return _load_run(session, run.id) or run
    except InspectionCancelled:
        _transition(session, run, 'cancelled', 'cancelled', run.progress_percent)
        return _load_run(session, run.id) or run
    except DeviceServiceError as error:
        session.refresh(run, attribute_names=['cancel_requested'])
        if run.cancel_requested:
            _transition(session, run, 'cancelled', 'cancelled', run.progress_percent)
            return _load_run(session, run.id) or run
        return _fault(session, run, 'runtime-error', str(error))
    except (InspectionRunError, OSError, ValueError) as error:
        return _fault(session, run, 'runtime-error', str(error))
    except Exception:
        LOGGER.exception('Inspection run %s failed unexpectedly.', run.id)
        return _fault(
            session,
            run,
            'internal-runtime-error',
            'Inspection execution failed unexpectedly. Review server diagnostics before retrying.',
        )


def replay_run(session: Session, run_id: str, artifact_root: Path) -> tuple[str, str, bool]:
    run = session.get(InspectionRun, run_id)
    if run is None or run.status != 'completed' or run.input_artifact is None:
        raise InspectionRunError('Only completed inspection runs can be replayed.')
    manifest = run.input_artifact
    artifact_path = artifact_root / manifest['relativePath']
    content = artifact_path.read_bytes()
    checksum = hashlib.sha256(content).hexdigest()
    if checksum != manifest['sha256'] or len(content) != manifest['byteLength']:
        raise InspectionRunError('Replay artifact checksum or byte length is invalid.')
    request = InspectionRunCreateRequest.model_validate(run.parameters)
    algorithm_version = run.effective_versions.get('deterministic-reference')
    if algorithm_version not in {'1.0.0', '2.0.0'}:
        raise InspectionRunError('Replay requires a supported immutable deterministic reference version.')
    outcome = InspectionOrchestrator().run_reference_slice(InspectionInput(
        artifact_sha256=manifest['sha256'], observed_sha256=checksum, byte_length=len(content),
        is_blurred=_is_blurred(content), is_registered=True, motion_in_position=True,
        pose_observed_at=_now(), pose_tolerance_seconds=POSE_TOLERANCE_SECONDS,
        reference_score=_reference_score(content),
    ), threshold=request.threshold, algorithm_version=algorithm_version)
    return outcome.decision, outcome.evidence_sha256, (
        outcome.decision == run.decision and outcome.evidence_sha256 == run.evidence_sha256
    )


def _enqueue_integration_events(session: Session, run: InspectionRun, result_id: int) -> None:
    policy = run.commissioning_snapshot.get('integrationPolicy', {})
    payload = {
        'schemaVersion': 1, 'runId': run.id, 'resultId': result_id,
        'stationId': run.station_id, 'workOrderId': run.work_order_id,
        'boardSerial': run.board_serial, 'lot': run.lot, 'decision': run.decision,
        'evidenceSha256': run.evidence_sha256,
    }
    for channel in ('plc', 'mes'):
        if policy.get(channel, {}).get('enabled') is True:
            session.add(IntegrationOutboxEvent(
                idempotency_key=f'{run.id}:{channel}:inspection-completed:v1',
                run_id=run.id, channel=channel, event_type='inspection-completed', payload=payload,
            ))