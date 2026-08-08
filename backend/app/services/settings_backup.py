import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.settings_activation import SettingsActivation
from app.models.settings_document import SettingsDocument
from app.models.settings_version import SettingsVersion
from app.services.settings_diff import settings_checksum
from app.services.settings_schema_registry import UnknownSettingsSchema, validate_settings_payload


class InvalidSettingsExport(RuntimeError):
    pass


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat().replace('+00:00', 'Z')
    return value


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def _manifest_checksum(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _safe_output_path(path: Path) -> None:
    if path.is_symlink():
        raise ValueError('Settings export output cannot be a symbolic link.')
    if '..' in path.parts:
        raise ValueError('Settings export output cannot contain parent traversal.')


def export_settings(session: Session, output: Path, *, exported_at: datetime) -> None:
    _safe_output_path(output)
    documents = list(session.scalars(select(SettingsDocument).order_by(
        SettingsDocument.scope,
        SettingsDocument.subject_id,
        SettingsDocument.document_key,
        SettingsDocument.owner_user_id.nullsfirst(),
        SettingsDocument.id,
    )))
    document_ids = [item.id for item in documents]
    versions = list(session.scalars(
        select(SettingsVersion)
        .join(SettingsDocument, SettingsVersion.document_id == SettingsDocument.id)
        .where(SettingsVersion.document_id.in_(document_ids) if document_ids else False)
        .order_by(
            SettingsDocument.scope,
            SettingsDocument.subject_id,
            SettingsDocument.document_key,
            SettingsDocument.owner_user_id.nullsfirst(),
            SettingsVersion.revision,
        )
    ))
    activations = list(session.scalars(
        select(SettingsActivation)
        .join(SettingsDocument, SettingsActivation.document_id == SettingsDocument.id)
        .where(SettingsActivation.document_id.in_(document_ids) if document_ids else False)
        .order_by(
            SettingsDocument.scope,
            SettingsDocument.subject_id,
            SettingsDocument.document_key,
            SettingsDocument.owner_user_id.nullsfirst(),
            SettingsActivation.created_at,
            SettingsActivation.id,
        )
    ))
    content: dict[str, Any] = {
        'formatVersion': 1,
        'exportedAt': _json_value(exported_at),
        'documents': [{
            'id': item.id,
            'scope': item.scope,
            'subjectId': item.subject_id,
            'documentKey': item.document_key,
            'ownerUserId': item.owner_user_id,
            'currentRevision': item.current_revision,
            'currentVersionId': item.current_version_id,
            'activeVersionId': item.active_version_id,
            'createdAt': _json_value(item.created_at),
            'updatedAt': _json_value(item.updated_at),
        } for item in documents],
        'versions': [{
            'id': item.id,
            'documentId': item.document_id,
            'revision': item.revision,
            'schemaVersion': item.schema_version,
            'payload': item.payload,
            'checksum': item.checksum,
            'createdBy': item.created_by,
            'reason': item.reason,
            'sourceVersionId': item.source_version_id,
            'createdAt': _json_value(item.created_at),
        } for item in versions],
        'activations': [{
            'id': item.id,
            'documentId': item.document_id,
            'requestedVersionId': item.requested_version_id,
            'idempotencyKey': item.idempotency_key,
            'requestChecksum': item.request_checksum,
            'status': item.status,
            'observedTargetRevision': item.observed_target_revision,
            'diagnostics': item.diagnostics,
            'requestedBy': item.requested_by,
            'reason': item.reason,
            'createdAt': _json_value(item.created_at),
            'completedAt': _json_value(item.completed_at),
        } for item in activations],
    }
    envelope = {
        **content,
        'manifest': {
            'algorithm': 'sha256',
            'documentCount': len(documents),
            'versionCount': len(versions),
            'activationCount': len(activations),
            'checksum': _manifest_checksum(content),
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + '.tmp')
    try:
        with temporary.open('wb') as stream:
            stream.write(json.dumps(envelope, sort_keys=True, ensure_ascii=False, indent=2).encode('utf-8'))
            stream.write(b'\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, output)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise


def verify_settings_export(path: Path) -> dict[str, Any]:
    try:
        envelope = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as error:
        raise InvalidSettingsExport('The settings export is not valid JSON.') from error
    if envelope.get('formatVersion') != 1:
        raise InvalidSettingsExport('The settings export format version is not supported.')
    manifest = envelope.pop('manifest', None)
    if not isinstance(manifest, dict) or manifest.get('algorithm') != 'sha256':
        raise InvalidSettingsExport('The settings export manifest is missing or invalid.')
    if manifest.get('checksum') != _manifest_checksum(envelope):
        raise InvalidSettingsExport('The settings export manifest checksum is invalid.')
    documents = envelope.get('documents', [])
    versions = envelope.get('versions', [])
    activations = envelope.get('activations', [])
    if not all(isinstance(items, list) for items in (documents, versions, activations)):
        raise InvalidSettingsExport('The settings export collections are invalid.')
    if (
        manifest.get('documentCount') != len(documents)
        or manifest.get('versionCount') != len(versions)
        or manifest.get('activationCount') != len(activations)
    ):
        raise InvalidSettingsExport('The settings export manifest counts are invalid.')
    document_keys = {item['id']: item['documentKey'] for item in documents}
    for version in versions:
        try:
            normalized = validate_settings_payload(
                document_keys[version['documentId']], version['schemaVersion'], version['payload'],
            )
        except (KeyError, UnknownSettingsSchema, ValueError) as error:
            raise InvalidSettingsExport('The settings export contains an invalid version.') from error
        if settings_checksum(normalized) != version['checksum']:
            raise InvalidSettingsExport('The settings export contains an invalid version checksum.')
    return {
        'valid': True,
        'documentCount': len(documents),
        'versionCount': len(versions),
        'activationCount': len(activations),
    }