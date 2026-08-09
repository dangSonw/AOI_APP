import hashlib
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.pilot import CalibrationRecord, CommissioningActivationEvent, CommissioningProfile
from app.schemas.pilot import CalibrationCreateRequest, CommissioningProfileCreateRequest


COMMISSIONING_ADVISORY_LOCK_NAMESPACE = 0x434F4D4D


def _station_lock(session: Session, station_id: str) -> None:
    session.execute(select(func.pg_advisory_xact_lock(
        COMMISSIONING_ADVISORY_LOCK_NAMESPACE,
        int(hashlib.sha256(station_id.encode()).hexdigest()[:8], 16) - 0x80000000,
    )))


def _verified_calibration(calibration: CalibrationRecord | None, artifact_root: Path) -> CalibrationRecord | None:
    if calibration is None:
        return None
    path = (artifact_root / calibration.artifact_relative_path).resolve()
    if (
        not path.is_relative_to(artifact_root.resolve()) or not path.is_file()
        or hashlib.sha256(path.read_bytes()).hexdigest() != calibration.artifact_sha256
    ):
        raise ValueError('Calibration artifact checksum is invalid.')
    return calibration


def create_calibration(
    session: Session, request: CalibrationCreateRequest, actor_id: int, artifact_root: Path,
) -> CalibrationRecord:
    path = (artifact_root / request.artifact_relative_path).resolve()
    if not path.is_relative_to(artifact_root.resolve()) or not path.is_file():
        raise ValueError('Calibration artifact does not exist inside approved storage.')
    if hashlib.sha256(path.read_bytes()).hexdigest() != request.artifact_sha256:
        raise ValueError('Calibration artifact checksum is invalid.')
    metrics = request.metrics
    valid = (
        metrics.image_count >= 10 and metrics.coverage_percent >= 70
        and metrics.reprojection_error_pixels <= 1
        and request.valid_until > datetime.now(timezone.utc)
    )
    record = CalibrationRecord(
        id=f'cal-{uuid4().hex}', station_id=request.station_id, camera_id=request.camera_id,
        calibration_type=request.calibration_type, artifact_relative_path=request.artifact_relative_path,
        artifact_sha256=request.artifact_sha256, metrics=metrics.model_dump(mode='json', by_alias=True),
        status='valid' if valid else 'failed', valid_until=request.valid_until, created_by=actor_id,
    )
    session.add(record)
    session.commit()
    return record


def create_profile(
    session: Session, request: CommissioningProfileCreateRequest, actor_id: int,
) -> CommissioningProfile:
    _station_lock(session, request.station_id)
    if request.calibration_id is not None:
        calibration = session.get(CalibrationRecord, request.calibration_id)
        if calibration is None or calibration.station_id != request.station_id:
            raise ValueError('Commissioning calibration must belong to the same station.')
    version = (session.scalar(select(func.max(CommissioningProfile.version)).where(
        CommissioningProfile.station_id == request.station_id,
    )) or 0) + 1
    profile = CommissioningProfile(
        id=f'profile-{uuid4().hex}', station_id=request.station_id, version=version,
        deployment_mode=request.deployment_mode, calibration_id=request.calibration_id,
        signal_mapping=request.signal_mapping.model_dump(mode='json', by_alias=True),
        integration_policy=request.integration_policy.model_dump(mode='json', by_alias=True),
        created_by=actor_id,
    )
    session.add(profile)
    session.commit()
    return profile


def activate_profile(
    session: Session, profile_id: str, actor_id: int, artifact_root: Path,
    reason: str = 'Commissioning profile activation',
) -> CommissioningProfile:
    profile = session.get(CommissioningProfile, profile_id)
    if profile is None:
        raise ValueError('Commissioning profile does not exist.')
    _station_lock(session, profile.station_id)
    if profile.deployment_mode in {'hardware-pilot', 'production'}:
        calibration = _verified_calibration(
            session.get(CalibrationRecord, profile.calibration_id), artifact_root,
        )
        if (
            calibration is None or calibration.status != 'valid'
            or calibration.station_id != profile.station_id
            or calibration.valid_until <= datetime.now(timezone.utc)
        ):
            raise ValueError('A valid unexpired calibration is required for profile activation.')
    previous = session.scalar(select(CommissioningProfile).where(
        CommissioningProfile.station_id == profile.station_id,
        CommissioningProfile.is_active.is_(True),
    ).with_for_update())
    session.execute(update(CommissioningProfile).where(
        CommissioningProfile.station_id == profile.station_id,
    ).values(is_active=False))
    profile.is_active = True
    session.add(CommissioningActivationEvent(
        station_id=profile.station_id, profile_id=profile.id,
        previous_profile_id=previous.id if previous and previous.id != profile.id else None,
        actor_id=actor_id, reason=reason,
    ))
    session.commit()
    return profile


def commissioning_snapshot(session: Session, station_id: str, artifact_root: Path) -> dict | None:
    profile = session.scalar(select(CommissioningProfile).where(
        CommissioningProfile.station_id == station_id,
        CommissioningProfile.is_active.is_(True),
    ).order_by(CommissioningProfile.version.desc()).limit(1))
    if profile is None:
        return None
    calibration = _verified_calibration(
        session.get(CalibrationRecord, profile.calibration_id) if profile.calibration_id else None,
        artifact_root,
    )
    return {
        'profileId': profile.id, 'stationId': profile.station_id, 'version': profile.version,
        'deploymentMode': profile.deployment_mode, 'signalMapping': profile.signal_mapping,
        'integrationPolicy': profile.integration_policy,
        'calibration': None if calibration is None else {
            'id': calibration.id, 'artifactSha256': calibration.artifact_sha256,
            'validUntil': calibration.valid_until.isoformat(), 'metrics': calibration.metrics,
        },
    }