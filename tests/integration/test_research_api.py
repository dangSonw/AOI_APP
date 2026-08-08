from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.config.settings import get_settings
from app.main import app


@pytest.fixture
def authenticated_client():
    with TestClient(app) as client:
        settings = get_settings()
        login = client.post('/api/auth/login', json={'email': settings.seed_admin_email, 'password': settings.seed_admin_password})
        yield client, {'Authorization': f"Bearer {login.json()['accessToken']}"}


def test_research_run_search_and_reproducibility_export(authenticated_client) -> None:
    client, headers = authenticated_client
    suffix = uuid4().hex
    experiment_id = f'experiment-{suffix}'
    run_id = f'run-{suffix}'

    experiment = client.post('/api/research/experiments', headers=headers, json={
        'id': experiment_id, 'name': 'PCB anomaly baseline', 'description': 'Deterministic baseline',
    })
    run = client.post('/api/research/runs', headers=headers, json={
        'id': run_id, 'experimentId': experiment_id, 'status': 'completed', 'executionTarget': 'local-cpu',
        'codeRevision': '9ae70df', 'nodeVersions': {'patchcore': '1.0.0'}, 'environment': {'python': '3.12'},
        'randomSeeds': {'python': 42}, 'resources': {'cpuCores': 4},
        'datasetVersions': {'pcb-train': 'sha256:' + 'a' * 64}, 'parameters': {'memoryBankSize': 10000},
        'metrics': {'auroc': 0.98}, 'outputArtifacts': {}, 'error': None,
    })
    search = client.get('/api/research/runs?query=PCB%20anomaly', headers=headers)
    manifest = client.get(f'/api/research/runs/{run_id}/reproducibility-manifest', headers=headers)

    assert experiment.status_code == 201
    assert run.status_code == 201
    assert any(item['id'] == run_id for item in search.json())
    assert manifest.json()['codeRevision'] == '9ae70df'
    assert manifest.json()['randomSeeds'] == {'python': 42}


def test_model_registration_promotion_and_rollback_are_persisted(authenticated_client) -> None:
    client, headers = authenticated_client
    suffix = uuid4().hex
    experiment_id = f'experiment-{suffix}'
    run_id = f'run-{suffix}'
    model_name = f'pcb-anomaly-{suffix}'
    client.post('/api/research/experiments', headers=headers, json={'id': experiment_id, 'name': model_name, 'description': ''})
    client.post('/api/research/runs', headers=headers, json={
        'id': run_id, 'experimentId': experiment_id, 'status': 'completed', 'executionTarget': 'local-cpu',
        'codeRevision': '9ae70df', 'nodeVersions': {}, 'environment': {}, 'randomSeeds': {'python': 42},
        'resources': {}, 'datasetVersions': {}, 'parameters': {}, 'metrics': {'auroc': 0.98},
        'outputArtifacts': {}, 'error': None,
    })
    artifact = client.post(f'/api/research/runs/{run_id}/artifacts', headers=headers, files={
        'file': ('weights.bin', b'model-one', 'application/octet-stream'),
    })
    model = client.post('/api/models', headers=headers, json={'name': model_name, 'description': 'PCB model'})
    version_1 = client.post(f'/api/models/{model_name}/versions', headers=headers, json={
        'runId': run_id, 'artifactId': artifact.json()['id'], 'validationEvidence': {'passed': True, 'auroc': 0.98},
    })
    artifact_2 = client.post(f'/api/research/runs/{run_id}/artifacts', headers=headers, files={
        'file': ('weights-two.bin', b'model-two', 'application/octet-stream'),
    })
    version_2 = client.post(f'/api/models/{model_name}/versions', headers=headers, json={
        'runId': run_id, 'artifactId': artifact_2.json()['id'], 'validationEvidence': {'passed': True, 'auroc': 0.99},
    })
    first = client.post(f'/api/models/{model_name}/aliases/champion/promotions', headers=headers, json={
        'version': 1, 'reason': 'Validated baseline',
    })
    second = client.post(f'/api/models/{model_name}/aliases/champion/promotions', headers=headers, json={
        'version': 2, 'reason': 'Higher validation score',
    })
    rollback = client.post(f'/api/models/{model_name}/aliases/champion/rollback', headers=headers, json={'reason': 'Pilot regression'})

    assert model.status_code == 201
    assert version_1.json()['version'] == 1 and version_2.json()['version'] == 2
    assert first.json()['nextVersion'] == 1
    assert second.json()['previousVersion'] == 1
    assert rollback.json()['nextVersion'] == 1
    resolved = client.post(f'/api/models/resolve-production-bindings', headers=headers, json={
        'model': {'modelName': model_name, 'alias': 'champion'}, 'threshold': 0.8,
    })
    assert resolved.status_code == 200
    assert resolved.json()['model'] == {
        'modelName': model_name, 'modelVersion': 1, 'artifactSha256': artifact.json()['sha256'],
    }


def test_research_api_requires_authentication() -> None:
    with TestClient(app) as client:
        assert client.get('/api/research/runs').status_code == 401
