import hashlib
from pathlib import Path

import cv2
import numpy as np
import pytest

from core.nodes import ArtifactBinding, ModelBinding, NodeExecutionContext
from core.visualization.contracts import ConfusionMatrixPayload, TablePayload
from tests.nodes.test_svm_image_classifier_contract import load_node_module
from tests.nodes.test_svm_image_classifier_features import handle, image, item


def datasets(tmp_path: Path):
    train, test = [], []
    for split, target in (('train', train), ('test', test)):
        for name, label, base in (('cats', 0, 30), ('dogs', 1, 220)):
            for index in range(4):
                path = tmp_path / f'{split}-{name}-{index}.png'
                pixels = np.full((32, 32, 3), base, np.uint8)
                cv2.line(pixels, (index, 0), (31, 31-index), (base + 20) % 255, 2)
                assert cv2.imwrite(str(path), pixels)
                target.append(item(path, f'{name}/{index}.png', name, label))
    return handle(train), handle(test)


def test_train_evaluate_round_trip_and_inference_are_deterministic(tmp_path: Path) -> None:
    module = load_node_module(); training, testing = datasets(tmp_path)
    first = module.train_and_evaluate(training, testing, module.DEFAULT_PARAMETERS)
    second = module.train_and_evaluate(training, testing, module.DEFAULT_PARAMETERS)
    assert first.metrics == second.metrics and 0 <= first.metrics['accuracy'] <= 1
    assert first.confusion_matrix['labels'] == ['cats', 'dogs']
    assert first.confusion_matrix['matrix'] == second.confusion_matrix['matrix']
    assert first.report['schema'] == 'aoi.table.v1'
    assert [column['key'] for column in first.report['columns']] == [
        'label', 'precision', 'recall', 'f1-score', 'support',
    ]
    assert TablePayload.from_mapping(first.report).to_mapping() == first.report
    assert ConfusionMatrixPayload.from_mapping(first.confusion_matrix).to_mapping() == first.confusion_matrix
    assert first.report['rows'] and first.failed_images['items'] == []
    assert first.artifact == second.artifact
    digest = hashlib.sha256(first.artifact).hexdigest()
    loaded = module.load_model_artifact(first.artifact, expected_sha256=digest, trusted=True)
    features, _, _ = module.extract_dataset_features(testing, module.DEFAULT_PARAMETERS)
    assert module.predict(loaded, features).tolist() == first.predictions.tolist()


def test_artifact_and_training_fail_closed(tmp_path: Path) -> None:
    module = load_node_module(); training, testing = datasets(tmp_path)
    result = module.train_and_evaluate(training, testing, module.DEFAULT_PARAMETERS)
    with pytest.raises(ValueError, match='checksum'):
        module.load_model_artifact(result.artifact, expected_sha256='0' * 64, trusted=True)
    with pytest.raises(ValueError, match='trusted'):
        module.load_model_artifact(result.artifact, expected_sha256=hashlib.sha256(result.artifact).hexdigest(), trusted=False)
    with pytest.raises(ValueError, match='artifact'):
        module.load_model_artifact(b'bad', expected_sha256=hashlib.sha256(b'bad').hexdigest(), trusted=True)
    one_class = handle([value for value in training.items if value.class_id == 0], {'cats': 0, 'dogs': 1})
    with pytest.raises(ValueError, match='two classes'):
        module.train_and_evaluate(one_class, testing, module.DEFAULT_PARAMETERS)


def test_contextual_svm_inference_uses_exact_immutable_binding(tmp_path: Path) -> None:
    module = load_node_module(); training, testing = datasets(tmp_path)
    trained = module.train_and_evaluate(training, testing, module.DEFAULT_PARAMETERS)
    digest = hashlib.sha256(trained.artifact).hexdigest()
    binding = ModelBinding('animals-svm', 1, digest)
    artifact = ArtifactBinding(digest, 'application/vnd.aoi.sklearn-pipeline+zip', len(trained.artifact))
    context = NodeExecutionContext(
        models={'animals-svm': binding}, artifacts={'animals-svm': artifact},
        resolve_artifact=lambda requested: trained.artifact if requested == artifact else b'',
    )
    image_path = Path(testing.items[0].path)
    image_pixels = cv2.imread(str(image_path), cv2.IMREAD_COLOR)

    outputs = module.execute_with_context({
        'action': 'infer', 'image': image_pixels,
        'model': {'modelName': 'animals-svm', 'modelVersion': 1, 'artifactSha256': digest},
    }, module.DEFAULT_PARAMETERS, context)

    assert outputs['class-id'] in {0, 1}
    assert outputs['model'] == {'modelName': 'animals-svm', 'modelVersion': 1, 'artifactSha256': digest}


def test_contextual_svm_inference_rejects_mismatched_or_missing_binding(tmp_path: Path) -> None:
    module = load_node_module(); training, testing = datasets(tmp_path)
    trained = module.train_and_evaluate(training, testing, module.DEFAULT_PARAMETERS)
    digest = hashlib.sha256(trained.artifact).hexdigest()
    image_pixels = cv2.imread(str(testing.items[0].path), cv2.IMREAD_COLOR)
    request = {
        'action': 'infer', 'image': image_pixels,
        'model': {'modelName': 'animals-svm', 'modelVersion': 1, 'artifactSha256': digest},
    }

    with pytest.raises(ValueError, match='resolved'):
        module.execute_with_context(request, module.DEFAULT_PARAMETERS, NodeExecutionContext())
    with pytest.raises(ValueError, match='does not match'):
        module.execute_with_context(request, module.DEFAULT_PARAMETERS, NodeExecutionContext(
            models={'animals-svm': ModelBinding('animals-svm', 2, digest)},
        ))