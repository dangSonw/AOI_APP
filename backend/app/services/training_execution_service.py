from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.research import ResearchArtifact, ResearchRun
from app.services.research_service import ArtifactIntegrityError, ArtifactStore
from core.training.contracts import TERMINAL_TRAINING_STATUSES, TrainingJobStatus, TrainingProgress
from core.nodes.errors import NodeExecutionCancelled
from core.nodes.registry import get_node_runtime


ORPHANED_TRAINING_REASON = 'Training job was interrupted by a server restart without an active worker lease.'
ACTIVE_TRAINING_STATUSES = frozenset({
    TrainingJobStatus.PREPARING_DATASET,
    TrainingJobStatus.VALIDATING,
    TrainingJobStatus.TRAINING,
    TrainingJobStatus.EVALUATING,
    TrainingJobStatus.PERSISTING_ARTIFACTS,
    TrainingJobStatus.CANCELLING,
})
_PROGRESS_STAGE_ORDER = {
    TrainingJobStatus.QUEUED: 0,
    TrainingJobStatus.PREPARING_DATASET: 1,
    TrainingJobStatus.VALIDATING: 2,
    TrainingJobStatus.TRAINING: 3,
    TrainingJobStatus.EVALUATING: 4,
    TrainingJobStatus.PERSISTING_ARTIFACTS: 5,
    TrainingJobStatus.CANCELLING: 6,
}


class TrainingProgressError(ValueError):
    pass


class TrainingCancelled(RuntimeError):
    pass


ProgressWriter = Callable[[dict], None]
CancellationProbe = Callable[[], bool]


@dataclass(frozen=True, slots=True)
class TrainingArtifactOutput:
    name: str
    content: bytes
    media_type: str
    expected_sha256: str | None = None
    expected_byte_length: int | None = None


@dataclass(frozen=True, slots=True)
class TrainingExecutionResult:
    metrics: dict[str, float]
    artifacts: tuple[TrainingArtifactOutput, ...]


TrainingAction = Callable[[object, 'TrainingExecutionContext'], TrainingExecutionResult]
RuntimeLoader = Callable[[str], object | None]


class TrainingExecutionContext:
    def __init__(self, is_cancelled: CancellationProbe, persist_progress: ProgressWriter) -> None:
        self._is_cancelled = is_cancelled
        self._persist_progress = persist_progress
        self._last: TrainingProgress | None = None

    def is_cancelled(self) -> bool:
        return self._is_cancelled()

    def checkpoint(
        self,
        stage: TrainingJobStatus,
        *,
        processed_units: int = 0,
        total_units: int | None = None,
        message: str = '',
    ) -> None:
        if self._is_cancelled():
            raise TrainingCancelled('Training cancellation was observed at a safe checkpoint.')
        try:
            progress = TrainingProgress(
                stage=stage, processed_units=processed_units,
                total_units=total_units, message=message,
            )
        except ValueError as error:
            raise TrainingProgressError(str(error)) from error
        if stage not in _PROGRESS_STAGE_ORDER:
            raise TrainingProgressError(f'Training progress stage {stage} is unsupported.')
        if self._last is not None:
            previous_order = _PROGRESS_STAGE_ORDER[self._last.stage]
            next_order = _PROGRESS_STAGE_ORDER[progress.stage]
            if next_order < previous_order:
                raise TrainingProgressError('Training progress cannot regress to an earlier stage.')
            if next_order == previous_order and progress.processed_units <= self._last.processed_units:
                raise TrainingProgressError('Training progress units cannot regress or repeat.')
        self._persist_progress({
            'stage': progress.stage.value,
            'processedUnits': progress.processed_units,
            'totalUnits': progress.total_units,
            'fraction': progress.fraction,
            'message': progress.message,
        })
        self._last = progress


def execute_training_dispatch(
    dispatch: object,
    context: TrainingExecutionContext,
    *,
    runtime_loader: RuntimeLoader = get_node_runtime,
) -> TrainingExecutionResult:
    node_id = str(getattr(dispatch, 'node_id'))
    runtime = runtime_loader(node_id)
    if runtime is None or not callable(getattr(runtime, 'execute', None)):
        raise TrainingProgressError(f'Training runtime {node_id} is unavailable.')
    datasets = dict(getattr(dispatch, 'datasets'))
    parameters = dict(getattr(dispatch, 'parameters'))
    context.checkpoint(TrainingJobStatus.PREPARING_DATASET, processed_units=1, total_units=1)
    context.checkpoint(TrainingJobStatus.VALIDATING, processed_units=1, total_units=1)
    context.checkpoint(TrainingJobStatus.TRAINING, processed_units=1, total_units=1)
    try:
        outputs = runtime.execute({
            'action': getattr(dispatch, 'action_name'),
            'is-cancelled': context.is_cancelled,
            **datasets,
        }, parameters)
    except NodeExecutionCancelled as error:
        raise TrainingCancelled('Node observed training cancellation at a safe checkpoint.') from error
    context.checkpoint(TrainingJobStatus.EVALUATING, processed_units=1, total_units=1)
    if not isinstance(outputs, Mapping):
        raise TrainingProgressError('Training runtime outputs must be a mapping.')
    raw_metrics = outputs.get('metrics', {})
    if not isinstance(raw_metrics, Mapping) or any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
        for value in raw_metrics.values()
    ):
        raise TrainingProgressError('Training runtime metrics must be finite numbers.')
    artifacts: list[TrainingArtifactOutput] = []
    for name, value in sorted(outputs.items()):
        if name == 'metrics':
            continue
        if isinstance(value, bytes):
            content, media_type = value, 'application/octet-stream'
        else:
            try:
                content = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf-8')
            except (TypeError, ValueError) as error:
                raise TrainingProgressError(f'Training artifact {name} is not JSON serializable.') from error
            media_type = 'application/json'
        artifacts.append(TrainingArtifactOutput(str(name), content, media_type))
    context.checkpoint(TrainingJobStatus.PERSISTING_ARTIFACTS, processed_units=1, total_units=1)
    return TrainingExecutionResult(
        metrics={str(key): float(value) for key, value in raw_metrics.items()},
        artifacts=tuple(artifacts),
    )


class TrainingOrchestrator:
    def __init__(self, artifact_store: ArtifactStore) -> None:
        self._artifact_store = artifact_store

    @staticmethod
    def _locked_run(session: Session, run_id: str) -> ResearchRun | None:
        try:
            return session.scalar(
                select(ResearchRun).where(ResearchRun.id == run_id).with_for_update(),
            )
        except (AttributeError, TypeError):
            return session.get(ResearchRun, run_id)

    def execute(
        self,
        session: Session,
        dispatch: object,
        action: TrainingAction,
    ) -> ResearchRun:
        run_id = str(getattr(dispatch, 'run_id'))
        run = session.get(ResearchRun, run_id)
        if run is None:
            raise TrainingProgressError('Training run does not exist.')
        current = TrainingJobStatus(run.status)
        if current in TERMINAL_TRAINING_STATUSES:
            raise TrainingProgressError(f'Training run status {current} is terminal.')
        if current is not TrainingJobStatus.QUEUED:
            raise TrainingProgressError('Training run must be queued before execution starts.')

        def is_cancelled() -> bool:
            return run.status in {TrainingJobStatus.CANCELLING.value, TrainingJobStatus.CANCELLED.value}

        def persist_progress(progress: dict) -> None:
            locked = self._locked_run(session, run_id) or run
            if locked.status in {TrainingJobStatus.CANCELLING.value, TrainingJobStatus.CANCELLED.value}:
                raise TrainingCancelled('Training cancellation won before progress persistence.')
            locked.status = progress['stage']
            locked.progress = progress
            session.commit()

        context = TrainingExecutionContext(is_cancelled, persist_progress)
        try:
            result = action(dispatch, context)
            locked = self._locked_run(session, run_id) or run
            if locked.status in {TrainingJobStatus.CANCELLING.value, TrainingJobStatus.CANCELLED.value}:
                locked.status = TrainingJobStatus.CANCELLED.value
                locked.completed_at = datetime.now(timezone.utc)
                session.commit()
                return locked
            if locked.status != TrainingJobStatus.PERSISTING_ARTIFACTS.value:
                raise TrainingProgressError('Training action must reach persisting-artifacts before completion.')

            artifacts: dict[str, dict[str, object]] = {}
            for output in result.artifacts:
                artifact = persist_verified_training_artifact(
                    session, self._artifact_store, run_id, output.name, output.content,
                    output.media_type, expected_sha256=output.expected_sha256,
                    expected_byte_length=output.expected_byte_length,
                )
                artifacts[output.name] = {
                    'sha256': artifact.sha256,
                    'mediaType': artifact.media_type,
                    'byteLength': artifact.byte_length,
                }
            if is_cancelled():
                session.rollback()
                run = session.get(ResearchRun, run_id) or run
                run.status = TrainingJobStatus.CANCELLED.value
                run.completed_at = datetime.now(timezone.utc)
                session.commit()
                return run
            locked.metrics = dict(result.metrics)
            locked.output_artifacts = artifacts
            locked.status = TrainingJobStatus.COMPLETED.value
            locked.completed_at = datetime.now(timezone.utc)
            session.commit()
            return locked
        except TrainingCancelled:
            session.rollback()
            run = session.get(ResearchRun, run_id) or run
            run.status = TrainingJobStatus.CANCELLED.value
            run.completed_at = datetime.now(timezone.utc)
            session.commit()
            return run
        except Exception:
            session.rollback()
            run = session.get(ResearchRun, run_id) or run
            run.status = TrainingJobStatus.FAILED.value
            run.error = 'Training action failed. Review server diagnostics before retrying.'
            run.output_artifacts = {}
            run.completed_at = datetime.now(timezone.utc)
            session.commit()
            return run


def persist_verified_training_artifact(
    session: Session,
    store: ArtifactStore,
    run_id: str,
    name: str,
    content: bytes,
    media_type: str,
    *,
    expected_sha256: str | None = None,
    expected_byte_length: int | None = None,
    max_bytes: int = 512 * 1024 * 1024,
) -> ResearchArtifact:
    if not name or len(name) > 200 or '/' in name or '\\' in name or '\x00' in name:
        raise ArtifactIntegrityError('Training artifact name is invalid.')
    if not media_type or len(media_type) > 200:
        raise ArtifactIntegrityError('Training artifact media type is invalid.')
    if len(content) > max_bytes:
        raise ArtifactIntegrityError(f'Training artifact exceeds the {max_bytes} byte size limit.')
    digest = hashlib.sha256(content).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise ArtifactIntegrityError('Training artifact checksum does not match the expected SHA-256.')
    if expected_byte_length is not None and len(content) != expected_byte_length:
        raise ArtifactIntegrityError('Training artifact length does not match the expected byte length.')

    stored = store.put_bytes(content, media_type=media_type)
    store.read_verified(stored)
    artifact = ResearchArtifact(
        run_id=run_id, name=name, sha256=stored.sha256, media_type=stored.media_type,
        byte_length=stored.byte_length, storage_uri=stored.storage_uri,
    )
    session.add(artifact)
    session.flush()
    return artifact


def recover_orphaned_training_jobs(session: Session) -> int:
    candidates = session.scalars(select(ResearchRun).where(
        ResearchRun.action_name != 'legacy-run',
        ResearchRun.status.in_(tuple(status.value for status in ACTIVE_TRAINING_STATUSES)),
    ))
    recovered = 0
    for run in candidates:
        try:
            status = TrainingJobStatus(run.status)
        except ValueError:
            continue
        if status not in ACTIVE_TRAINING_STATUSES or run.action_name == 'legacy-run':
            continue
        run.status = TrainingJobStatus.FAILED.value
        run.error = ORPHANED_TRAINING_REASON
        run.completed_at = datetime.now(timezone.utc)
        recovered += 1
    if recovered:
        session.commit()
    return recovered