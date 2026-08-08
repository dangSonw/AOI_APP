import json
import hashlib
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from app.database.session import SessionLocal
from app.models.settings_document import SettingsDocument
from app.models.user import User
from app.schemas.workstation_preferences import WorkstationPreferenceContentSchema


def _manifest_checksum(envelope: dict) -> str:
    content = {key: value for key, value in envelope.items() if key != 'manifest'}
    canonical = json.dumps(
        content, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
    ).encode('utf-8')
    return hashlib.sha256(canonical).hexdigest()


def _preference_payload() -> dict:
    return WorkstationPreferenceContentSchema.create_default().model_dump(mode='json', by_alias=True)


def test_settings_export_is_deterministic_and_verifiable(tmp_path) -> None:
    from app.services.settings_backup import export_settings, verify_settings_export

    first = tmp_path / 'first.json'
    second = tmp_path / 'second.json'
    exported_at = datetime(2026, 8, 8, tzinfo=timezone.utc)
    with SessionLocal() as session:
        export_settings(session, first, exported_at=exported_at)
        export_settings(session, second, exported_at=exported_at)

    assert first.read_bytes() == second.read_bytes()
    report = verify_settings_export(first)
    assert report['valid'] is True
    assert report['documentCount'] >= 0
    serialized = first.read_text(encoding='utf-8').lower()
    assert 'hashed_password' not in serialized
    assert 'access_token' not in serialized
    assert 'authorization' not in serialized


def test_settings_export_verifier_rejects_tampering(tmp_path) -> None:
    from app.services.settings_backup import InvalidSettingsExport, export_settings, verify_settings_export

    output = tmp_path / 'settings.json'
    with SessionLocal() as session:
        export_settings(session, output, exported_at=datetime(2026, 8, 8, tzinfo=timezone.utc))
    envelope = json.loads(output.read_text(encoding='utf-8'))
    envelope['formatVersion'] = 2
    output.write_text(json.dumps(envelope), encoding='utf-8')

    with pytest.raises(InvalidSettingsExport):
        verify_settings_export(output)


def test_settings_export_verifier_rejects_one_byte_tamper(tmp_path) -> None:
    from app.services.settings_backup import InvalidSettingsExport, export_settings, verify_settings_export

    output = tmp_path / 'settings.json'
    with SessionLocal() as session:
        export_settings(session, output, exported_at=datetime(2026, 8, 8, tzinfo=timezone.utc))
    payload = output.read_bytes()
    offset = payload.index(b'"exportedAt"')
    output.write_bytes(payload[:offset] + b'X' + payload[offset + 1:])

    with pytest.raises(InvalidSettingsExport):
        verify_settings_export(output)


def test_settings_export_verifier_rejects_invalid_collection_shape(tmp_path) -> None:
    from app.services.settings_backup import InvalidSettingsExport, export_settings, verify_settings_export

    output = tmp_path / 'settings.json'
    with SessionLocal() as session:
        export_settings(session, output, exported_at=datetime(2026, 8, 8, tzinfo=timezone.utc))
    envelope = json.loads(output.read_text(encoding='utf-8'))
    envelope['documents'] = {}
    envelope['manifest']['documentCount'] = 0
    envelope['manifest']['checksum'] = _manifest_checksum(envelope)
    output.write_text(json.dumps(envelope), encoding='utf-8')

    with pytest.raises(InvalidSettingsExport):
        verify_settings_export(output)


def test_settings_export_orders_versions_by_document_identity(tmp_path) -> None:
    from app.services.settings_backup import export_settings
    from app.services.settings_service import SettingsIdentity, create_settings_version

    suffix = uuid4().hex
    output = tmp_path / 'settings.json'
    with SessionLocal() as session:
        user_id = session.scalar(select(User.id).limit(1))
        assert user_id is not None
        for subject_id in (f'z-{suffix}', f'a-{suffix}'):
            create_settings_version(
                session,
                SettingsIdentity('workstation', subject_id, 'workstation-preferences', user_id),
                0,
                1,
                _preference_payload(),
                user_id,
                'Ordering test',
            )
        session.flush()
        export_settings(session, output, exported_at=datetime(2026, 8, 8, tzinfo=timezone.utc))
        session.rollback()

    envelope = json.loads(output.read_text(encoding='utf-8'))
    document_by_id = {item['id']: item for item in envelope['documents']}
    matching_subjects = [
        document_by_id[item['documentId']]['subjectId']
        for item in envelope['versions']
        if document_by_id[item['documentId']]['subjectId'].endswith(suffix)
    ]
    assert matching_subjects == [f'a-{suffix}', f'z-{suffix}']


def test_settings_export_verifier_rejects_unknown_schema(tmp_path) -> None:
    from app.services.settings_backup import InvalidSettingsExport, export_settings, verify_settings_export

    output = tmp_path / 'settings.json'
    with SessionLocal() as session:
        export_settings(session, output, exported_at=datetime(2026, 8, 8, tzinfo=timezone.utc))
    envelope = json.loads(output.read_text(encoding='utf-8'))
    if not envelope['versions']:
        pytest.skip('The integration database contains no settings versions.')
    document_id = envelope['versions'][0]['documentId']
    document = next(item for item in envelope['documents'] if item['id'] == document_id)
    document['documentKey'] = 'unknown-schema'
    envelope['manifest']['checksum'] = _manifest_checksum(envelope)
    output.write_text(json.dumps(envelope), encoding='utf-8')

    with pytest.raises(InvalidSettingsExport):
        verify_settings_export(output)


def test_settings_export_supports_empty_database(tmp_path) -> None:
    from app.services.settings_backup import export_settings, verify_settings_export

    output = tmp_path / 'empty.json'
    with SessionLocal() as session:
        session.execute(delete(SettingsDocument))
        session.flush()
        export_settings(session, output, exported_at=datetime(2026, 8, 8, tzinfo=timezone.utc))
        session.rollback()

    assert verify_settings_export(output) == {
        'valid': True,
        'documentCount': 0,
        'versionCount': 0,
        'activationCount': 0,
    }


def test_settings_export_refuses_symlink_and_parent_traversal(tmp_path) -> None:
    from app.services.settings_backup import export_settings

    target = tmp_path / 'target.json'
    symlink = tmp_path / 'settings.json'
    symlink.symlink_to(target)
    with SessionLocal() as session:
        with pytest.raises(ValueError, match='symbolic link'):
            export_settings(session, symlink, exported_at=datetime(2026, 8, 8, tzinfo=timezone.utc))
        with pytest.raises(ValueError, match='parent traversal'):
            export_settings(
                session,
                tmp_path / '..' / 'settings.json',
                exported_at=datetime(2026, 8, 8, tzinfo=timezone.utc),
            )