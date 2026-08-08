from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import func, select

from app.clients.camera_client import InspectionImage as VerifiedImage
from app.clients.device_client import DeviceServiceError
from app.database.session import SessionLocal
from app.models.inspection_result import InspectionResult
from app.models.inspection_run import InspectionReviewEvent, InspectionRun
from app.models.recipe import Recipe
from app.models.user import User
from app.schemas.inspection_run import InspectionRunCreateRequest
from app.services.inspection_runtime_service import (
    create_run,
    execute_run,
    recover_interrupted_runs,
    replay_run,
    request_cancellation,
)
from app.services.inspection_service import submit_review
from core.devices.camera import CaptureRequest, CaptureResult
from core.devices.motion import MotionState, MotionStateName, Position
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
        assert len(completed.node_runs) == 1
        assert completed.node_runs[0].status == 'completed'

        decision, evidence, matches = replay_run(session, run.id, tmp_path / 'captures')
        assert decision == completed.decision
        assert evidence == completed.evidence_sha256
        assert matches is True


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