import pytest
from fastapi.testclient import TestClient

from app.config.settings import get_settings
from app.main import app


@pytest.fixture
def client_and_headers():
    with TestClient(app) as client:
        settings = get_settings()
        login = client.post('/api/auth/login', json={
            'email': settings.seed_admin_email, 'password': settings.seed_admin_password,
        })
        assert login.status_code == 200
        yield client, {'Authorization': f"Bearer {login.json()['accessToken']}"}


def test_uncommissioned_station_readiness_fails_closed(client_and_headers) -> None:
    client, headers = client_and_headers
    response = client.get('/api/pilot/stations/not-commissioned/readiness', headers=headers)
    assert response.status_code == 200
    assert response.json()['ready'] is False
    assert response.json()['reasons'] == ['no-active-commissioning-profile']


def test_calibration_artifact_upload_is_authenticated_bounded_and_checksum_addressed(
    client_and_headers,
) -> None:
    import hashlib
    client, headers = client_and_headers
    content = b'{"cameraMatrix":[1,0,1]}'

    response = client.put(
        '/api/pilot/calibration-artifacts/api-test-calibration.json',
        content=content,
        headers={**headers, 'Content-Type': 'application/json'},
    )

    assert response.status_code == 201
    assert response.json()['sha256'] == hashlib.sha256(content).hexdigest()
    assert response.json()['relativePath'] == 'api-test-calibration.json'
    conflict = client.put(
        '/api/pilot/calibration-artifacts/api-test-calibration.json',
        content=b'{"different":true}',
        headers={**headers, 'Content-Type': 'application/json'},
    )
    assert conflict.status_code == 409


def test_commissioning_api_activates_valid_calibration_with_audited_reason(client_and_headers) -> None:
    import hashlib
    from datetime import datetime, timedelta, timezone
    from uuid import uuid4

    client, headers = client_and_headers
    suffix = uuid4().hex
    station_id = f'api-station-{suffix}'
    artifact_name = f'api-calibration-{suffix}.json'
    content = b'{"cameraMatrix":[1,0,1]}'
    upload = client.put(
        f'/api/pilot/calibration-artifacts/{artifact_name}', content=content,
        headers={**headers, 'Content-Type': 'application/json'},
    )
    calibration = client.post('/api/pilot/calibrations', headers=headers, json={
        'stationId': station_id, 'cameraId': 'top-camera', 'calibrationType': 'intrinsic',
        'artifactRelativePath': artifact_name,
        'artifactSha256': hashlib.sha256(content).hexdigest(),
        'validUntil': (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        'metrics': {'imageCount': 20, 'coveragePercent': 90, 'reprojectionErrorPixels': 0.2},
    })
    profile = client.post('/api/pilot/commissioning-profiles', headers=headers, json={
        'stationId': station_id, 'deploymentMode': 'hardware-pilot',
        'calibrationId': calibration.json()['id'], 'signalMapping': {}, 'integrationPolicy': {},
    })
    activation = client.post(
        f"/api/pilot/commissioning-profiles/{profile.json()['id']}/activate",
        headers=headers, json={'reason': 'API commissioning acceptance'},
    )
    readiness = client.get(f'/api/pilot/stations/{station_id}/readiness', headers=headers)

    assert upload.status_code == 201
    assert calibration.status_code == 201
    assert profile.status_code == 201
    assert activation.status_code == 200
    assert readiness.json()['ready'] is True
    assert readiness.json()['snapshot']['calibration']['id'] == calibration.json()['id']


def test_pilot_endpoints_require_authentication() -> None:
    with TestClient(app) as client:
        assert client.get('/api/pilot/stations/station-01/readiness').status_code == 401
        assert client.get('/api/pilot/integration-outbox').status_code == 401
        assert client.put(
            '/api/pilot/calibration-artifacts/no-auth.json', content=b'{}',
            headers={'Content-Type': 'application/json'},
        ).status_code == 401