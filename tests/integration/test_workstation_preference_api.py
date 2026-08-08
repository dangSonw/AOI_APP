from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.database.session import SessionLocal
from app.main import app
from app.models.settings_document import SettingsDocument
from app.models.user import User
from sqlalchemy import delete, select


@pytest.fixture
def client():
    with SessionLocal() as session:
        user_id = session.scalar(select(User.id).limit(1))
    assert user_id is not None
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=user_id, is_active=True)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_preferences_require_authentication() -> None:
    with TestClient(app) as anonymous_client:
        assert anonymous_client.get('/api/workstation-preferences/station-01').status_code == 401


def test_preferences_round_trip_and_reject_stale_revision(client: TestClient) -> None:
    station = f'legacy-{uuid4().hex}'
    default_response = client.get(f'/api/workstation-preferences/{station}')
    payload = default_response.json()
    payload['photometric']['lights'][0]['azimuth'] = 35
    payload['locale']['language'] = 'en-GB'
    payload['locale']['measurementSystem'] = 'imperial'

    saved_response = client.put(f'/api/workstation-preferences/{station}', json=payload)
    stale_response = client.put(f'/api/workstation-preferences/{station}', json=payload)

    assert default_response.status_code == 200
    assert saved_response.status_code == 200
    assert saved_response.json()['revision'] == 1
    assert saved_response.json()['photometric']['lights'][0]['azimuth'] == 35
    assert saved_response.json()['locale']['language'] == 'en-GB'
    assert saved_response.json()['locale']['measurementSystem'] == 'imperial'
    assert stale_response.status_code == 409
    with SessionLocal() as session:
        session.execute(delete(SettingsDocument).where(SettingsDocument.subject_id == station))
        session.commit()


def test_preferences_reject_invalid_workstation_id(client: TestClient) -> None:
    assert client.get('/api/workstation-preferences/Station_01').status_code == 422