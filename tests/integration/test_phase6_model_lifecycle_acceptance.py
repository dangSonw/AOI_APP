import hashlib
from pathlib import Path
from uuid import uuid4

import cv2
from fastapi.testclient import TestClient

from app.config.settings import get_settings
from app.database.session import SessionLocal
from app.main import app
from app.models.research import ResearchExperiment, ResearchRun
from core.nodes import ArtifactBinding, ModelBinding, NodeExecutionContext
from tests.integration.test_svm_training_flow import datasets
from tests.nodes.test_svm_image_classifier_contract import load_node_module


def test_phase6_training_registration_champion_inference_and_viewer_journey(tmp_path: Path) -> None:
    module = load_node_module()
    training, testing = datasets(tmp_path)
    trained = module.train_and_evaluate(training, testing, module.DEFAULT_PARAMETERS)
    model_sha256 = hashlib.sha256(trained.artifact).hexdigest()
    suffix = uuid4().hex
    experiment_id = f'animals-svm-{suffix}'
    run_id = f'run-svm-{suffix}'
    model_name = f'animals-svm-{suffix}'

    with TestClient(app) as client:
        settings = get_settings()
        login = client.post('/api/auth/login', json={
            'email': settings.seed_admin_email,
            'password': settings.seed_admin_password,
        })
        headers = {'Authorization': f"Bearer {login.json()['accessToken']}"}
        with SessionLocal() as session:
            user_id = int(login.json()['user']['id'])
            session.add(ResearchExperiment(
                id=experiment_id, name='Deterministic animals SVM', description='', created_by=user_id,
            ))
            session.flush()
            session.add(ResearchRun(
                id=run_id, experiment_id=experiment_id, status='completed', execution_target='local-cpu',
                code_revision='phase6-acceptance', node_versions={'svm-image-classifier': '1.0.0'},
                environment={}, random_seeds={'python': 42, 'numpy': 42}, resources={'cpuCores': 2},
                dataset_versions={'training': training.version, 'test': testing.version},
                parameters=dict(module.DEFAULT_PARAMETERS), metrics=trained.metrics,
                output_artifacts={'model': model_sha256}, error=None, created_by=user_id,
            ))
            session.commit()

        artifact = client.post(
            f'/api/research/runs/{run_id}/artifacts', headers=headers,
            files={'file': ('model.zip', trained.artifact, 'application/vnd.aoi.sklearn-pipeline+zip')},
        )
        model = client.post('/api/v1/models', headers=headers, json={
            'name': model_name, 'description': 'Phase 6 deterministic acceptance model',
        })
        version = client.post(f'/api/v1/models/{model_name}/versions', headers=headers, json={
            'runId': run_id,
            'artifactId': artifact.json()['id'],
            'validationEvidence': {'passed': True, 'accuracy': trained.metrics['accuracy']},
        })
        champion = client.post(
            f'/api/v1/models/{model_name}/aliases/champion/promotions', headers=headers,
            json={'version': 1, 'reason': 'Phase 6 deterministic validation passed'},
        )
        resolved = client.post('/api/models/resolve-production-bindings', headers=headers, json={
            'model': {'modelName': model_name, 'alias': 'champion'},
        })

    assert artifact.status_code == model.status_code == version.status_code == champion.status_code == 201
    assert artifact.json()['sha256'] == model_sha256
    immutable = resolved.json()['model']
    assert immutable == {'modelName': model_name, 'modelVersion': 1, 'artifactSha256': model_sha256}
    binding = ModelBinding.from_mapping(immutable)
    artifact_binding = ArtifactBinding(
        model_sha256, 'application/vnd.aoi.sklearn-pipeline+zip', len(trained.artifact),
    )
    context = NodeExecutionContext(
        models={model_name: binding}, artifacts={model_name: artifact_binding},
        resolve_artifact=lambda requested: trained.artifact if requested == artifact_binding else b'',
    )
    inference = module.execute_with_context({
        'action': 'infer',
        'image': cv2.imread(str(testing.items[0].path), cv2.IMREAD_COLOR),
        'model': immutable,
    }, module.DEFAULT_PARAMETERS, context)

    assert inference['class-id'] == int(trained.predictions[0])
    assert inference['model'] == immutable
    assert trained.report['schema'] == 'aoi.table.v1'
    assert trained.confusion_matrix['schema'] == 'aoi.confusion-matrix.v1'