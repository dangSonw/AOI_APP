from fastapi.testclient import TestClient
import pytest

from app.config.settings import get_settings
from app.main import app


def test_seed_operator_can_sign_in_and_read_protected_inputs() -> None:
    settings = get_settings()

    with TestClient(app) as client:
        login_response = client.post(
            '/api/auth/login',
            json={
                'email': settings.seed_admin_email,
                'password': settings.seed_admin_password,
            },
        )

        assert login_response.status_code == 200
        session = login_response.json()
        assert session['user']['email'] == settings.seed_admin_email

        input_response = client.get(
            '/api/io/inputs',
            headers={'Authorization': f"Bearer {session['accessToken']}"},
        )

        assert input_response.status_code == 200
        assert input_response.json()['machine']['doorClosed'] is True


def test_protected_inputs_reject_anonymous_requests() -> None:
    with TestClient(app) as client:
        response = client.get('/api/io/inputs')

    assert response.status_code == 401


def test_debug_session_is_hidden_when_debug_auto_login_is_disabled() -> None:
    settings = get_settings()
    original = settings.debug_auto_login
    settings.debug_auto_login = False
    try:
        with TestClient(app) as client:
            response = client.post('/api/auth/debug-session')
    finally:
        settings.debug_auto_login = original

    assert response.status_code == 404


def test_debug_session_uses_seed_account_without_receiving_credentials() -> None:
    settings = get_settings()
    original = settings.debug_auto_login
    settings.debug_auto_login = True
    try:
        with TestClient(app) as client:
            response = client.post('/api/auth/debug-session')
    finally:
        settings.debug_auto_login = original

    assert response.status_code == 200
    assert response.json()['user']['email'] == settings.seed_admin_email


def test_public_registration_is_disabled() -> None:
    with TestClient(app) as client:
        response = client.post(
            '/api/auth/register',
            json={
                'email': 'other@example.com',
                'fullName': 'Other User',
                'password': 'secure-password',
            },
        )

    assert response.status_code == 403
    assert response.json()['detail'] == 'Public account registration is disabled.'


@pytest.mark.parametrize(
    'origin',
    ['http://127.0.0.1:5173', 'http://localhost:5173'],
)
def test_development_loopback_origins_are_allowed(origin: str) -> None:
    with TestClient(app) as client:
        response = client.options(
            '/api/auth/login',
            headers={
                'Origin': origin,
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'content-type',
            },
        )

    assert response.status_code == 200
    assert response.headers['access-control-allow-origin'] == origin


def test_unconfigured_frontend_origin_is_rejected() -> None:
    with TestClient(app) as client:
        response = client.options(
            '/api/auth/login',
            headers={
                'Origin': 'http://example.com',
                'Access-Control-Request-Method': 'POST',
            },
        )

    assert response.status_code == 400
    assert 'access-control-allow-origin' not in response.headers