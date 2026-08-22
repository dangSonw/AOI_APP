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


def test_model_lifecycle_rejects_invalid_actions_and_missing_versions(authenticated_client) -> None:
    client, headers = authenticated_client
    suffix = uuid4().hex
    experiment_id = f'experiment-{suffix}'
    run_id = f'run-{suffix}'
    model_name = f'pcb-lifecycle-{suffix}'
    client.post('/api/research/experiments', headers=headers, json={'id': experiment_id, 'name': model_name, 'description': ''})
    client.post('/api/research/runs', headers=headers, json={
        'id': run_id, 'experimentId': experiment_id, 'status': 'completed', 'executionTarget': 'local-cpu',
        'codeRevision': '9ae70df', 'nodeVersions': {}, 'environment': {}, 'randomSeeds': {},
        'resources': {}, 'datasetVersions': {}, 'parameters': {}, 'metrics': {}, 'outputArtifacts': {}, 'error': None,
    })
    artifact = client.post(f'/api/research/runs/{run_id}/artifacts', headers=headers, files={
        'file': ('weights.bin', b'lifecycle-model', 'application/octet-stream'),
    }).json()
    client.post('/api/models', headers=headers, json={'name': model_name, 'description': ''})
    client.post(f'/api/models/{model_name}/versions', headers=headers, json={
        'runId': run_id, 'artifactId': artifact['id'], 'validationEvidence': {'passed': False},
    })

    rejected_validation = client.post(
        f'/api/models/{model_name}/aliases/champion/promotions', headers=headers,
        json={'version': 1, 'reason': 'Not validated'},
    )
    missing_version = client.post(
        f'/api/models/{model_name}/aliases/champion/promotions', headers=headers,
        json={'version': 99, 'reason': 'Missing version'},
    )
    blank_reason = client.post(
        f'/api/models/{model_name}/aliases/champion/promotions', headers=headers,
        json={'version': 1, 'reason': ''},
    )
    unsupported_alias = client.post(
        f'/api/models/{model_name}/aliases/unsupported/promotions', headers=headers,
        json={'version': 1, 'reason': 'Unsupported alias'},
    )
    rollback_without_history = client.post(
        f'/api/models/{model_name}/aliases/champion/rollback', headers=headers,
        json={'reason': 'No history'},
    )

    assert rejected_validation.status_code == 422
    assert missing_version.status_code == 404
    assert blank_reason.status_code == 422
    assert unsupported_alias.status_code == 422
    assert rollback_without_history.status_code == 409


def test_model_listing_exposes_lineage_compatibility_and_rejects_corrupt_alias_artifacts(authenticated_client) -> None:
    from pathlib import Path

    client, headers = authenticated_client
    suffix = uuid4().hex
    experiment_id = f'experiment-{suffix}'
    run_id = f'run-{suffix}'
    model_name = f'pcb-classifier-{suffix}'
    client.post('/api/research/experiments', headers=headers, json={'id': experiment_id, 'name': model_name, 'description': ''})
    client.post('/api/research/runs', headers=headers, json={
        'id': run_id, 'experimentId': experiment_id, 'status': 'completed', 'executionTarget': 'local-cpu',
        'codeRevision': '9ae70df', 'nodeVersions': {}, 'environment': {}, 'randomSeeds': {'python': 42},
        'resources': {}, 'datasetVersions': {'boards': 'sha256:' + 'a' * 64}, 'parameters': {},
        'metrics': {'accuracy': 0.99}, 'outputArtifacts': {}, 'error': None,
    })
    artifact = client.post(f'/api/research/runs/{run_id}/artifacts', headers=headers, files={
        'file': ('classifier.bin', b'verified-model', 'application/octet-stream'),
    }).json()
    client.post('/api/models', headers=headers, json={'name': model_name, 'description': 'Verified classifier'})
    version = client.post(f'/api/models/{model_name}/versions', headers=headers, json={
        'runId': run_id, 'artifactId': artifact['id'], 'validationEvidence': {
            'passed': True,
            'compatibility': {'task': 'classification', 'inputSchema': 'features', 'outputSchema': 'label', 'framework': 'python', 'status': 'validated'},
        },
    })
    promoted = client.post(f'/api/models/{model_name}/aliases/champion/promotions', headers=headers, json={'version': 1, 'reason': 'Validated artifact'})
    listed = client.get('/api/models', headers=headers)

    assert version.status_code == 201
    assert promoted.status_code == 201
    entry = next(item for item in listed.json() if item['name'] == model_name)
    assert entry['aliases'] == {'champion': 1}
    assert entry['versions'][0]['artifactVerified'] is True
    assert entry['versions'][0]['compatibility']['inputSchema'] == 'features'

    artifact_path = Path('data/artifacts') / artifact['sha256'][:2] / artifact['sha256']
    original_content = artifact_path.read_bytes()
    try:
        artifact_path.write_bytes(b'corrupt')
        resolved = client.post('/api/models/resolve-production-bindings', headers=headers, json={
            'model': {'modelName': model_name, 'alias': 'champion'},
        })
        assert resolved.status_code == 422
        assert 'integrity' in resolved.json()['detail']
    finally:
        artifact_path.write_bytes(original_content)


def test_model_version_accepts_only_a_valid_external_onnx_contract(authenticated_client) -> None:
    client, headers = authenticated_client
    suffix = uuid4().hex
    experiment_id = f'experiment-{suffix}'
    run_id = f'run-{suffix}'
    model_name = f'onnx-classifier-{suffix}'
    client.post('/api/research/experiments', headers=headers, json={'id': experiment_id, 'name': model_name, 'description': ''})
    client.post('/api/research/runs', headers=headers, json={
        'id': run_id, 'experimentId': experiment_id, 'status': 'completed', 'executionTarget': 'local-cpu',
        'codeRevision': '9ae70df', 'nodeVersions': {}, 'environment': {}, 'randomSeeds': {}, 'resources': {},
        'datasetVersions': {}, 'parameters': {}, 'metrics': {}, 'outputArtifacts': {}, 'error': None,
    })
    artifact = client.post(f'/api/research/runs/{run_id}/artifacts', headers=headers, files={
        'file': ('classifier.onnx', b'external-onnx-artifact', 'application/octet-stream'),
    }).json()
    client.post('/api/models', headers=headers, json={'name': model_name, 'description': 'External ONNX classifier'})
    contract = {
        'format': 'onnx', 'runtime': 'onnxruntime', 'runtimeVersion': '1.18.0',
        'inputSchema': [{'name': 'image', 'dtype': 'float32', 'shape': [1, 3, 224, 224]}],
        'outputSchema': [{'name': 'scores', 'dtype': 'float32', 'shape': [1, 2]}],
        'preprocessing': {'channelOrder': 'RGB'}, 'postprocessing': {'kind': 'classification'},
    }
    version = client.post(f'/api/models/{model_name}/versions', headers=headers, json={
        'runId': run_id, 'artifactId': artifact['id'], 'validationEvidence': {'passed': True}, 'artifactContract': contract,
    })
    invalid = client.post(f'/api/models/{model_name}/versions', headers=headers, json={
        'runId': run_id, 'artifactId': artifact['id'], 'validationEvidence': {'passed': True},
        'artifactContract': {**contract, 'runtime': 'pytorch'},
    })

    assert version.status_code == 201
    assert version.json()['deepLearningContract']['inputSchema'][0]['name'] == 'image'
    assert invalid.status_code == 422
    assert 'Deep-learning artifact contract is invalid' in invalid.json()['detail']


def test_research_api_requires_authentication() -> None:
    with TestClient(app) as client:
        assert client.get('/api/research/runs').status_code == 401
