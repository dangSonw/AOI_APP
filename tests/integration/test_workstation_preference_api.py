from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.workstation_preferences import get_preference_repository
from app.auth.dependencies import get_current_user
from app.main import app
from app.services.workstation_preference_repository import WorkstationPreferenceRepository


@pytest.fixture
def client(tmp_path: Path):
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=11, is_active=True)
    app.dependency_overrides[get_preference_repository] = lambda: WorkstationPreferenceRepository(tmp_path)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_preferences_require_authentication() -> None:
    with TestClient(app) as anonymous_client:
        assert anonymous_client.get('/api/workstation-preferences/station-01').status_code == 401


def test_preferences_round_trip_and_reject_stale_revision(client: TestClient) -> None:
    default_response = client.get('/api/workstation-preferences/station-01')
    payload = default_response.json()
    payload['photometric']['lights'][0]['azimuth'] = 35

    saved_response = client.put('/api/workstation-preferences/station-01', json=payload)
    stale_response = client.put('/api/workstation-preferences/station-01', json=payload)

    assert default_response.status_code == 200
    assert saved_response.status_code == 200
    assert saved_response.json()['revision'] == 1
    assert saved_response.json()['photometric']['lights'][0]['azimuth'] == 35
    assert stale_response.status_code == 409


def test_preferences_reject_invalid_workstation_id(client: TestClient) -> None:
    assert client.get('/api/workstation-preferences/Station_01').status_code == 422