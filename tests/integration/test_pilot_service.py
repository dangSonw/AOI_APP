import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.database.session import SessionLocal
from app.models.pilot import CalibrationRecord, CommissioningActivationEvent, IntegrationOutboxEvent
from app.models.inspection_run import InspectionRun
from app.models.recipe import Recipe
from app.models.user import User
from app.schemas.inspection_run import InspectionRunCreateRequest
from app.schemas.pilot import CalibrationCreateRequest, CommissioningProfileCreateRequest
from app.services.inspection_runtime_service import InspectionRunError, create_run
from app.services.inspection_runtime_service import request_cancellation
from app.services.pilot_service import activate_profile, create_calibration, create_profile


def operator_and_recipe() -> tuple[int, int]:
    with SessionLocal() as session:
        operator = session.scalar(select(User.id).order_by(User.id))
        recipe = session.scalar(select(Recipe.id).where(Recipe.slug == 'rev-c-mainboard'))
        assert operator is not None and recipe is not None
        return operator, recipe


def calibration_request(
    path: Path, *, valid_until: datetime, reprojection_error: float = 0.2,
    station_id: str = 'station-pilot',
) -> CalibrationCreateRequest:
    content = path.read_bytes()
    return CalibrationCreateRequest(
        station_id=station_id, camera_id='top-camera', calibration_type='intrinsic',
        artifact_relative_path=path.name, artifact_sha256=hashlib.sha256(content).hexdigest(),
        valid_until=valid_until,
        metrics={'imageCount': 20, 'coveragePercent': 90, 'reprojectionErrorPixels': reprojection_error},
    )


def test_hardware_pilot_run_pins_valid_calibration_and_commissioning_lineage(tmp_path: Path) -> None:
    operator_id, recipe_id = operator_and_recipe()
    calibration_root = tmp_path / 'calibration'
    calibration_root.mkdir()
    artifact = calibration_root / 'calibration.json'
    artifact.write_text('{"cameraMatrix":[1,0,1]}', encoding='utf-8')
    with SessionLocal() as session:
        calibration = create_calibration(
            session, calibration_request(artifact, valid_until=datetime.now(timezone.utc) + timedelta(days=30)),
            operator_id, calibration_root,
        )
        profile = create_profile(session, CommissioningProfileCreateRequest(
            station_id='station-pilot', deployment_mode='hardware-pilot', calibration_id=calibration.id,
            signal_mapping={
                'ready': 'DO0', 'busy': 'DO1', 'trigger': 'DI0',
                'resultPass': 'DO2', 'resultFail': 'DO3', 'fault': 'DO4',
            },
            integration_policy={
                'plc': {'enabled': True},
                'mes': {'enabled': True, 'outagePolicy': 'queue', 'endpointReference': 'config://mes/pilot'},
            },
        ), operator_id)
        activate_profile(session, profile.id, operator_id, calibration_root, 'Pilot commissioning approved')
        activation = session.scalar(select(CommissioningActivationEvent).where(
            CommissioningActivationEvent.profile_id == profile.id,
        ).order_by(CommissioningActivationEvent.id.desc()))
        assert activation is not None
        assert activation.actor_id == operator_id
        assert activation.reason == 'Pilot commissioning approved'

        run = create_run(session, InspectionRunCreateRequest(
            board_serial=f'PILOT-{uuid4().hex}', lot='LOT-1', recipe_id=recipe_id,
            station_id='station-pilot', work_order_id='WO-1',
        ), operator_id, tmp_path / 'projects')
        try:
            assert run.commissioning_snapshot['profileId'] == profile.id
            assert run.commissioning_snapshot['calibration']['id'] == calibration.id
            assert run.commissioning_snapshot['calibration']['artifactSha256'] == calibration.artifact_sha256
        finally:
            request_cancellation(session, run.id)


def test_hardware_pilot_blocks_expired_or_failed_calibration(tmp_path: Path) -> None:
    operator_id, recipe_id = operator_and_recipe()
    calibration_root = tmp_path / 'calibration'
    calibration_root.mkdir()
    artifact = calibration_root / 'calibration.json'
    artifact.write_text('{}', encoding='utf-8')
    with SessionLocal() as session:
        calibration = create_calibration(
            session,
            calibration_request(
                artifact, valid_until=datetime.now(timezone.utc) - timedelta(seconds=1),
                reprojection_error=5, station_id='station-blocked',
            ),
            operator_id,
            calibration_root,
        )
        profile = create_profile(session, CommissioningProfileCreateRequest(
            station_id='station-blocked', deployment_mode='hardware-pilot', calibration_id=calibration.id,
            signal_mapping={}, integration_policy={},
        ), operator_id)

        with pytest.raises(ValueError, match='calibration'):
                activate_profile(session, profile.id, operator_id, calibration_root)
        with pytest.raises(InspectionRunError, match='commissioning'):
            create_run(session, InspectionRunCreateRequest(
                board_serial=f'BLOCK-{uuid4().hex}', recipe_id=recipe_id, station_id='station-blocked',
            ), operator_id, tmp_path / 'projects')


def test_calibration_artifact_checksum_is_verified_before_persistence(tmp_path: Path) -> None:
    operator_id, _ = operator_and_recipe()
    artifact = tmp_path / 'calibration.json'
    artifact.write_text('{}', encoding='utf-8')
    request = calibration_request(artifact, valid_until=datetime.now(timezone.utc) + timedelta(days=1))
    request = request.model_copy(update={'artifact_sha256': '0' * 64})

    with SessionLocal() as session, pytest.raises(ValueError, match='checksum'):
        create_calibration(session, request, operator_id, tmp_path)
    with SessionLocal() as session:
        assert session.scalar(select(CalibrationRecord).where(
            CalibrationRecord.artifact_sha256 == '0' * 64,
        )) is None


def test_tampered_active_calibration_blocks_new_run(tmp_path: Path) -> None:
    operator_id, recipe_id = operator_and_recipe()
    calibration_root = tmp_path / 'calibration'
    calibration_root.mkdir()
    artifact = calibration_root / 'tamper.json'
    artifact.write_text('{}', encoding='utf-8')
    station_id = f'station-{uuid4().hex}'
    with SessionLocal() as session:
        calibration = create_calibration(
            session,
            calibration_request(artifact, valid_until=datetime.now(timezone.utc) + timedelta(days=1)),
            operator_id,
            calibration_root,
        )
        calibration.station_id = station_id
        session.commit()
        profile = create_profile(session, CommissioningProfileCreateRequest(
            station_id=station_id, deployment_mode='hardware-pilot', calibration_id=calibration.id,
            signal_mapping={}, integration_policy={},
        ), operator_id)
        activate_profile(session, profile.id, operator_id, calibration_root)
        artifact.write_text('{"tampered":true}', encoding='utf-8')

        with pytest.raises(InspectionRunError, match='calibration evidence'):
            create_run(session, InspectionRunCreateRequest(
                board_serial=f'TAMPER-{uuid4().hex}', recipe_id=recipe_id, station_id=station_id,
            ), operator_id, tmp_path / 'projects')


def test_commissioning_rejects_cross_station_calibration() -> None:
    operator_id, _ = operator_and_recipe()
    with SessionLocal() as session:
        calibration = session.scalar(select(CalibrationRecord).order_by(CalibrationRecord.created_at.desc()))
        if calibration is None:
            pytest.skip('No calibration exists in integration database.')
        with pytest.raises(ValueError, match='same station'):
            create_profile(session, CommissioningProfileCreateRequest(
                station_id=f'other-{uuid4().hex}', deployment_mode='hardware-pilot',
                calibration_id=calibration.id, signal_mapping={}, integration_policy={},
            ), operator_id)


def test_integration_outbox_model_enforces_idempotent_run_channel_event() -> None:
    assert IntegrationOutboxEvent.__table__.c.idempotency_key.unique is True


def test_completed_pilot_result_enqueues_idempotent_plc_and_mes_events() -> None:
    from app.services.inspection_runtime_service import _enqueue_integration_events

    with SessionLocal() as session:
        run = session.scalar(select(InspectionRun).where(
            InspectionRun.commissioning_snapshot['integrationPolicy']['plc']['enabled'].as_boolean().is_(True),
        ).order_by(InspectionRun.created_at.desc()).limit(1))
        if run is None:
            pytest.skip('No pilot lineage run exists in integration database.')
        run.decision = 'PASS'
        run.evidence_sha256 = 'a' * 64
        _enqueue_integration_events(session, run, result_id=1)
        session.flush()
        events = list(session.scalars(select(IntegrationOutboxEvent).where(
            IntegrationOutboxEvent.run_id == run.id,
        ).order_by(IntegrationOutboxEvent.channel)))
        channels = [event.channel for event in events]
        schema_versions = [event.payload['schemaVersion'] for event in events]
        session.rollback()

        assert channels == ['mes', 'plc']
        assert schema_versions == [1, 1]