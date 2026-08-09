from datetime import datetime, timezone

import hashlib
import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.auth.dependencies import CurrentUser, DatabaseSession
from app.config.settings import PROJECT_ROOT
from app.models.pilot import CalibrationRecord, CommissioningProfile, IntegrationOutboxEvent
from app.schemas.pilot import (
    CalibrationCreateRequest, CommissioningActivationRequest, CommissioningProfileCreateRequest,
)
from app.services.pilot_service import activate_profile, commissioning_snapshot, create_calibration, create_profile


router = APIRouter(prefix='/api/pilot', tags=['pilot'])
CALIBRATION_ROOT = PROJECT_ROOT / 'data/calibration'
MAX_CALIBRATION_ARTIFACT_BYTES = 2 * 1024 * 1024


@router.put('/calibration-artifacts/{artifact_name}', status_code=status.HTTP_201_CREATED)
async def upload_calibration_artifact(
    artifact_name: str,
    _: CurrentUser,
    request: Request,
) -> dict:
    if request.headers.get('content-type', '').split(';', 1)[0].strip() != 'application/json':
        raise HTTPException(415, 'Calibration artifact content type must be application/json.')
    declared_length = request.headers.get('content-length')
    if declared_length:
        try:
            if int(declared_length) > MAX_CALIBRATION_ARTIFACT_BYTES:
                raise HTTPException(413, 'Calibration artifact size is invalid.')
        except ValueError as error:
            raise HTTPException(422, 'Calibration artifact content length is invalid.') from error
    content = await request.body()
    if not artifact_name.endswith('.json') or not artifact_name.replace('-', '').replace('_', '').replace('.', '').isalnum():
        raise HTTPException(422, 'Calibration artifact name is invalid.')
    if not content or len(content) > MAX_CALIBRATION_ARTIFACT_BYTES:
        raise HTTPException(413, 'Calibration artifact size is invalid.')
    try:
        json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HTTPException(415, 'Calibration artifact must be valid JSON.') from error
    if content.lstrip()[:1] not in {b'{', b'['}:
        raise HTTPException(415, 'Calibration artifact must be JSON.')
    CALIBRATION_ROOT.mkdir(parents=True, exist_ok=True)
    destination = CALIBRATION_ROOT / artifact_name
    checksum = hashlib.sha256(content).hexdigest()
    if destination.exists():
        if hashlib.sha256(destination.read_bytes()).hexdigest() != checksum:
            raise HTTPException(409, 'Calibration artifact name already identifies different immutable content.')
        return {'relativePath': artifact_name, 'byteLength': len(content), 'sha256': checksum}
    temporary = destination.with_suffix('.json.tmp')
    with temporary.open('wb') as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(destination)
    return {'relativePath': artifact_name, 'byteLength': len(content), 'sha256': checksum}


@router.post('/calibrations', status_code=status.HTTP_201_CREATED)
def add_calibration(request: CalibrationCreateRequest, user: CurrentUser, session: DatabaseSession) -> dict:
    try:
        record = create_calibration(session, request, user.id, CALIBRATION_ROOT)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    return {'id': record.id, 'status': record.status, 'validUntil': record.valid_until,
            'artifactSha256': record.artifact_sha256, 'metrics': record.metrics}


@router.post('/commissioning-profiles', status_code=status.HTTP_201_CREATED)
def add_profile(request: CommissioningProfileCreateRequest, user: CurrentUser, session: DatabaseSession) -> dict:
    try:
        profile = create_profile(session, request, user.id)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    return {'id': profile.id, 'stationId': profile.station_id, 'version': profile.version,
            'deploymentMode': profile.deployment_mode, 'isActive': profile.is_active}


@router.post('/commissioning-profiles/{profile_id}/activate')
def activate(
    profile_id: str, request: CommissioningActivationRequest,
    user: CurrentUser, session: DatabaseSession,
) -> dict:
    try:
        profile = activate_profile(session, profile_id, user.id, CALIBRATION_ROOT, request.reason)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    return {'id': profile.id, 'stationId': profile.station_id, 'version': profile.version, 'isActive': True}


@router.get('/stations/{station_id}/readiness')
def station_readiness(station_id: str, _: CurrentUser, session: DatabaseSession) -> dict:
    reasons: list[str] = []
    try:
        snapshot = commissioning_snapshot(session, station_id, CALIBRATION_ROOT)
    except ValueError:
        snapshot = None
        reasons.append('invalid-calibration-artifact')
    if snapshot is None:
        if not reasons:
            reasons.append('no-active-commissioning-profile')
    elif snapshot['deploymentMode'] in {'hardware-pilot', 'production'}:
        calibration = snapshot.get('calibration')
        if calibration is None:
            reasons.append('missing-calibration')
        elif datetime.fromisoformat(calibration['validUntil']) <= datetime.now(timezone.utc):
            reasons.append('expired-calibration')
    return {'stationId': station_id, 'ready': not reasons, 'reasons': reasons, 'snapshot': snapshot}


@router.get('/integration-outbox')
def read_outbox(_: CurrentUser, session: DatabaseSession, limit: int = 100) -> list[dict]:
    events = session.scalars(select(IntegrationOutboxEvent).order_by(
        IntegrationOutboxEvent.id.desc(),
    ).limit(max(1, min(limit, 100))))
    return [{'id': event.id, 'runId': event.run_id, 'channel': event.channel,
             'eventType': event.event_type, 'status': event.status,
             'attemptCount': event.attempt_count, 'createdAt': event.created_at}
            for event in events]