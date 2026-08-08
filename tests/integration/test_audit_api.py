from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.api.workstation_preferences import get_preference_repository
from app.config.settings import get_settings
from app.database.session import SessionLocal
from app.main import app
from app.models.audit_event import AuditEvent
from app.services.workstation_preference_repository import WorkstationPreferenceRepository


@pytest.fixture
def client(tmp_path: Path):
    app.dependency_overrides[get_preference_repository] = lambda: WorkstationPreferenceRepository(tmp_path)
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        with SessionLocal() as session:
            session.execute(delete(AuditEvent).where(AuditEvent.request_id.in_((
                'audit-login-request',
                'audit-preference-update',
                'audit-invalid-update',
            ))))
            session.commit()


def authenticate(client: TestClient) -> tuple[str, int]:
    settings = get_settings()
    response = client.post(
        '/api/auth/login',
        headers={'X-Request-ID': 'audit-login-request'},
        json={'email': settings.seed_admin_email, 'password': settings.seed_admin_password},
    )
    session = response.json()
    return session['accessToken'], session['user']['id']


def test_authenticated_mutation_emits_queryable_audit_event(client: TestClient) -> None:
    access_token, user_id = authenticate(client)
    headers = {'Authorization': f'Bearer {access_token}'}
    payload = client.get('/api/workstation-preferences/audit-station', headers=headers).json()

    mutation = client.put(
        '/api/workstation-preferences/audit-station',
        headers={**headers, 'X-Request-ID': 'audit-preference-update'},
        json=payload,
    )
    audit_response = client.get('/api/audit-events?page=1&pageSize=100', headers=headers)

    assert mutation.status_code == 200
    assert mutation.headers['x-request-id'] == 'audit-preference-update'
    assert audit_response.status_code == 200
    event = next(item for item in audit_response.json()['events'] if item['requestId'] == 'audit-preference-update')
    assert event['actorId'] == user_id
    assert event['action'] == 'update'
    assert event['method'] == 'PUT'
    assert event['path'] == '/api/workstation-preferences/audit-station'
    assert event['resourceType'] == 'workstation-preferences'
    assert event['resourceId'] == 'audit-station'
    assert event['statusCode'] == 200
    assert event['result'] == 'success'


def test_failed_authenticated_mutation_is_audited(client: TestClient) -> None:
    access_token, _ = authenticate(client)
    headers = {'Authorization': f'Bearer {access_token}'}

    mutation = client.put(
        '/api/workstation-preferences/audit-station',
        headers={**headers, 'X-Request-ID': 'audit-invalid-update'},
        json={},
    )
    audit_response = client.get('/api/audit-events?page=1&pageSize=100', headers=headers)

    assert mutation.status_code == 422
    event = next(item for item in audit_response.json()['events'] if item['requestId'] == 'audit-invalid-update')
    assert event['actorId'] is not None
    assert event['statusCode'] == 422
    assert event['result'] == 'failure'


def test_audit_events_reject_anonymous_reads() -> None:
    with TestClient(app) as anonymous_client:
        assert anonymous_client.get('/api/audit-events').status_code == 401