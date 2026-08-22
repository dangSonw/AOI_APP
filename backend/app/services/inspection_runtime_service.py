from __future__ import annotations

import hashlib
import json
import logging
import os
import struct
import time
import zlib
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.research import ModelAlias, ModelRegistryEntry, ModelVersion, ResearchArtifact

from app.clients.camera_client import CameraClient
from app.clients.device_client import DeviceServiceError
from app.clients.motion_client import MotionClient
from app.config.settings import get_settings
from app.models.defect import Defect
from app.models.inspection_image import InspectionImage
from app.models.inspection_result import InspectionResult
from app.models.inspection_run import InspectionNodeRun, InspectionRun
from app.models.pilot import CommissioningProfile, IntegrationOutboxEvent
from app.models.recipe import Recipe
from app.schemas.inspection_run import InspectionRunCreateRequest
from app.schemas.workflow import WorkflowSchema
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
from core.devices.models import DeviceMode
from core.devices.motion import HomeRequest
from core.nodes import ModelBinding, NodeExecutionCancelled, NodeExecutionContext, get_node_manifest_registry
from core.pipeline import WorkflowExecutionRecord, execute_workflow


TERMINAL_STATUSES = {'completed', 'faulted', 'cancelled'}
ACTIVE_STATUSES = {'queued', 'precheck', 'capturing', 'executing'}
POSE_TOLERANCE_SECONDS = 60.0
POSITION_TOLERANCE_MILLIMETERS = 0.01
INSPECTION_RUN_ADVISORY_LOCK = 0x414F4952554E
LOGGER = logging.getLogger(__name__)


class InspectionRunError(RuntimeError):
    pass


def _append_workflow_log_line(run_id: str, record: WorkflowExecutionRecord) -> None:
    event = record.log_event or {}
    log_path = get_settings().workflow_log_path
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = _now().isoformat(timespec='milliseconds')
        line = (
            f'{timestamp} [{str(event.get("level", "info")).upper()}] '
            f'run={run_id} node={record.node_instance_id} algorithm={record.algorithm_id}: '
            f'{str(event.get("message", ""))}\n'
        )
        with log_path.open('a', encoding='utf-8') as log_file:
            log_file.write(line)
            log_file.flush()
            os.fsync(log_file.fileno())
    except OSError:
        LOGGER.exception('The workflow log file could not be written.')


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
    if not saw_end or width <= 0 or height <= 0 or bit_depth != 8 or color_type not in {0, 2, 4, 6}:
        raise InspectionRunError('Captured artifact is corrupt or unsupported.')
    source_channels = {0: 1, 2: 3, 4: 2, 6: 4}[color_type]
    try:
        raw = zlib.decompress(bytes(compressed))
    except zlib.error as error:
        raise InspectionRunError('Captured artifact is corrupt.') from error
    stride = width * source_channels
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
            left = scanline[index - source_channels] if index >= source_channels else 0
            above = prior[index]
            upper_left = prior[index - source_channels] if index >= source_channels else 0
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
    if color_type in {0, 2}:
        return width, height, b''.join(rows)
    channels_without_alpha = source_channels - 1
    return width, height, b''.join(
        bytes(channel for index, channel in enumerate(scanline) if index % source_channels < channels_without_alpha)
        for scanline in rows
    )


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


def _decode_image(content: bytes) -> np.ndarray:
    image = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None or image.size == 0:
        raise InspectionRunError('Captured artifact cannot be decoded by OpenCV.')
    return image


def _encode_preview(image: np.ndarray) -> bytes:
    preview = image
    if preview.dtype != np.uint8:
        preview = cv2.normalize(preview, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    encoded, payload = cv2.imencode('.png', preview)
    if not encoded:
        raise InspectionRunError('Workflow preview could not be encoded.')
    return payload.tobytes()


def _workflow_evidence_hash(
    workflow_sha256: str,
    artifact_sha256: str,
    preview_sha256: str,
    decision: str,
    score: float | None,
    records: tuple,
) -> str:
    return _canonical_sha256({
        'workflowSha256': workflow_sha256,
        'artifactSha256': artifact_sha256,
        'previewSha256': preview_sha256,
        'decision': decision,
        'score': score,
        'nodes': [
            {
                'nodeInstanceId': record.node_instance_id,
                'algorithmId': record.algorithm_id,
                'status': record.status,
                'parameters': record.parameters,
                'inputs': record.inputs,
                'outputs': record.outputs,
                'errorCode': record.error_code,
                **({
                    'activationId': record.activation_id,
                    'activationSequence': record.activation_sequence,
                    'visitIndex': record.visit_index,
                } if record.activation_id is not None else {}),
            }
            for record in records
        ],
    })


def _fault(session: Session, run: InspectionRun, code: str, message: str) -> InspectionRun:
    run.error_code = code
    run.error_message = message[:500]
    run.decision = 'FAULT'
    _transition(session, run, 'faulted', 'faulted', run.progress_percent)
    return _load_run(session, run.id) or run


def _model_references(value: object) -> tuple[dict[str, object], ...]:
    if isinstance(value, dict):
        if set(value) in ({'modelName', 'alias'}, {'modelName', 'modelVersion', 'artifactSha256'}):
            return (value,)
        return tuple(reference for item in value.values() for reference in _model_references(item))
    if isinstance(value, list):
        return tuple(reference for item in value for reference in _model_references(item))
    return ()


def _production_node_context(
    session: Session,
    workflow: WorkflowSchema,
    *,
    is_cancelled: Callable[[], bool],
) -> NodeExecutionContext:
    bindings: dict[str, ModelBinding] = {}
    for node in workflow.nodes:
        for reference in _model_references(node.parameters):
            model_name = str(reference['modelName'])
            model = session.scalar(select(ModelRegistryEntry).where(ModelRegistryEntry.name == model_name))
            if model is None:
                raise InspectionRunError(f'Production model {model_name} does not exist.')
            if 'alias' in reference:
                assignment = session.scalar(select(ModelAlias).where(
                    ModelAlias.model_id == model.id, ModelAlias.alias == str(reference['alias']),
                ))
                if assignment is None:
                    raise InspectionRunError(f'Production model {model_name} alias is not assigned.')
                version = session.get(ModelVersion, assignment.model_version_id)
            else:
                version = session.scalar(select(ModelVersion).where(
                    ModelVersion.model_id == model.id, ModelVersion.version == int(reference['modelVersion']),
                ))
            if version is None:
                raise InspectionRunError(f'Production model {model_name} version does not exist.')
            artifact = session.get(ResearchArtifact, version.artifact_id)
            if artifact is None:
                raise InspectionRunError(f'Production model {model_name} artifact is missing.')
            if 'artifactSha256' in reference and str(reference['artifactSha256']) != artifact.sha256:
                raise InspectionRunError(f'Production model {model_name} artifact checksum does not match.')
            if not artifact.storage_uri or len(artifact.sha256) != 64 or artifact.byte_length < 0:
                raise InspectionRunError(f'Production model {model_name} artifact integrity metadata is invalid.')
            artifact_path = Path(artifact.storage_uri).resolve()
            try:
                artifact_content = artifact_path.read_bytes()
            except OSError as error:
                raise InspectionRunError(f'Production model {model_name} artifact is unavailable.') from error
            if len(artifact_content) != artifact.byte_length or hashlib.sha256(artifact_content).hexdigest() != artifact.sha256:
                raise InspectionRunError(f'Production model {model_name} artifact integrity verification failed.')
            binding = ModelBinding(model.name, version.version, artifact.sha256)
            previous = bindings.get(model_name)
            if previous is not None and previous != binding:
                raise InspectionRunError(f'Production model {model_name} has conflicting immutable bindings.')
            bindings[model_name] = binding
    return NodeExecutionContext(models=bindings, is_cancelled=is_cancelled)


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
        if not state.is_homed and run.commissioning_snapshot.get('deploymentMode') == 'simulation-uncommissioned':
            if motion.health().mode == DeviceMode.SIMULATION:
                motion.home(HomeRequest(command_id=f'{run.id}-auto-home'))
                state = motion.state()
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

        _transition(session, run, 'executing', 'workflow-execution', 70)
        _check_cancelled(session, run)
        context = ExecutionContext(
            run_id=run.id, node_id='workflow-execution', deadline=_now() + timedelta(seconds=30),
            cancellation=CancellationToken(run.cancel_requested), resources={'cpuCores': 1, 'memoryMiB': 512},
        )
        context.checkpoint()
        precheck = InspectionOrchestrator().run_reference_slice(InspectionInput(
            artifact_sha256=capture.sha256, observed_sha256=image.sha256, byte_length=len(image.content),
            is_blurred=blurred, is_registered=registered, motion_in_position=state.is_in_position,
            pose_observed_at=state.updated_at, pose_tolerance_seconds=POSE_TOLERANCE_SECONDS,
            reference_score=_reference_score(image.content),
        ), threshold=request.threshold, algorithm_version='2.0.0')
        if precheck.decision == 'FAULT':
            return _fault(session, run, precheck.error_code or 'execution-fault', 'Inspection safety contract rejected input artifact.')

        workflow = WorkflowSchema.model_validate(run.workflow_snapshot).to_core()
        def workflow_is_cancelled() -> bool:
            session.refresh(run, attribute_names=['cancel_requested'])
            return bool(run.cancel_requested)

        is_production = run.commissioning_snapshot.get('deploymentMode') == 'production'
        node_context = (
            _production_node_context(session, workflow, is_cancelled=workflow_is_cancelled)
            if is_production
            else NodeExecutionContext(is_cancelled=workflow_is_cancelled)
        )
        manifests = get_node_manifest_registry()
        active_node_runs: dict[int, InspectionNodeRun] = {}

        def observe_node(record: WorkflowExecutionRecord) -> None:
            sequence = record.activation_sequence or len(active_node_runs) + 1
            if record.status == 'running' or sequence not in active_node_runs:
                manifest = manifests[record.algorithm_id]
                node_run = InspectionNodeRun(
                    run_id=run.id, sequence=sequence, node_id=record.node_instance_id,
                    algorithm_id=record.algorithm_id, visit_index=record.visit_index,
                    node_version=run.effective_versions[record.algorithm_id],
                    execution_target=manifest.execution_target, status=record.status,
                    parameters=record.parameters, inputs=record.inputs, outputs=record.outputs,
                    resources=dict(manifest.resource_hints), started_at=_now(),
                )
                session.add(node_run)
                session.commit()
                active_node_runs[sequence] = node_run
                if record.status == 'running':
                    return

            node_run = active_node_runs[sequence]
            node_run.status = record.status
            node_run.outputs = record.outputs
            node_run.error_code = record.error_code
            node_run.error_message = record.error_message
            node_run.completed_at = _now()
            node_run.duration_ms = record.duration_ms
            node_run.log_event = record.log_event
            node_run.evidence_sha256 = _canonical_sha256({
                'workflowSha256': run.workflow_sha256, 'artifactSha256': image.sha256,
                'nodeInstanceId': record.node_instance_id, 'algorithmId': record.algorithm_id,
                'parameters': record.parameters, 'inputs': record.inputs, 'outputs': record.outputs,
                'status': record.status, 'errorCode': record.error_code,
                'activationId': record.activation_id,
                'activationSequence': record.activation_sequence,
                'visitIndex': record.visit_index,
                'logEvent': record.log_event,
            })
            if record.log_event and record.log_event.get('destination') == 'file':
                _append_workflow_log_line(run.id, record)
            session.commit()

        execution_options = {'production': True} if is_production else {}
        workflow_result = execute_workflow(
            workflow, source_image=_decode_image(image.content), context=node_context,
            observer=observe_node, **execution_options,
        )
        faulted_record = next((record for record in workflow_result.records if record.status == 'faulted'), None)
        cancelled_record = next((record for record in workflow_result.records if record.status == 'cancelled'), None)
        if faulted_record is not None:
            session.commit()
            return _fault(
                session, run, faulted_record.error_code or 'node-execution-error',
                faulted_record.error_message or f'Workflow node {faulted_record.algorithm_id} faulted.',
            )
        if cancelled_record is not None:
            _transition(session, run, 'cancelled', 'cancelled', run.progress_percent)
            return _load_run(session, run.id) or run

        preview_image = workflow_result.final_image
        if preview_image is None:
            raise InspectionRunError('Workflow did not produce a preview image.')
        preview_content = _encode_preview(preview_image)
        preview_sha256 = hashlib.sha256(preview_content).hexdigest()
        preview_relative_path = _store_artifact(artifact_root, preview_content, preview_sha256, 'image/png')
        preview_artifacts: dict[str, dict[str, object]] = {}
        for node_id, node_image in workflow_result.preview_images.items():
            node_content = _encode_preview(node_image)
            node_sha256 = hashlib.sha256(node_content).hexdigest()
            node_relative_path = _store_artifact(artifact_root, node_content, node_sha256, 'image/png')
            preview_artifacts[node_id] = {
                'relativePath': node_relative_path,
                'sha256': node_sha256,
                'mediaType': 'image/png',
                'width': int(node_image.shape[1]),
                'height': int(node_image.shape[0]),
            }
        decision = workflow_result.decision or ('FAIL' if (workflow_result.score or 0.0) >= request.threshold else 'PASS')
        score = workflow_result.score
        evidence_sha256 = _workflow_evidence_hash(
            run.workflow_sha256, image.sha256, preview_sha256, decision, score, workflow_result.records,
        )
        run.input_artifact = {
            **run.input_artifact,
            'previewRelativePath': preview_relative_path,
            'previewSha256': preview_sha256,
            'previewMediaType': 'image/png',
            'previewWidth': int(preview_image.shape[1]),
            'previewHeight': int(preview_image.shape[0]),
            'previewArtifacts': preview_artifacts,
        }

        recipe = session.get(Recipe, run.recipe_id)
        if recipe is None:
            raise InspectionRunError('Inspection recipe disappeared during execution.')
        result = InspectionResult(
            board_serial=run.board_serial, lot=run.lot, recipe_id=run.recipe_id,
            recipe_name=recipe.name, operator_id=run.operator_id, result=decision,
            defect_count=1 if decision == 'FAIL' else 0, score=score,
            cycle_time_ms=max(0, int((time.monotonic() - started) * 1000)),
            camera_config={
                'cameraId': request.camera_id, 'sensorMode': request.sensor_mode,
                'exposureMicroseconds': request.exposure_microseconds, 'analogGain': request.analog_gain,
            },
        )
        session.add(result)
        session.flush()
        if decision == 'FAIL':
            session.add(Defect(
                result_id=result.id, defect_type='reference-anomaly', severity='high',
                confidence=score, description='Workflow score exceeded the configured threshold.',
            ))
        session.add(InspectionImage(
            result_id=result.id, image_type='original', relative_path=relative_path,
            file_size_bytes=len(image.content), width_px=capture.width, height_px=capture.height,
            sha256_hash=image.sha256, media_type=image.media_type, captured_at=capture.captured_at,
        ))
        session.add(InspectionImage(
            result_id=result.id, image_type='workflow-preview', relative_path=preview_relative_path,
            file_size_bytes=len(preview_content), width_px=int(preview_image.shape[1]),
            height_px=int(preview_image.shape[0]), sha256_hash=preview_sha256,
            media_type='image/png', captured_at=capture.captured_at,
        ))
        run.result_id = result.id
        run.decision = decision
        run.evidence_sha256 = evidence_sha256
        _enqueue_integration_events(session, run, result.id)
        _transition(session, run, 'completed', 'completed', 100)
        return _load_run(session, run.id) or run
    except (InspectionCancelled, NodeExecutionCancelled):
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
    if algorithm_version in {'1.0.0', '2.0.0'}:
        outcome = InspectionOrchestrator().run_reference_slice(InspectionInput(
            artifact_sha256=manifest['sha256'], observed_sha256=checksum, byte_length=len(content),
            is_blurred=_is_blurred(content), is_registered=True, motion_in_position=True,
            pose_observed_at=_now(), pose_tolerance_seconds=POSE_TOLERANCE_SECONDS,
            reference_score=_reference_score(content),
        ), threshold=request.threshold, algorithm_version=algorithm_version)
        return outcome.decision, outcome.evidence_sha256, (
            outcome.decision == run.decision and outcome.evidence_sha256 == run.evidence_sha256
        )

    workflow = WorkflowSchema.model_validate(run.workflow_snapshot).to_core()
    current_versions = get_node_manifest_registry()
    for node in workflow.nodes:
        pinned = run.effective_versions.get(node.algorithm_id)
        current = current_versions.get(node.algorithm_id)
        if current is None or pinned != current.package_version:
            raise InspectionRunError(f'Replay requires immutable node version {node.algorithm_id}@{pinned}.')
    workflow_result = execute_workflow(workflow, source_image=_decode_image(content))
    if any(record.status == 'faulted' for record in workflow_result.records) or workflow_result.final_image is None:
        raise InspectionRunError('Replay workflow did not complete successfully.')
    preview_content = _encode_preview(workflow_result.final_image)
    preview_sha256 = hashlib.sha256(preview_content).hexdigest()
    decision = workflow_result.decision or ('FAIL' if (workflow_result.score or 0.0) >= request.threshold else 'PASS')
    evidence_sha256 = _workflow_evidence_hash(
        run.workflow_sha256, checksum, preview_sha256, decision,
        workflow_result.score, workflow_result.records,
    )
    return decision, evidence_sha256, decision == run.decision and evidence_sha256 == run.evidence_sha256


def get_preview_artifact(
    session: Session,
    run_id: str,
    artifact_root: Path,
    node_id: str | None = None,
) -> tuple[Path, str] | None:
    run = session.get(InspectionRun, run_id)
    manifest = run.input_artifact if run is not None else None
    if not isinstance(manifest, dict):
        return None
    node_manifest = manifest.get('previewArtifacts', {}).get(node_id) if node_id else None
    selected = node_manifest if isinstance(node_manifest, dict) else manifest
    if 'relativePath' in selected:
        relative_path = selected.get('relativePath')
        expected_sha256 = selected.get('sha256')
        media_type = selected.get('mediaType', 'image/png')
    elif 'previewRelativePath' in selected:
        relative_path = selected.get('previewRelativePath')
        expected_sha256 = selected.get('previewSha256')
        media_type = selected.get('previewMediaType', 'image/png')
    else:
        return None
    root = artifact_root.resolve()
    path = (root / str(relative_path)).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise InspectionRunError('Workflow preview artifact path is invalid.')
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha256:
        raise InspectionRunError('Workflow preview artifact checksum is invalid.')
    return path, str(media_type)


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