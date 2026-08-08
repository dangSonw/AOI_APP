from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import ValidationError
from sqlalchemy import select

from app.auth.dependencies import CurrentUser, DatabaseSession
from app.models.settings_document import SettingsDocument
from app.models.settings_version import SettingsVersion
from app.schemas.settings import (
    SettingsDocumentResponse,
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
    SettingsRevisionConflict,
    create_settings_version,
    get_current_settings,
    list_settings_history,
    rollback_settings,
)


router = APIRouter(prefix='/api/v1/settings', tags=['settings'])


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
    current_user: CurrentUser,
    session: DatabaseSession,
) -> SettingsVersionResponse:
    identity = _identity(scope, subject_id, request.document_key, current_user.id)
    try:
        version = create_settings_version(
            session, identity, request.expected_revision, request.schema_version,
            request.payload, current_user.id, request.reason,
        )
        session.commit()
        session.refresh(version)
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
    current_user: CurrentUser,
    session: DatabaseSession,
) -> SettingsVersionResponse:
    identity = _identity(scope, subject_id, request.document_key, current_user.id)
    try:
        version = rollback_settings(
            session, identity, request.expected_revision, request.target_revision,
            current_user.id, request.reason,
        )
        session.commit()
        session.refresh(version)
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
        version = create_settings_version(
            session, identity, expected_revision, envelope.schema_version,
            envelope.payload, current_user.id, reason,
        )
        session.commit()
        session.refresh(version)
    except SettingsRevisionConflict as error:
        session.rollback()
        raise HTTPException(status_code=409, detail=_conflict_detail(error)) from error
    except (UnknownSettingsSchema, ValidationError) as error:
        session.rollback()
        raise _validation_error(error) from error
    return _version_response(version)