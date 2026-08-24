from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.training_jobs import get_training_artifact_store, get_training_platform
from app.config.settings import get_settings
from app.main import app
from app.services.training_job_service import TrainingJobDispatch, TrainingPlatform
from app.services.research_service import ArtifactStore
from app.models.research import ResearchArtifact, ResearchExperiment, ResearchRun
from core.algorithms.models import AlgorithmActionDefinition, AlgorithmDefinition
from core.nodes.models import NodeManifest, NodeUse
from core.pipeline.models import Point, Workflow, WorkflowNode


def test_training_job_routes_require_authentication() -> None:
    with TestClient(app) as client:
        assert client.post('/api/v1/research/training-jobs', json={}).status_code == 401
        assert client.get('/api/v1/research/training-jobs/missing').status_code == 401
        assert client.post('/api/v1/research/training-jobs/missing/cancellations').status_code == 401
        assert client.get('/api/v1/research/artifacts/1').status_code == 401


def test_authenticated_artifact_read_reverifies_content_without_exposing_storage_uri(tmp_path) -> None:
    store = ArtifactStore(tmp_path / 'artifacts')
    stored = store.put_bytes(b'{"schema":"aoi.table.v1"}', media_type='application/json')
    with TestClient(app) as client:
        settings = get_settings()
        login = client.post('/api/auth/login', json={'email': settings.seed_admin_email, 'password': settings.seed_admin_password})
        headers = {'Authorization': f"Bearer {login.json()['accessToken']}"}
        from app.database.session import SessionLocal
        experiment_id = f'artifact-api-{uuid4().hex}'
        run_id = f'run-{uuid4().hex}'
        created = client.post('/api/research/experiments', headers=headers, json={
            'id': experiment_id, 'name': 'Artifact API', 'description': '',
        })
        with SessionLocal() as session:
            experiment = session.get(ResearchExperiment, experiment_id)
            session.add(ResearchRun(
                id=run_id, experiment_id=experiment_id, status='completed', execution_target='local-cpu',
                code_revision='test', node_versions={}, environment={}, random_seeds={}, resources={},
                dataset_versions={}, parameters={}, metrics={}, output_artifacts={}, created_by=experiment.created_by,
            ))
            session.flush()
            artifact = ResearchArtifact(run_id=run_id, name='table', sha256=stored.sha256, media_type=stored.media_type, byte_length=stored.byte_length, storage_uri=stored.storage_uri)
            session.add(artifact); session.commit(); session.refresh(artifact); artifact_id = artifact.id
        app.dependency_overrides[get_training_artifact_store] = lambda: store
        try:
            read = client.get(f'/api/v1/research/artifacts/{artifact_id}', headers=headers)
            missing = client.get('/api/v1/research/artifacts/999999999', headers=headers)
            Path(stored.storage_uri).write_bytes(b'corrupt')
            corrupt = client.get(f'/api/v1/research/artifacts/{artifact_id}', headers=headers)
        finally:
            app.dependency_overrides.pop(get_training_artifact_store, None)
    assert created.status_code == 201
    assert read.status_code == 200 and read.content == b'{"schema":"aoi.table.v1"}'
    assert read.headers['content-type'].startswith('application/json')
    assert str(tmp_path).encode() not in read.content
    assert missing.status_code == 404
    assert corrupt.status_code == 409
    assert 'checksum' in corrupt.json()['detail'].lower()


def test_legacy_run_creation_rejects_client_authored_results() -> None:
    with TestClient(app) as client:
        settings = get_settings()
        login = client.post('/api/auth/login', json={
            'email': settings.seed_admin_email, 'password': settings.seed_admin_password,
        })
        response = client.post('/api/research/runs', headers={
            'Authorization': f"Bearer {login.json()['accessToken']}",
        }, json={
            'id': 'client-authored-run', 'experimentId': 'missing', 'status': 'completed',
            'executionTarget': 'local-cpu', 'codeRevision': 'client', 'nodeVersions': {},
            'environment': {}, 'randomSeeds': {}, 'resources': {}, 'datasetVersions': {},
            'parameters': {}, 'metrics': {'forged': 1}, 'outputArtifacts': {}, 'error': None,
        })

    assert response.status_code == 410
    assert 'Client-authored research results are disabled' in response.json()['detail']


def test_authenticated_training_job_create_read_and_cancel_round_trip() -> None:
    suffix = uuid4().hex
    experiment_id = f'training-api-{suffix}'
    node_id = 'fake-api-trainer'
    node_instance_id = f'node-{suffix}'
    action = AlgorithmActionDefinition(
        dataset_inputs=('training-dataset',), execution_targets=('local-cpu',), cancellable=True,
    )
    definition = AlgorithmDefinition(
        id=node_id, name='Fake API trainer', description='', category='Research',
        documentation_group='research', inputs=(), outputs=(), manifest_version=2,
        package_version='1.0.0', capabilities=('train',), actions=MappingProxyType({'train': action}),
    )
    manifest = NodeManifest(
        manifest_version=2, catalog_order=1, package_version='1.0.0', id=node_id,
        use=NodeUse.RELEASE, execution_target='local-cpu', capabilities=('train',),
        resource_hints={}, artifact_contracts={}, parameter_migration_hooks=(),
        inspector_kind='generic', custom_inspector_key=None, definition=definition,
        actions=MappingProxyType({'train': action}),
    )
    workflow = Workflow(
        recipe_slug='rev-c-mainboard', recipe_name='Recipe', version=2, revision=4,
        updated_at=datetime.now(timezone.utc), connections=(), execution_order=(node_instance_id,),
        nodes=(WorkflowNode(node_instance_id, node_id, 'Trainer', Point(0, 0), {}, ()),),
    )
    dispatched: list[TrainingJobDispatch] = []
    platform = TrainingPlatform(
        manifest_registry=lambda: {node_id: manifest}, workflow_reader=lambda _: workflow,
        dataset_resolver=lambda binding: SimpleNamespace(
            dataset_id=binding.dataset_id, version=binding.version, items=(),
        ),
        dispatcher=dispatched.append, code_revision=lambda: 'server-owned-revision',
    )
    app.dependency_overrides[get_training_platform] = lambda: platform
    try:
        with TestClient(app) as client:
            settings = get_settings()
            login = client.post('/api/auth/login', json={
                'email': settings.seed_admin_email, 'password': settings.seed_admin_password,
            })
            headers = {'Authorization': f"Bearer {login.json()['accessToken']}"}
            experiment = client.post('/api/research/experiments', headers=headers, json={
                'id': experiment_id, 'name': 'Fake training API', 'description': '',
            })
            created = client.post('/api/v1/research/training-jobs', headers=headers, json={
                'experimentId': experiment_id, 'recipeSlug': 'rev-c-mainboard',
                'workflowRevision': 4, 'nodeInstanceId': node_instance_id, 'nodeId': node_id,
                'nodePackageVersion': '1.0.0', 'actionName': 'train',
                'executionTarget': 'local-cpu',
                'datasetBindings': {'training-dataset': {
                    'datasetId': 'images', 'version': 'sha256:' + 'a' * 64,
                }},
                'parameters': {}, 'randomSeeds': {'python': 42},
            })
            run_id = created.json()['id']
            read = client.get(f'/api/v1/research/training-jobs/{run_id}', headers=headers)
            cancelled = client.post(
                f'/api/v1/research/training-jobs/{run_id}/cancellations', headers=headers,
            )
            duplicate = client.post(
                f'/api/v1/research/training-jobs/{run_id}/cancellations', headers=headers,
            )
    finally:
        app.dependency_overrides.pop(get_training_platform, None)

    assert experiment.status_code == 201
    assert created.status_code == 201
    assert created.json()['codeRevision'] == 'server-owned-revision'
    assert created.json()['status'] == 'queued'
    assert read.status_code == 200 and read.json()['id'] == run_id
    assert cancelled.status_code == 200 and cancelled.json()['status'] == 'cancelled'
    assert duplicate.status_code == 409
    assert len(dispatched) == 1 and dispatched[0].run_id == run_id
    assert 'path' not in str(created.json()).lower()