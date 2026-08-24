from pathlib import Path
from types import SimpleNamespace
from io import BytesIO
import json
import zipfile

import cv2
import numpy as np

from app.database import bootstrap as _database_bootstrap  # noqa: F401
from app.services.research_service import ArtifactStore, ResearchRunRecord, build_reproducibility_manifest
from app.services.training_execution_service import TrainingOrchestrator, execute_training_dispatch
from core.nodes import get_node_manifest_registry
from tests.nodes.test_svm_image_classifier_features import handle, item


class Session:
    def __init__(self, run, *, cancel_on_training: bool = False) -> None:
        self.run = run
        self.artifacts = []
        self.cancel_on_training = cancel_on_training
    def get(self, model, identity): return self.run if identity == self.run.id else None
    def scalar(self, statement): return self.run
    def add(self, value): self.artifacts.append(value)
    def flush(self): pass
    def commit(self):
        if self.cancel_on_training and self.run.status == 'training':
            self.run.status = 'cancelling'
    def rollback(self): self.artifacts.clear()


def datasets(tmp_path: Path, *, one_class: bool = False):
    values = [('cats', 0, 30)] if one_class else [('cats', 0, 30), ('dogs', 1, 220)]
    handles = []
    for role in ('train', 'test'):
        items = []
        for name, label, base in values:
            for index in range(3):
                path = tmp_path / f'{role}-{name}-{index}.png'
                pixels = np.full((32, 32, 3), base, np.uint8)
                cv2.circle(pixels, (8 + index * 4, 16), 4, (base + 20) % 255, -1)
                assert cv2.imwrite(str(path), pixels)
                items.append(item(path, f'{name}/{index}.png', name, label))
        handles.append(handle(items))
    return handles


def dispatch(tmp_path: Path, *, one_class: bool = False):
    training, testing = datasets(tmp_path, one_class=one_class)
    manifest = get_node_manifest_registry()['svm-image-classifier']
    parameters = {parameter.key: parameter.default_value for parameter in manifest.definition.parameters}
    return SimpleNamespace(
        run_id='run-svm', node_id='svm-image-classifier', action_name='train',
        datasets={'training-dataset': training, 'test-dataset': testing}, parameters=parameters,
    )


def run_record():
    return SimpleNamespace(id='run-svm', status='queued', action_name='train', progress=None,
                           metrics={}, output_artifacts={}, error=None, completed_at=None)


def test_svm_dispatch_completes_with_verified_lineage_artifacts(tmp_path: Path) -> None:
    run = run_record(); session = Session(run)
    store = ArtifactStore(tmp_path / 'artifacts')
    completed = TrainingOrchestrator(store).execute(
        session, dispatch(tmp_path), execute_training_dispatch,
    )
    assert completed.status == 'completed'
    assert 0 <= completed.metrics['accuracy'] <= 1
    assert set(completed.output_artifacts) == {'model', 'report', 'confusion-matrix', 'failed-images'}
    assert all(len(value['sha256']) == 64 for value in completed.output_artifacts.values())
    assert 'path' not in str(completed.output_artifacts).lower()
    model_record = next(artifact for artifact in session.artifacts if artifact.name == 'model')
    model_content = store.read_verified(SimpleNamespace(
        storage_uri=model_record.storage_uri, sha256=model_record.sha256,
        byte_length=model_record.byte_length,
    ))
    with zipfile.ZipFile(BytesIO(model_content)) as archive:
        metadata = json.loads(archive.read('metadata.json'))
    assert metadata['schema'] == 'aoi.sklearn-pipeline.v1'
    assert metadata['nodeId'] == 'svm-image-classifier'
    assert metadata['datasets'] == [
        {'datasetId': 'animals', 'role': 'training', 'version': 'sha256:' + 'a' * 64},
        {'datasetId': 'animals', 'role': 'test', 'version': 'sha256:' + 'a' * 64},
    ]
    structured_records = {
        artifact.name: artifact for artifact in session.artifacts
        if artifact.name in {'report', 'confusion-matrix'}
    }
    report = json.loads(store.read_verified(SimpleNamespace(
        storage_uri=structured_records['report'].storage_uri,
        sha256=structured_records['report'].sha256,
        byte_length=structured_records['report'].byte_length,
    )))
    confusion = json.loads(store.read_verified(SimpleNamespace(
        storage_uri=structured_records['confusion-matrix'].storage_uri,
        sha256=structured_records['confusion-matrix'].sha256,
        byte_length=structured_records['confusion-matrix'].byte_length,
    )))
    assert report['schema'] == 'aoi.table.v1'
    assert report['columns'][0] == {'key': 'label', 'label': 'Label', 'type': 'string'}
    assert confusion['schema'] == 'aoi.confusion-matrix.v1'
    assert completed.output_artifacts['report']['mediaType'] == 'application/json'
    assert 'storage' not in str(completed.output_artifacts).lower()
    reproducibility = build_reproducibility_manifest(ResearchRunRecord(
        run_id='run-svm', experiment_id='animals-svm', code_revision='test-revision',
        node_versions={'svm-image-classifier': '1.0.0'}, environment={'python': 'test'},
        random_seeds={'python': 42, 'numpy': 42}, resources={'executionTarget': 'local-cpu'},
        dataset_versions={item['role']: item['version'] for item in metadata['datasets']},
        parameters=metadata['parameters'], metrics=completed.metrics,
        output_artifacts={name: value['sha256'] for name, value in completed.output_artifacts.items()},
        status='completed', error=None,
    ))
    assert reproducibility['runId'] == 'run-svm'
    assert reproducibility['nodeVersions'] == {'svm-image-classifier': '1.0.0'}
    assert reproducibility['metrics'] == completed.metrics
    assert reproducibility['outputArtifacts']['model'] == model_record.sha256


def test_svm_dispatch_persists_safe_failure_for_one_class_dataset(tmp_path: Path) -> None:
    run = run_record(); session = Session(run)
    failed = TrainingOrchestrator(ArtifactStore(tmp_path / 'artifacts')).execute(
        session, dispatch(tmp_path, one_class=True), execute_training_dispatch,
    )
    assert failed.status == 'failed'
    assert failed.error == 'Training action failed. Review server diagnostics before retrying.'
    assert failed.output_artifacts == {}


def test_svm_dispatch_observes_cancellation_inside_node_boundary(tmp_path: Path) -> None:
    run = run_record(); session = Session(run, cancel_on_training=True)
    cancelled = TrainingOrchestrator(ArtifactStore(tmp_path / 'artifacts')).execute(
        session, dispatch(tmp_path), execute_training_dispatch,
    )
    assert cancelled.status == 'cancelled'
    assert cancelled.output_artifacts == {}