from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import struct
import zlib

import pytest
from sqlalchemy import func, select

from app.clients.camera_client import InspectionImage as VerifiedImage
from app.clients.device_client import DeviceServiceError
from app.database.session import SessionLocal
from app.models.inspection_result import InspectionResult
from app.models.inspection_run import InspectionReviewEvent, InspectionRun
from app.models.recipe import Recipe
from app.models.research import ModelAlias, ModelRegistryEntry, ModelVersion, ResearchArtifact, ResearchExperiment, ResearchRun
from app.models.user import User
from app.schemas.inspection_run import InspectionRunCreateRequest
from app.services.inspection_runtime_service import (
    _production_node_context,
    create_run,
    execute_run,
    get_preview_artifact,
    recover_interrupted_runs,
    replay_run,
    request_cancellation,
)
from app.services.inspection_service import submit_review
from core.devices.camera import CaptureRequest, CaptureResult
from core.devices.models import DeviceMode
from core.devices.motion import CommandResult, HomeRequest, MotionState, MotionStateName, Position
from core.nodes import NodeExecutionContext
from app.schemas.workflow import WorkflowSchema
from core.pipeline import create_default_workflow


def test_production_context_pins_alias_and_exposes_verified_artifact(tmp_path: Path) -> None:
    import hashlib
    from dataclasses import replace
    from app.services.research_service import ArtifactStore

    operator_id, _ = _operator_and_recipe()
    suffix = uuid4().hex
    model_name = f'production-svm-{suffix}'
    store = ArtifactStore(tmp_path / 'models')
    first_content = b'first-model'
    second_content = b'second-model'
    first_record = store.put_bytes(first_content, media_type='application/vnd.aoi.sklearn-pipeline+zip')
    second_record = store.put_bytes(second_content, media_type='application/vnd.aoi.sklearn-pipeline+zip')
    with SessionLocal() as session:
        experiment = ResearchExperiment(id=f'experiment-{suffix}', name=model_name, description='', created_by=operator_id)
        run = ResearchRun(
            id=f'run-{suffix}', experiment_id=experiment.id, status='completed', execution_target='local-cpu',
            code_revision='test', node_versions={}, environment={}, random_seeds={}, resources={},
            dataset_versions={}, parameters={}, metrics={}, output_artifacts={}, error=None, created_by=operator_id,
        )
        session.add_all([experiment, run]); session.flush()
        artifacts = [
            ResearchArtifact(run_id=run.id, name=name, sha256=record.sha256, media_type=record.media_type, byte_length=record.byte_length, storage_uri=record.storage_uri)
            for name, record in (('model-1', first_record), ('model-2', second_record))
        ]
        session.add_all(artifacts); session.flush()
        model = ModelRegistryEntry(name=model_name, description='', created_by=operator_id)
        session.add(model); session.flush()
        versions = [
            ModelVersion(model_id=model.id, version=index, run_id=run.id, artifact_id=artifact.id, validation_evidence={'passed': True}, created_by=operator_id)
            for index, artifact in enumerate(artifacts, 1)
        ]
        session.add_all(versions); session.flush()
        alias = ModelAlias(model_id=model.id, alias='champion', model_version_id=versions[0].id)
        session.add(alias); session.commit()

        workflow = create_default_workflow()
        first_node = workflow.nodes[0]
        portable = replace(workflow, nodes=(replace(first_node, parameters={**first_node.parameters, 'model': {
            'modelName': model_name, 'alias': 'champion',
        }}), *workflow.nodes[1:]))
        context = _production_node_context(
            session, WorkflowSchema.from_core(portable), is_cancelled=lambda: False,
        )
        alias.model_version_id = versions[1].id
        session.commit()

        assert context.models[model_name].model_version == 1
        assert context.models[model_name].artifact_sha256 == hashlib.sha256(first_content).hexdigest()
        assert context.read_artifact(model_name) == first_content
from simulator.camera.capture_service import create_test_pattern_png


class ReadyMotion:
    def state(self) -> MotionState:
        return MotionState(
            revision=1,
            state=MotionStateName.IDLE,
            is_homed=True,
            is_in_position=True,
            position=Position(x_millimeters=0, y_millimeters=0, z_millimeters=0),
            emergency_stop=False,
            door_closed=True,
            communication_connected=True,
            updated_at=datetime.now(timezone.utc),
        )


class StaleMotion(ReadyMotion):
    def state(self) -> MotionState:
        from datetime import timedelta
        state = super().state()
        return state.model_copy(update={'updated_at': state.updated_at - timedelta(seconds=120)})


class UnhomedSimulationMotion(ReadyMotion):
    def __init__(self) -> None:
        self.was_homed = False

    def state(self) -> MotionState:
        state = super().state()
        if self.was_homed:
            return state
        return state.model_copy(update={
            'revision': 0,
            'state': MotionStateName.NOT_HOMED,
            'is_homed': False,
            'is_in_position': False,
        })

    def health(self):
        return type('Health', (), {'mode': DeviceMode.SIMULATION})()

    def home(self, request: HomeRequest) -> CommandResult:
        self.was_homed = True
        return CommandResult(command_id=request.command_id, status='completed', state_revision=1)


class UnhomedHardwareMotion(UnhomedSimulationMotion):
    def health(self):
        return type('Health', (), {'mode': DeviceMode.HARDWARE})()

    def home(self, request: HomeRequest) -> CommandResult:
        raise AssertionError('Hardware motion must not be auto-homed by an uncommissioned run.')


class VerifiedCamera:
    def __init__(self) -> None:
        self.content = create_test_pattern_png()
        import hashlib
        self.sha256 = hashlib.sha256(self.content).hexdigest()

    def capture(self, request: CaptureRequest) -> CaptureResult:
        return CaptureResult(
            capture_id=request.request_id,
            request_id=request.request_id,
            status='ready',
            camera_id=request.camera_id,
            sensor_model='deterministic-test-camera',
            captured_at=datetime.now(timezone.utc),
            monotonic_timestamp_nanoseconds=1,
            width=2,
            height=2,
            pixel_format='rgb8',
            position=request.expected_position,
            exposure_microseconds=request.exposure_microseconds,
            analog_gain=request.analog_gain,
            media_type='image/png',
            byte_length=len(self.content),
            sha256=self.sha256,
            inspection_image_url=f'/captures/{request.request_id}/inspection-image',
        )

    def inspection_image(self, capture_id: str, **_: object) -> VerifiedImage:
        assert capture_id
        return VerifiedImage(self.content, 'image/png', self.sha256)


def _rgba_png() -> bytes:
    def chunk(chunk_type: bytes, payload: bytes) -> bytes:
        body = chunk_type + payload
        return struct.pack('>I', len(payload)) + body + struct.pack('>I', zlib.crc32(body) & 0xFFFFFFFF)

    width = height = 2
    raw_rows = b'\x00\x00\x00\x00\xff\xff\xff\xff\xff' + b'\x00\xff\x00\x00\xff\x00\xff\x00\xff'
    return (
        b'\x89PNG\r\n\x1a\n'
        + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
        + chunk(b'IDAT', zlib.compress(raw_rows))
        + chunk(b'IEND', b'')
    )


class RgbaVerifiedCamera(VerifiedCamera):
    def __init__(self) -> None:
        self.content = _rgba_png()
        import hashlib
        self.sha256 = hashlib.sha256(self.content).hexdigest()


class CancelledTimeoutCamera(VerifiedCamera):
    def __init__(self, session, run_id: str) -> None:
        super().__init__()
        self.session = session
        self.run_id = run_id

    def capture(self, request: CaptureRequest) -> CaptureResult:
        run = self.session.get(InspectionRun, self.run_id)
        assert run is not None
        run.cancel_requested = True
        self.session.commit()
        raise DeviceServiceError('The device adapter request timed out.', 504)


def _operator_and_recipe() -> tuple[int, int]:
    with SessionLocal() as session:
        operator_id = session.scalar(select(User.id).order_by(User.id))
        recipe_id = session.scalar(select(Recipe.id).where(Recipe.slug == 'rev-c-mainboard'))
        assert operator_id is not None and recipe_id is not None
        return operator_id, recipe_id


def test_persisted_run_completes_with_replayable_node_and_artifact_evidence(tmp_path: Path) -> None:
    operator_id, recipe_id = _operator_and_recipe()
    request = InspectionRunCreateRequest(
        board_serial=f'PCB-{uuid4().hex}', recipe_id=recipe_id, threshold=0.5,
    )
    with SessionLocal() as session:
        run = create_run(session, request, operator_id, tmp_path / 'projects')
        completed = execute_run(session, run.id, VerifiedCamera(), ReadyMotion(), tmp_path / 'captures')

        assert completed.status == 'completed'
        assert completed.decision in {'PASS', 'FAIL'}
        assert completed.result_id is not None
        assert completed.input_artifact is not None
        assert len(completed.workflow_sha256) == 64
        assert len(completed.evidence_sha256 or '') == 64
        assert len(completed.node_runs) == 11
        assert all(node.status == 'completed' for node in completed.node_runs)
        assert completed.node_runs[-1].node_id == completed.workflow_snapshot['executionOrder'][-1]
        assert completed.node_runs[-1].algorithm_id == 'image-output'
        assert all(node.visit_index >= 1 for node in completed.node_runs)
        assert completed.input_artifact['previewRelativePath'].endswith('.png')
        assert completed.input_artifact['previewArtifacts']
        assert completed.input_artifact['previewArtifacts'][completed.node_runs[-1].node_id]['sha256']
        preview = get_preview_artifact(session, run.id, tmp_path / 'captures')
        assert preview is not None
        assert preview[0].read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
        assert preview[1] == 'image/png'
        node_preview = get_preview_artifact(session, run.id, tmp_path / 'captures', completed.node_runs[-1].node_id)
        assert node_preview is not None
        assert node_preview[0].read_bytes().startswith(b'\x89PNG\r\n\x1a\n')

        decision, evidence, matches = replay_run(session, run.id, tmp_path / 'captures')
        assert decision == completed.decision
        assert evidence == completed.evidence_sha256
        assert matches is True


def test_persisted_run_accepts_rgba_png_camera_and_folder_sources(tmp_path: Path) -> None:
    operator_id, recipe_id = _operator_and_recipe()
    with SessionLocal() as session:
        run = create_run(session, InspectionRunCreateRequest(
            board_serial=f'RGBA-{uuid4().hex}', recipe_id=recipe_id, threshold=0.5,
        ), operator_id, tmp_path / 'projects')

        completed = execute_run(session, run.id, RgbaVerifiedCamera(), ReadyMotion(), tmp_path / 'captures')

        assert completed.status == 'completed'
        assert completed.input_artifact is not None
        assert completed.input_artifact['width'] == 2
        assert completed.input_artifact['height'] == 2
        decision, evidence, matches = replay_run(session, run.id, tmp_path / 'captures')
        assert decision == completed.decision
        assert evidence == completed.evidence_sha256
        assert matches is True


def test_uncommissioned_simulation_homes_before_capture_and_persists_preview(tmp_path: Path) -> None:
    operator_id, recipe_id = _operator_and_recipe()
    motion = UnhomedSimulationMotion()
    with SessionLocal() as session:
        run = create_run(session, InspectionRunCreateRequest(
            board_serial=f'PCB-{uuid4().hex}', recipe_id=recipe_id,
        ), operator_id, tmp_path / 'projects')

        completed = execute_run(session, run.id, VerifiedCamera(), motion, tmp_path / 'captures')

        assert motion.was_homed is True
        assert completed.status == 'completed'
        assert completed.input_artifact is not None
        assert get_preview_artifact(session, run.id, tmp_path / 'captures') is not None


def test_uncommissioned_run_does_not_auto_home_a_hardware_adapter(tmp_path: Path) -> None:
    operator_id, recipe_id = _operator_and_recipe()
    motion = UnhomedHardwareMotion()
    with SessionLocal() as session:
        run = create_run(session, InspectionRunCreateRequest(
            board_serial=f'PCB-{uuid4().hex}', recipe_id=recipe_id,
        ), operator_id, tmp_path / 'projects')

        faulted = execute_run(session, run.id, VerifiedCamera(), motion, tmp_path / 'captures')

        assert faulted.status == 'faulted'
        assert faulted.error_code == 'motion-not-in-position'
        assert faulted.input_artifact is None


def test_queued_cancel_and_restart_recovery_are_persisted_without_device_calls(tmp_path: Path) -> None:
    operator_id, recipe_id = _operator_and_recipe()
    with SessionLocal() as session:
        cancelled = create_run(session, InspectionRunCreateRequest(
            board_serial=f'PCB-{uuid4().hex}', recipe_id=recipe_id,
        ), operator_id, tmp_path)
        assert request_cancellation(session, cancelled.id).status == 'cancelled'

        interrupted = create_run(session, InspectionRunCreateRequest(
            board_serial=f'PCB-{uuid4().hex}', recipe_id=recipe_id,
        ), operator_id, tmp_path)
        interrupted.status = 'capturing'
        session.commit()
        assert recover_interrupted_runs(session) == 1
        session.refresh(interrupted)
        assert interrupted.status == 'faulted'
        assert interrupted.error_code == 'restart-during-physical-operation'


def test_stale_pose_faults_before_capture(tmp_path: Path) -> None:
    operator_id, recipe_id = _operator_and_recipe()
    with SessionLocal() as session:
        run = create_run(session, InspectionRunCreateRequest(
            board_serial=f'PCB-{uuid4().hex}', recipe_id=recipe_id,
        ), operator_id, tmp_path)
        faulted = execute_run(session, run.id, VerifiedCamera(), StaleMotion(), tmp_path)

        assert faulted.status == 'faulted'
        assert faulted.error_code == 'stale-pose'
        assert faulted.input_artifact is None


def test_cancel_intent_wins_when_blocking_adapter_returns_timeout(tmp_path: Path) -> None:
    operator_id, recipe_id = _operator_and_recipe()
    with SessionLocal() as session:
        run = create_run(session, InspectionRunCreateRequest(
            board_serial=f'PCB-{uuid4().hex}', recipe_id=recipe_id,
        ), operator_id, tmp_path)
        cancelled = execute_run(
            session, run.id, CancelledTimeoutCamera(session, run.id), ReadyMotion(), tmp_path,
        )

        assert cancelled.status == 'cancelled'
        assert cancelled.cancel_requested is True
        assert cancelled.result_id is None


def test_live_workflow_passes_refreshing_cancellation_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import inspection_runtime_service

    operator_id, recipe_id = _operator_and_recipe()
    received_contexts: list[NodeExecutionContext] = []
    with SessionLocal() as session:
        run = create_run(session, InspectionRunCreateRequest(
            board_serial=f'PCB-{uuid4().hex}', recipe_id=recipe_id,
        ), operator_id, tmp_path / 'projects')

        def cancelled_workflow(workflow, *, source_image, context, observer=None):
            received_contexts.append(context)
            run.cancel_requested = True
            session.commit()
            context.checkpoint()
            raise AssertionError('Cancellation checkpoint must stop workflow execution.')

        monkeypatch.setattr(inspection_runtime_service, 'execute_workflow', cancelled_workflow)

        cancelled = execute_run(
            session, run.id, VerifiedCamera(), ReadyMotion(), tmp_path / 'captures',
        )

        assert received_contexts and isinstance(received_contexts[0], NodeExecutionContext)
        assert cancelled.status == 'cancelled'
        assert cancelled.cancel_requested is True
        assert cancelled.result_id is None


def test_review_events_are_append_only_while_current_decision_remains_queryable() -> None:
    with SessionLocal() as session:
        result = session.scalar(select(InspectionResult).order_by(InspectionResult.id.desc()))
        operator_id = session.scalar(select(User.id).order_by(User.id))
        assert result is not None and operator_id is not None
        before = session.scalar(select(func.count(InspectionReviewEvent.id))) or 0

        submit_review(session, result.id, operator_id, 'PASS', 'First verification')
        submit_review(session, result.id, operator_id, 'FAIL', 'Second verification')

        after = session.scalar(select(func.count(InspectionReviewEvent.id))) or 0
        events = list(session.scalars(
            select(InspectionReviewEvent)
            .where(InspectionReviewEvent.result_id == result.id)
            .order_by(InspectionReviewEvent.id.desc())
            .limit(2),
        ))
        assert after == before + 2
        assert {event.reason for event in events} == {'First verification', 'Second verification'}
        session.refresh(result)
        assert result.review_decision == 'FAIL'