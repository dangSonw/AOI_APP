from pathlib import Path
from types import SimpleNamespace

import pytest

from app.database import bootstrap as _database_bootstrap  # noqa: F401
from app.services.research_service import ArtifactIntegrityError, ArtifactStore
from app.services.training_execution_service import (
    TrainingArtifactOutput, TrainingCancelled, TrainingExecutionContext, TrainingExecutionResult,
    TrainingOrchestrator, TrainingProgressError, execute_training_dispatch,
    persist_verified_training_artifact,
)
from core.training.contracts import TrainingJobStatus


def test_progress_is_monotonic_by_stage_and_units() -> None:
    persisted: list[dict] = []
    context = TrainingExecutionContext(lambda: False, persisted.append)

    context.checkpoint(TrainingJobStatus.PREPARING_DATASET, processed_units=1, total_units=2)
    context.checkpoint(TrainingJobStatus.PREPARING_DATASET, processed_units=2, total_units=2)
    context.checkpoint(TrainingJobStatus.VALIDATING, processed_units=0, total_units=1)

    assert [item['stage'] for item in persisted] == ['preparing-dataset', 'preparing-dataset', 'validating']
    with pytest.raises(TrainingProgressError, match='regress'):
        context.checkpoint(TrainingJobStatus.PREPARING_DATASET, processed_units=2, total_units=2)
    with pytest.raises(TrainingProgressError, match='regress'):
        context.checkpoint(TrainingJobStatus.VALIDATING, processed_units=0, total_units=1)


def test_safe_checkpoint_observes_cancellation_before_persisting_progress() -> None:
    persisted: list[dict] = []
    context = TrainingExecutionContext(lambda: True, persisted.append)

    with pytest.raises(TrainingCancelled):
        context.checkpoint(TrainingJobStatus.TRAINING, processed_units=1, total_units=10)
    assert persisted == []


def test_verified_artifact_rejects_size_checksum_and_length_before_db_add(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    session = SimpleNamespace(added=[], add=lambda value: session.added.append(value), flush=lambda: None)
    content = b'model-data'

    with pytest.raises(ArtifactIntegrityError, match='size limit'):
        persist_verified_training_artifact(session, store, 'run-1', 'model.bin', content, 'application/octet-stream', max_bytes=2)
    with pytest.raises(ArtifactIntegrityError, match='checksum'):
        persist_verified_training_artifact(session, store, 'run-1', 'model.bin', content, 'application/octet-stream', expected_sha256='0' * 64)
    with pytest.raises(ArtifactIntegrityError, match='length'):
        persist_verified_training_artifact(session, store, 'run-1', 'model.bin', content, 'application/octet-stream', expected_byte_length=999)
    assert session.added == []


def test_verified_artifact_creates_record_and_store_can_verify_it(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    session = SimpleNamespace(added=[], add=lambda value: session.added.append(value), flush=lambda: None)
    content = b'model-data'

    artifact = persist_verified_training_artifact(
        session, store, 'run-1', 'model.bin', content, 'application/octet-stream',
    )

    assert artifact.storage_uri not in artifact.name
    assert store.read_verified(SimpleNamespace(
        storage_uri=artifact.storage_uri, sha256=artifact.sha256, byte_length=artifact.byte_length,
    )) == content
    assert session.added == [artifact]


class OrchestratorSession:
    def __init__(self, run) -> None:
        self.run = run
        self.added = []
        self.commits = 0
        self.rollbacks = 0

    def get(self, model, identity): return self.run if identity == self.run.id else None
    def scalar(self, statement): return self.run
    def add(self, value): self.added.append(value)
    def flush(self): pass
    def commit(self): self.commits += 1
    def rollback(self):
        self.rollbacks += 1
        self.added.clear()
    def refresh(self, value): pass


def training_run(status: str = 'queued'):
    return SimpleNamespace(
        id='run-1', status=status, action_name='train', progress=None, metrics={},
        output_artifacts={}, error=None, completed_at=None,
    )


def test_orchestrator_completes_generic_action_with_verified_artifacts(tmp_path: Path) -> None:
    run = training_run()
    session = OrchestratorSession(run)
    dispatch = SimpleNamespace(run_id=run.id)

    def action(_, context):
        context.checkpoint(TrainingJobStatus.PREPARING_DATASET, processed_units=1, total_units=1)
        context.checkpoint(TrainingJobStatus.VALIDATING, processed_units=1, total_units=1)
        context.checkpoint(TrainingJobStatus.TRAINING, processed_units=1, total_units=1)
        context.checkpoint(TrainingJobStatus.EVALUATING, processed_units=1, total_units=1)
        context.checkpoint(TrainingJobStatus.PERSISTING_ARTIFACTS, processed_units=1, total_units=1)
        return TrainingExecutionResult(
            metrics={'accuracy': 1.0},
            artifacts=(TrainingArtifactOutput('model.bin', b'model', 'application/octet-stream'),),
        )

    completed = TrainingOrchestrator(ArtifactStore(tmp_path)).execute(session, dispatch, action)

    assert completed.status == 'completed'
    assert completed.metrics == {'accuracy': 1.0}
    assert completed.output_artifacts['model.bin']['sha256']
    assert len(session.added) == 1


def test_orchestrator_cancel_wins_before_terminal_commit_and_writes_no_artifact(tmp_path: Path) -> None:
    run = training_run()
    session = OrchestratorSession(run)

    def action(_, context):
        context.checkpoint(TrainingJobStatus.PREPARING_DATASET, processed_units=1, total_units=1)
        run.status = 'cancelling'
        return TrainingExecutionResult(
            metrics={}, artifacts=(TrainingArtifactOutput('model.bin', b'model', 'application/octet-stream'),),
        )

    cancelled = TrainingOrchestrator(ArtifactStore(tmp_path)).execute(
        session, SimpleNamespace(run_id=run.id), action,
    )

    assert cancelled.status == 'cancelled'
    assert session.added == []


def test_orchestrator_rolls_back_artifacts_and_persists_failure(tmp_path: Path) -> None:
    run = training_run()
    session = OrchestratorSession(run)

    def action(_, context):
        context.checkpoint(TrainingJobStatus.PREPARING_DATASET, processed_units=1, total_units=1)
        raise RuntimeError('sensitive internal failure')

    failed = TrainingOrchestrator(ArtifactStore(tmp_path)).execute(
        session, SimpleNamespace(run_id=run.id), action,
    )

    assert failed.status == 'failed'
    assert failed.error == 'Training action failed. Review server diagnostics before retrying.'
    assert failed.output_artifacts == {} and session.added == []
    assert session.rollbacks == 1


def test_orchestrator_rejects_terminal_reexecution(tmp_path: Path) -> None:
    session = OrchestratorSession(training_run('completed'))
    with pytest.raises(TrainingProgressError, match='terminal'):
        TrainingOrchestrator(ArtifactStore(tmp_path)).execute(
            session, SimpleNamespace(run_id='run-1'), lambda *_: TrainingExecutionResult({}, ()),
        )


def test_generic_dispatch_adapter_invokes_runtime_and_converts_typed_outputs() -> None:
    checkpoints = []
    context = TrainingExecutionContext(lambda: False, checkpoints.append)
    dispatch = SimpleNamespace(
        node_id='fake-trainer', action_name='train', datasets={'training-dataset': object()},
        parameters={'value': 2},
    )
    received_inputs = []
    runtime = SimpleNamespace(execute=lambda inputs, parameters: (
        received_inputs.append(inputs) or {
            'model': b'model', 'metrics': {'accuracy': 0.75},
            'report': {'schema': 'aoi.classification-report.v1', 'rows': []},
        }
    ))

    result = execute_training_dispatch(dispatch, context, runtime_loader=lambda _: runtime)

    assert result.metrics == {'accuracy': 0.75}
    assert [artifact.name for artifact in result.artifacts] == ['model', 'report']
    assert result.artifacts[0].content == b'model'
    assert result.artifacts[1].media_type == 'application/json'
    assert callable(received_inputs[0]['is-cancelled'])
    assert [item['stage'] for item in checkpoints] == [
        'preparing-dataset', 'validating', 'training', 'evaluating', 'persisting-artifacts',
    ]


def test_generic_dispatch_adapter_rejects_unknown_runtime_and_malformed_metrics() -> None:
    context = TrainingExecutionContext(lambda: False, lambda _: None)
    dispatch = SimpleNamespace(node_id='missing', action_name='train', datasets={}, parameters={})
    with pytest.raises(TrainingProgressError, match='runtime'):
        execute_training_dispatch(dispatch, context, runtime_loader=lambda _: None)
    runtime = SimpleNamespace(execute=lambda *_: {'metrics': {'accuracy': float('nan')}})
    with pytest.raises(TrainingProgressError, match='metrics'):
        execute_training_dispatch(dispatch, context, runtime_loader=lambda _: runtime)