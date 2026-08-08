from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.config.settings import get_settings
from app.main import app
from app.schemas.workstation_preferences import WorkstationPreferenceContentSchema


@pytest.fixture
def authenticated_client():
    with TestClient(app) as client:
        settings = get_settings()
        login = client.post('/api/auth/login', json={
            'email': settings.seed_admin_email,
            'password': settings.seed_admin_password,
        })
        headers = {'Authorization': f"Bearer {login.json()['accessToken']}"}
        yield client, headers


def content(language: str = 'en-US') -> dict:
    value = WorkstationPreferenceContentSchema.create_default()
    return value.model_copy(update={
        'locale': value.locale.model_copy(update={'language': language}),
    }).model_dump(mode='json', by_alias=True)


def test_settings_api_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.get('/api/v1/settings/workstation/station-01?documentKey=workstation-preferences')
    assert response.status_code == 401


def test_validate_create_read_history_and_conflict(authenticated_client) -> None:
    client, headers = authenticated_client
    station = f'api-{uuid4().hex}'
    base = f'/api/v1/settings/workstation/{station}'
    validation = client.post(f'{base}/validate', headers=headers, json={
        'documentKey': 'workstation-preferences', 'schemaVersion': 1, 'payload': content(),
    })
    missing = client.get(f'{base}?documentKey=workstation-preferences', headers=headers)
    first = client.post(f'{base}/versions', headers=headers, json={
        'documentKey': 'workstation-preferences', 'expectedRevision': 0,
        'schemaVersion': 1, 'payload': content(), 'reason': 'Initial',
    })
    stale = client.post(f'{base}/versions', headers=headers, json={
        'documentKey': 'workstation-preferences', 'expectedRevision': 0,
        'schemaVersion': 1, 'payload': content('en-GB'), 'reason': 'Stale',
    })
    current = client.get(f'{base}?documentKey=workstation-preferences', headers=headers)
    history = client.get(f'{base}/history?documentKey=workstation-preferences', headers=headers)

    assert validation.status_code == 200
    assert missing.status_code == 404
    assert first.status_code == 201 and first.json()['revision'] == 1
    assert stale.status_code == 409
    assert stale.json()['detail']['code'] == 'settings_revision_conflict'
    assert current.json()['currentRevision'] == 1
    assert history.json()['total'] == 1


def test_export_and_import_verify_checksum(authenticated_client) -> None:
    client, headers = authenticated_client
    source = f'export-{uuid4().hex}'
    destination = f'import-{uuid4().hex}'
    source_base = f'/api/v1/settings/workstation/{source}'
    client.post(f'{source_base}/versions', headers=headers, json={
        'documentKey': 'workstation-preferences', 'expectedRevision': 0,
        'schemaVersion': 1, 'payload': content(), 'reason': 'Export',
    })
    exported = client.get(f'{source_base}/export?documentKey=workstation-preferences', headers=headers).json()
    exported['subjectId'] = destination
    imported = client.post(
        f'/api/v1/settings/workstation/{destination}/import?expectedRevision=0&reason=Portable',
        headers=headers, json=exported,
    )
    exported['payload']['locale']['language'] = 'en-GB'
    tampered = client.post(
        f'/api/v1/settings/workstation/{destination}/import?expectedRevision=1&reason=Tampered',
        headers=headers, json=exported,
    )

    assert imported.status_code == 201
    assert tampered.status_code == 422
    assert tampered.json()['detail']['code'] == 'settings_checksum_mismatch'