from typing import Any

import re

from fastapi import APIRouter, Header, HTTPException, Query, Request, Response, status
from pydantic import ValidationError
from sqlalchemy import select

from app.auth.dependencies import CurrentUser, DatabaseSession
from app.models.settings_document import SettingsDocument
from app.models.settings_version import SettingsVersion
from app.models.audit_event import AuditEvent
from app.schemas.settings import (
    SettingsDocumentResponse,
    SettingsActivationListResponse,
    SettingsActivationRequest,
    SettingsActivationResponse,
    SettingsExportEnvelope,
    SettingsHistoryResponse,
    SettingsRollbackRequest,
    SettingsScope,
    SettingsValidationRequest,
    SettingsVersionCreate,
    SettingsVersionResponse,
)
from app.services.settings_diff import settings_checksum
from app.services.settings_schema_registry import UnknownSettingsSchema, validate_settings_payload
from app.services.settings_service import (
    SettingsIdentity,
    IdempotencyKeyReused,
    SettingsRevisionConflict,
    activate_settings,
    create_settings_version,
    get_current_settings,
    list_settings_history,
    list_settings_activations,
    rollback_settings,
)


router = APIRouter(prefix='/api/v1/settings', tags=['settings'])
IDEMPOTENCY_KEY_PATTERN = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$')


def _identity(scope: SettingsScope, subject_id: str, document_key: str, user_id: int) -> SettingsIdentity:
    owner_user_id = user_id if scope in {'user', 'workstation'} else None
    return SettingsIdentity(scope, subject_id, document_key, owner_user_id)


def _version_response(version: SettingsVersion) -> SettingsVersionResponse:
    return SettingsVersionResponse.model_validate(version)


def _conflict_detail(error: SettingsRevisionConflict) -> dict[str, Any]:
    return {
        'code': 'settings_revision_conflict',
        'message': str(error),
        'expectedRevision': error.expected_revision,
        'currentRevision': error.current_revision,
        'currentChecksum': error.current_checksum,
        'differences': error.differences,
    }


def _validation_error(error: Exception) -> HTTPException:
    details = error.errors() if isinstance(error, ValidationError) else []
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            'code': 'settings_validation_failed',
            'message': str(error),
            'errors': details,
        },
    )


def _record_settings_success(
    session,
    request: Request,
    current_user,
    version: SettingsVersion,
    *,
    action: str,
    reason: str,
    before_checksum: str | None,
    status_code: int = 201,
) -> None:
    session.add(AuditEvent(
        actor_id=current_user.id,
        action=action,
        method='POST',
        path=request.url.path,
        resource_type='settings',
        resource_id=str(version.document_id),
        request_id=request.state.request_id,
        status_code=status_code,
        result='success',
        before_checksum=before_checksum,
        after_checksum=version.checksum,
        reason=reason,
        client_metadata={},
    ))
    session.flush()


@router.post('/{scope}/{subject_id}/validate')
def validate_settings(
    scope: SettingsScope,
    subject_id: str,
    request: SettingsValidationRequest,
    _: CurrentUser,
) -> dict[str, Any]:
    try:
        normalized = validate_settings_payload(request.document_key, request.schema_version, request.payload)
    except (UnknownSettingsSchema, ValidationError) as error:
        raise _validation_error(error) from error
    return {'valid': True, 'payload': normalized}


@router.post('/{scope}/{subject_id}/versions', response_model=SettingsVersionResponse, status_code=201)
def create_version(
    scope: SettingsScope,
    subject_id: str,
    request: SettingsVersionCreate,
    http_request: Request,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> SettingsVersionResponse:
    identity = _identity(scope, subject_id, request.document_key, current_user.id)
    try:
        previous = get_current_settings(session, identity)
        version = create_settings_version(
            session, identity, request.expected_revision, request.schema_version,
            request.payload, current_user.id, request.reason,
        )
        _record_settings_success(
            session, http_request, current_user, version,
            action='create-version', reason=request.reason,
            before_checksum=previous.checksum if previous is not None else None,
        )
        session.commit()
        session.refresh(version)
        http_request.state.audit_recorded = True
    except SettingsRevisionConflict as error:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_conflict_detail(error)) from error
    except (UnknownSettingsSchema, ValidationError) as error:
        session.rollback()
        raise _validation_error(error) from error
    return _version_response(version)


@router.get('/{scope}/{subject_id}', response_model=SettingsDocumentResponse)
def get_document(
    scope: SettingsScope,
    subject_id: str,
    current_user: CurrentUser,
    session: DatabaseSession,
    document_key: str = Query(alias='documentKey', min_length=1, max_length=128),
) -> SettingsDocumentResponse:
    identity = _identity(scope, subject_id, document_key, current_user.id)
    version = get_current_settings(session, identity)
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={'code': 'settings_document_not_found', 'message': 'The settings document does not exist.'},
        )
    document = session.get(SettingsDocument, version.document_id)
    assert document is not None
    active_revision = None
    if document.active_version_id is not None:
        active = session.get(SettingsVersion, document.active_version_id)
        active_revision = active.revision if active is not None else None
    return SettingsDocumentResponse(
        scope=scope,
        subject_id=subject_id,
        document_key=document_key,
        owner_user_id=identity.owner_user_id,
        current_revision=document.current_revision,
        current=_version_response(version),
        active_revision=active_revision,
    )


@router.get('/{scope}/{subject_id}/history', response_model=SettingsHistoryResponse)
def get_history(
    scope: SettingsScope,
    subject_id: str,
    current_user: CurrentUser,
    session: DatabaseSession,
    document_key: str = Query(alias='documentKey', min_length=1, max_length=128),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> SettingsHistoryResponse:
    versions, total = list_settings_history(
        session, _identity(scope, subject_id, document_key, current_user.id), offset, limit,
    )
    return SettingsHistoryResponse(versions=[_version_response(item) for item in versions], total=total)


@router.post('/{scope}/{subject_id}/rollback', response_model=SettingsVersionResponse, status_code=201)
def rollback_version(
    scope: SettingsScope,
    subject_id: str,
    request: SettingsRollbackRequest,
    http_request: Request,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> SettingsVersionResponse:
    identity = _identity(scope, subject_id, request.document_key, current_user.id)
    try:
        previous = get_current_settings(session, identity)
        version = rollback_settings(
            session, identity, request.expected_revision, request.target_revision,
            current_user.id, request.reason,
        )
        _record_settings_success(
            session, http_request, current_user, version,
            action='rollback', reason=request.reason,
            before_checksum=previous.checksum if previous is not None else None,
        )
        session.commit()
        session.refresh(version)
        http_request.state.audit_recorded = True
    except SettingsRevisionConflict as error:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_conflict_detail(error)) from error
    except ValueError as error:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={
            'code': 'settings_revision_not_found', 'message': str(error),
        }) from error
    return _version_response(version)


@router.get('/{scope}/{subject_id}/export', response_model=SettingsExportEnvelope)
def export_settings(
    scope: SettingsScope,
    subject_id: str,
    current_user: CurrentUser,
    session: DatabaseSession,
    document_key: str = Query(alias='documentKey', min_length=1, max_length=128),
) -> SettingsExportEnvelope:
    identity = _identity(scope, subject_id, document_key, current_user.id)
    version = get_current_settings(session, identity)
    if version is None:
        raise HTTPException(status_code=404, detail={
            'code': 'settings_document_not_found', 'message': 'The settings document does not exist.',
        })
    return SettingsExportEnvelope(
        scope=scope,
        subject_id=subject_id,
        document_key=document_key,
        owner_user_id=identity.owner_user_id,
        revision=version.revision,
        schema_version=version.schema_version,
        payload=version.payload,
        payload_checksum=version.checksum,
    )


@router.post('/{scope}/{subject_id}/import', response_model=SettingsVersionResponse, status_code=201)
def import_settings(
    scope: SettingsScope,
    subject_id: str,
    envelope: SettingsExportEnvelope,
    http_request: Request,
    current_user: CurrentUser,
    session: DatabaseSession,
    expected_revision: int = Query(alias='expectedRevision', ge=0),
    reason: str = Query(min_length=1, max_length=2000),
) -> SettingsVersionResponse:
    identity = _identity(scope, subject_id, envelope.document_key, current_user.id)
    if envelope.scope != scope or envelope.subject_id != subject_id or envelope.owner_user_id != identity.owner_user_id:
        raise HTTPException(status_code=422, detail={
            'code': 'settings_identity_mismatch', 'message': 'The settings export identity does not match the destination.',
        })
    if settings_checksum(envelope.payload) != envelope.payload_checksum:
        raise HTTPException(status_code=422, detail={
            'code': 'settings_checksum_mismatch', 'message': 'The settings export checksum is invalid.',
        })
    try:
        previous = get_current_settings(session, identity)
        version = create_settings_version(
            session, identity, expected_revision, envelope.schema_version,
            envelope.payload, current_user.id, reason,
        )
        _record_settings_success(
            session, http_request, current_user, version,
            action='import', reason=reason,
            before_checksum=previous.checksum if previous is not None else None,
        )
        session.commit()
        session.refresh(version)
        http_request.state.audit_recorded = True
    except SettingsRevisionConflict as error:
        session.rollback()
        raise HTTPException(status_code=409, detail=_conflict_detail(error)) from error
    except (UnknownSettingsSchema, ValidationError) as error:
        session.rollback()
        raise _validation_error(error) from error
    return _version_response(version)


@router.post('/{scope}/{subject_id}/activations', response_model=SettingsActivationResponse, status_code=201)
def activate_version(
    scope: SettingsScope,
    subject_id: str,
    activation_request: SettingsActivationRequest,
    request: Request,
    response: Response,
    current_user: CurrentUser,
    session: DatabaseSession,
    idempotency_key: str | None = Header(default=None, alias='Idempotency-Key'),
) -> SettingsActivationResponse:
    if idempotency_key is None or IDEMPOTENCY_KEY_PATTERN.fullmatch(idempotency_key) is None:
        raise HTTPException(status_code=422, detail={
            'code': 'idempotency_key_required',
            'message': 'A valid Idempotency-Key header is required.',
        })
    identity = _identity(scope, subject_id, activation_request.document_key, current_user.id)
    try:
        activation, replayed = activate_settings(
            session, identity, activation_request.revision, idempotency_key,
            current_user.id, activation_request.reason,
        )
        document = session.get(SettingsDocument, activation.document_id)
        version = session.get(SettingsVersion, activation.requested_version_id)
        assert document is not None and version is not None
        audit_event = AuditEvent(
            actor_id=current_user.id,
            action='activate',
            method='POST',
            path=request.url.path,
            resource_type='settings',
            resource_id=str(document.id),
            request_id=request.state.request_id,
            status_code=200 if replayed else 201,
            result='success',
            before_checksum=None,
            after_checksum=version.checksum,
            reason=activation_request.reason,
            client_metadata={},
        )
        session.add(audit_event)
        session.commit()
        session.refresh(activation)
        request.state.audit_recorded = True
    except IdempotencyKeyReused as error:
        session.rollback()
        raise HTTPException(status_code=409, detail={
            'code': 'idempotency_key_reused', 'message': str(error),
        }) from error
    except ValueError as error:
        session.rollback()
        raise HTTPException(status_code=404, detail={
            'code': 'settings_revision_not_found', 'message': str(error),
        }) from error
    if replayed:
        response.status_code = 200
    return SettingsActivationResponse.model_validate(activation)


@router.get('/{scope}/{subject_id}/activations', response_model=SettingsActivationListResponse)
def get_activations(
    scope: SettingsScope,
    subject_id: str,
    current_user: CurrentUser,
    session: DatabaseSession,
    document_key: str = Query(alias='documentKey', min_length=1, max_length=128),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> SettingsActivationListResponse:
    activations, total = list_settings_activations(
        session, _identity(scope, subject_id, document_key, current_user.id), offset, limit,
    )
    return SettingsActivationListResponse(
        activations=[SettingsActivationResponse.model_validate(item) for item in activations],
        total=total,
    )