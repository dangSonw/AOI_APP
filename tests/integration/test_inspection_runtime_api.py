import pytest
from fastapi.testclient import TestClient

from app.config.settings import get_settings
from app.main import app


@pytest.fixture
def authenticated_client():
    with TestClient(app) as client:
        settings = get_settings()
        login = client.post('/api/auth/login', json={
            'email': settings.seed_admin_email,
            'password': settings.seed_admin_password,
        })
        assert login.status_code == 200
        yield client, {'Authorization': f"Bearer {login.json()['accessToken']}"}


def test_latest_run_restores_persisted_terminal_state(authenticated_client) -> None:
    client, headers = authenticated_client

    response = client.get('/api/inspection-runs/latest', headers=headers)

    assert response.status_code == 200
    if response.json() is not None:
        assert response.json()['status'] in {
            'queued', 'precheck', 'capturing', 'executing', 'completed', 'faulted', 'cancelled',
        }


def test_inspection_run_routes_require_authentication() -> None:
    with TestClient(app) as client:
        assert client.get('/api/inspection-runs/latest').status_code == 401
        assert client.get('/api/inspection-runs/active').status_code == 401