from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config.settings import get_settings
from app.database.session import SessionLocal
from app.main import app
from app.models.research import ModelAlias, ModelRegistryEntry, ModelVersion, ResearchExperiment, ResearchRun


@pytest.fixture
def authenticated_client():
    with TestClient(app) as client:
        settings = get_settings()
        login = client.post('/api/auth/login', json={'email': settings.seed_admin_email, 'password': settings.seed_admin_password})
        yield client, {'Authorization': f"Bearer {login.json()['accessToken']}"}


def seed_completed_run(
    experiment_id: str,
    run_id: str,
    *,
    node_versions: dict[str, str] | None = None,
    environment: dict | None = None,
    random_seeds: dict[str, int] | None = None,
    resources: dict | None = None,
    dataset_versions: dict | None = None,
    parameters: dict | None = None,
    metrics: dict[str, float] | None = None,
) -> None:
    """Seed server-owned completed evidence without exercising the disabled client write API."""
    with SessionLocal() as session:
        experiment = session.get(ResearchExperiment, experiment_id)
        assert experiment is not None
        session.add(ResearchRun(
            id=run_id, experiment_id=experiment_id, status='completed', execution_target='local-cpu',
            code_revision='9ae70df', node_versions=node_versions or {}, environment=environment or {},
            random_seeds=random_seeds or {}, resources=resources or {},
            dataset_versions=dataset_versions or {}, parameters=parameters or {}, metrics=metrics or {},
            output_artifacts={}, error=None, created_by=experiment.created_by,
        ))
        session.commit()


def test_research_run_search_and_reproducibility_export(authenticated_client) -> None:
    client, headers = authenticated_client
    suffix = uuid4().hex
    experiment_id = f'experiment-{suffix}'
    run_id = f'run-{suffix}'

    experiment = client.post('/api/research/experiments', headers=headers, json={
        'id': experiment_id, 'name': 'PCB anomaly baseline', 'description': 'Deterministic baseline',
    })
    seed_completed_run(
        experiment_id, run_id, node_versions={'patchcore': '1.0.0'}, environment={'python': '3.12'},
        random_seeds={'python': 42}, resources={'cpuCores': 4},
        dataset_versions={'pcb-train': 'sha256:' + 'a' * 64},
        parameters={'memoryBankSize': 10000}, metrics={'auroc': 0.98},
    )
    search = client.get('/api/research/runs?query=PCB%20anomaly', headers=headers)
    search_by_experiment_id = client.get(f'/api/research/runs?query={experiment_id}', headers=headers)
    search_by_code_revision = client.get('/api/research/runs?query=9AE70DF', headers=headers)
    search_by_execution_target = client.get('/api/research/runs?query=LOCAL-CPU', headers=headers)
    no_match = client.get('/api/research/runs?query=no-such-research-run', headers=headers)
    manifest = client.get(f'/api/research/runs/{run_id}/reproducibility-manifest', headers=headers)

    assert experiment.status_code == 201
    assert any(item['id'] == run_id for item in search.json())
    assert any(item['id'] == run_id for item in search_by_experiment_id.json())
    assert any(item['id'] == run_id for item in search_by_code_revision.json())
    assert any(item['id'] == run_id for item in search_by_execution_target.json())
    assert all(item['id'] != run_id for item in no_match.json())
    assert manifest.json()['codeRevision'] == '9ae70df'
    assert manifest.json()['randomSeeds'] == {'python': 42}


def test_model_registration_promotion_and_rollback_are_persisted(authenticated_client) -> None:
    client, headers = authenticated_client
    suffix = uuid4().hex
    experiment_id = f'experiment-{suffix}'
    run_id = f'run-{suffix}'
    model_name = f'pcb-anomaly-{suffix}'
    client.post('/api/research/experiments', headers=headers, json={'id': experiment_id, 'name': model_name, 'description': ''})
    seed_completed_run(experiment_id, run_id, random_seeds={'python': 42}, metrics={'auroc': 0.98})
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
    preview = client.get(f'/api/v1/models/{model_name}/aliases/champion/rollback-preview', headers=headers)
    rollback = client.post(f'/api/v1/models/{model_name}/aliases/champion/rollback', headers=headers, json={
        'reason': 'Pilot regression', 'previewEventId': preview.json()['previewEventId'],
    })
    events = client.get(f'/api/v1/models/{model_name}/events', headers=headers)

    assert model.status_code == 201
    assert version_1.json()['version'] == 1 and version_2.json()['version'] == 2
    assert first.json()['nextVersion'] == 1
    assert second.json()['previousVersion'] == 1
    assert preview.json() == {
        'alias': 'champion', 'currentVersion': 2, 'targetVersion': 1,
        'previewEventId': second.json()['id'],
    }
    assert rollback.json()['nextVersion'] == 1
    assert [event['action'] for event in events.json()] == ['rollback', 'promote', 'promote']
    assert [event['id'] for event in events.json()] == sorted(
        [event['id'] for event in events.json()], reverse=True,
    )
    assert events.json()[0]['actor']['email'] == get_settings().seed_admin_email
    assert events.json()[0]['reason'] == 'Pilot regression'
    assert events.json()[0]['createdAt']
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
    seed_completed_run(experiment_id, run_id)
    artifact = client.post(f'/api/research/runs/{run_id}/artifacts', headers=headers, files={
        'file': ('weights.bin', b'lifecycle-model', 'application/octet-stream'),
    }).json()
    client.post('/api/models', headers=headers, json={'name': model_name, 'description': ''})
    rejected_validation = client.post(f'/api/models/{model_name}/versions', headers=headers, json={
        'runId': run_id, 'artifactId': artifact['id'], 'validationEvidence': {'passed': False},
    })
    accepted_version = client.post(f'/api/models/{model_name}/versions', headers=headers, json={
        'runId': run_id, 'artifactId': artifact['id'], 'validationEvidence': {'passed': True},
    })
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
    rollback_alias = client.post(
        f'/api/models/{model_name}/aliases/rollback/promotions', headers=headers,
        json={'version': 1, 'reason': 'Rollback is not an alias'},
    )
    rollback_without_history = client.get(
        f'/api/v1/models/{model_name}/aliases/champion/rollback-preview', headers=headers,
    )

    assert rejected_validation.status_code == 422
    assert accepted_version.status_code == 201
    assert missing_version.status_code == 404
    assert blank_reason.status_code == 422
    assert unsupported_alias.status_code == 422
    assert rollback_alias.status_code == 422
    assert rollback_without_history.status_code == 409


def test_model_rollback_rejects_a_stale_preview(authenticated_client) -> None:
    client, headers = authenticated_client
    suffix = uuid4().hex
    experiment_id = f'experiment-{suffix}'
    run_id = f'run-{suffix}'
    model_name = f'pcb-stale-rollback-{suffix}'
    client.post('/api/research/experiments', headers=headers, json={'id': experiment_id, 'name': model_name, 'description': ''})
    seed_completed_run(experiment_id, run_id)
    artifacts = [client.post(f'/api/research/runs/{run_id}/artifacts', headers=headers, files={
        'file': (f'weights-{index}.bin', f'model-{index}'.encode(), 'application/octet-stream'),
    }).json() for index in range(1, 4)]
    client.post('/api/models', headers=headers, json={'name': model_name, 'description': ''})
    for artifact in artifacts:
        client.post(f'/api/models/{model_name}/versions', headers=headers, json={
            'runId': run_id, 'artifactId': artifact['id'], 'validationEvidence': {'passed': True},
        })
    for version in (1, 2):
        client.post(f'/api/models/{model_name}/aliases/champion/promotions', headers=headers, json={
            'version': version, 'reason': f'Promote version {version}',
        })
    stale_preview = client.get(f'/api/v1/models/{model_name}/aliases/champion/rollback-preview', headers=headers).json()
    client.post(f'/api/models/{model_name}/aliases/champion/promotions', headers=headers, json={
        'version': 3, 'reason': 'Alias changed after preview',
    })

    stale = client.post(f'/api/v1/models/{model_name}/aliases/champion/rollback', headers=headers, json={
        'reason': 'Use stale preview', 'previewEventId': stale_preview['previewEventId'],
    })

    assert stale.status_code == 409
    assert 'preview is stale' in stale.json()['detail']


def test_model_rollback_revalidates_target_artifact_integrity(authenticated_client) -> None:
    from pathlib import Path

    client, headers = authenticated_client
    suffix = uuid4().hex
    experiment_id = f'experiment-{suffix}'
    run_id = f'run-{suffix}'
    model_name = f'pcb-integrity-rollback-{suffix}'
    client.post('/api/research/experiments', headers=headers, json={'id': experiment_id, 'name': model_name, 'description': ''})
    seed_completed_run(experiment_id, run_id)
    artifacts = [client.post(f'/api/research/runs/{run_id}/artifacts', headers=headers, files={
        'file': (f'weights-{index}.bin', f'model-{index}'.encode(), 'application/octet-stream'),
    }).json() for index in (1, 2)]
    client.post('/api/v1/models', headers=headers, json={'name': model_name, 'description': ''})
    for artifact in artifacts:
        client.post(f'/api/v1/models/{model_name}/versions', headers=headers, json={
            'runId': run_id, 'artifactId': artifact['id'], 'validationEvidence': {'passed': True},
        })
    for version in (1, 2):
        client.post(f'/api/v1/models/{model_name}/aliases/champion/promotions', headers=headers, json={
            'version': version, 'reason': f'Promote version {version}',
        })
    preview = client.get(f'/api/v1/models/{model_name}/aliases/champion/rollback-preview', headers=headers).json()
    target_path = Path('data/artifacts') / artifacts[0]['sha256'][:2] / artifacts[0]['sha256']
    original = target_path.read_bytes()
    try:
        target_path.write_bytes(b'corrupt')
        response = client.post(f'/api/v1/models/{model_name}/aliases/champion/rollback', headers=headers, json={
            'reason': 'Restore version one', 'previewEventId': preview['previewEventId'],
        })
        assert response.status_code == 422
        assert 'integrity' in response.json()['detail']
    finally:
        target_path.write_bytes(original)


def test_model_listing_rejects_persisted_rollback_alias(authenticated_client) -> None:
    client, headers = authenticated_client
    with SessionLocal() as session:
        stale_aliases = list(session.scalars(
            select(ModelAlias)
            .join(ModelRegistryEntry, ModelAlias.model_id == ModelRegistryEntry.id)
            .where(ModelAlias.alias == 'rollback', ModelRegistryEntry.name.like('pcb-invalid-alias-%'))
        ))
        for stale_alias in stale_aliases:
            session.delete(stale_alias)
        session.commit()
    suffix = uuid4().hex
    experiment_id = f'experiment-{suffix}'
    run_id = f'run-{suffix}'
    model_name = f'pcb-invalid-alias-{suffix}'
    client.post('/api/research/experiments', headers=headers, json={'id': experiment_id, 'name': model_name, 'description': ''})
    seed_completed_run(experiment_id, run_id)
    artifact = client.post(f'/api/research/runs/{run_id}/artifacts', headers=headers, files={
        'file': ('weights.bin', b'invalid-alias-model', 'application/octet-stream'),
    }).json()
    client.post('/api/models', headers=headers, json={'name': model_name, 'description': ''})
    client.post(f'/api/models/{model_name}/versions', headers=headers, json={
        'runId': run_id, 'artifactId': artifact['id'], 'validationEvidence': {'passed': True},
    })
    invalid_alias_id: int | None = None
    with SessionLocal() as session:
        model = session.scalar(select(ModelRegistryEntry).where(ModelRegistryEntry.name == model_name))
        assert model is not None
        version = session.scalar(select(ModelVersion).where(ModelVersion.model_id == model.id))
        assert version is not None
        invalid_alias = ModelAlias(model_id=model.id, alias='rollback', model_version_id=version.id)
        session.add(invalid_alias)
        session.commit()
        session.refresh(invalid_alias)
        invalid_alias_id = invalid_alias.id

    try:
        listed = client.get('/api/models', headers=headers)
        assert listed.status_code == 422
        assert 'unsupported persisted alias' in listed.json()['detail']
    finally:
        with SessionLocal() as session:
            invalid_alias = session.get(ModelAlias, invalid_alias_id)
            if invalid_alias is not None:
                session.delete(invalid_alias)
                session.commit()


def test_model_listing_exposes_lineage_compatibility_and_rejects_corrupt_alias_artifacts(authenticated_client) -> None:
    from pathlib import Path

    client, headers = authenticated_client
    suffix = uuid4().hex
    experiment_id = f'experiment-{suffix}'
    run_id = f'run-{suffix}'
    model_name = f'pcb-classifier-{suffix}'
    client.post('/api/research/experiments', headers=headers, json={'id': experiment_id, 'name': model_name, 'description': ''})
    seed_completed_run(
        experiment_id, run_id, random_seeds={'python': 42},
        dataset_versions={'boards': 'sha256:' + 'a' * 64}, metrics={'accuracy': 0.99},
    )
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
    assert entry['versions'][0]['createdAt']

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
    seed_completed_run(experiment_id, run_id)
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


def test_model_registration_requires_completed_run_and_passed_validation(authenticated_client) -> None:
    client, headers = authenticated_client
    suffix = uuid4().hex
    experiment_id = f'experiment-{suffix}'
    completed_run_id = f'run-completed-{suffix}'
    running_run_id = f'run-running-{suffix}'
    model_name = f'registration-{suffix}'
    client.post('/api/research/experiments', headers=headers, json={
        'id': experiment_id, 'name': model_name, 'description': '',
    })
    seed_completed_run(experiment_id, completed_run_id)
    seed_completed_run(experiment_id, running_run_id)
    with SessionLocal() as session:
        running_run = session.get(ResearchRun, running_run_id)
        assert running_run is not None
        running_run.status = 'training'
        session.commit()
    completed_artifact = client.post(
        f'/api/research/runs/{completed_run_id}/artifacts', headers=headers,
        files={'file': ('completed.bin', b'completed-model', 'application/octet-stream')},
    ).json()
    running_artifact = client.post(
        f'/api/research/runs/{running_run_id}/artifacts', headers=headers,
        files={'file': ('running.bin', b'running-model', 'application/octet-stream')},
    ).json()
    assert client.post('/api/v1/models', headers=headers, json={
        'name': model_name, 'description': '',
    }).status_code == 201

    incomplete = client.post(f'/api/v1/models/{model_name}/versions', headers=headers, json={
        'runId': running_run_id,
        'artifactId': running_artifact['id'],
        'validationEvidence': {'passed': True},
    })
    failed_validation = client.post(f'/api/v1/models/{model_name}/versions', headers=headers, json={
        'runId': completed_run_id,
        'artifactId': completed_artifact['id'],
        'validationEvidence': {'passed': False},
    })

    assert incomplete.status_code == 422
    assert 'completed' in incomplete.json()['detail']
    assert failed_validation.status_code == 422
    assert 'validation' in failed_validation.json()['detail'].lower()


def test_run_artifact_listing_exposes_safe_registration_metadata(authenticated_client) -> None:
    client, headers = authenticated_client
    suffix = uuid4().hex
    experiment_id = f'experiment-{suffix}'
    run_id = f'run-{suffix}'
    client.post('/api/research/experiments', headers=headers, json={
        'id': experiment_id, 'name': experiment_id, 'description': '',
    })
    seed_completed_run(experiment_id, run_id)
    created = client.post(f'/api/research/runs/{run_id}/artifacts', headers=headers, files={
        'file': ('classifier.bin', b'verified-model', 'application/octet-stream'),
    }).json()

    response = client.get(f'/api/v1/research/runs/{run_id}/artifacts', headers=headers)

    assert response.status_code == 200
    assert response.json() == [{
        'id': created['id'],
        'runId': run_id,
        'name': 'classifier.bin',
        'sha256': created['sha256'],
        'mediaType': 'application/octet-stream',
        'byteLength': len(b'verified-model'),
        'verified': True,
    }]
    assert 'storageUri' not in response.text


def test_research_api_requires_authentication() -> None:
    with TestClient(app) as client:
        assert client.get('/api/research/runs').status_code == 401
        assert client.get('/api/v1/research/runs/private-run/artifacts').status_code == 401
        assert client.post('/api/models', json={'name': 'private-model', 'description': ''}).status_code == 401
