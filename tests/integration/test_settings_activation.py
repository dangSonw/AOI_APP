from uuid import uuid4

from fastapi.testclient import TestClient

from app.config.settings import get_settings
from app.main import app
from app.schemas.workstation_preferences import WorkstationPreferenceContentSchema


def test_activation_is_idempotent_and_rejects_changed_reuse() -> None:
    with TestClient(app) as client:
        settings = get_settings()
        login = client.post('/api/auth/login', json={
            'email': settings.seed_admin_email, 'password': settings.seed_admin_password,
        }).json()
        headers = {'Authorization': f"Bearer {login['accessToken']}"}
        station = f'activation-{uuid4().hex}'
        base = f'/api/v1/settings/workstation/{station}'
        payload = WorkstationPreferenceContentSchema.create_default().model_dump(mode='json', by_alias=True)
        client.post(f'{base}/versions', headers=headers, json={
            'documentKey': 'workstation-preferences', 'expectedRevision': 0,
            'schemaVersion': 1, 'payload': payload, 'reason': 'Initial',
        })
        activation_headers = {**headers, 'Idempotency-Key': f'activate-{station}'}
        first = client.post(f'{base}/activations', headers={**activation_headers, 'X-Request-ID': f'first-{station}'}, json={
            'documentKey': 'workstation-preferences', 'revision': 1, 'reason': 'Approve',
        })
        replay = client.post(f'{base}/activations', headers={**activation_headers, 'X-Request-ID': f'replay-{station}'}, json={
            'documentKey': 'workstation-preferences', 'revision': 1, 'reason': 'Approve',
        })
        changed = client.post(f'{base}/activations', headers={**activation_headers, 'X-Request-ID': f'changed-{station}'}, json={
            'documentKey': 'workstation-preferences', 'revision': 1, 'reason': 'Changed',
        })
        document = client.get(f'{base}?documentKey=workstation-preferences', headers=headers)
        history = client.get(f'{base}/activations?documentKey=workstation-preferences', headers=headers)

        assert first.status_code == 201
        assert replay.status_code == 200
        assert replay.json()['id'] == first.json()['id']
        assert changed.status_code == 409
        assert changed.json()['detail']['code'] == 'idempotency_key_reused'
        assert document.json()['activeRevision'] == 1
        assert history.json()['total'] == 1


def test_activation_requires_valid_idempotency_key() -> None:
    with TestClient(app) as client:
        settings = get_settings()
        login = client.post('/api/auth/login', json={
            'email': settings.seed_admin_email, 'password': settings.seed_admin_password,
        }).json()
        response = client.post(
            '/api/v1/settings/workstation/station-01/activations',
            headers={'Authorization': f"Bearer {login['accessToken']}"},
            json={'documentKey': 'workstation-preferences', 'revision': 1, 'reason': 'Approve'},
        )
        assert response.status_code == 422
        assert response.json()['detail']['code'] == 'idempotency_key_required'