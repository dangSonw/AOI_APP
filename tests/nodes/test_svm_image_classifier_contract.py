import importlib.util
import json
from pathlib import Path

import pytest

from core.nodes import NodeNotImplementedError, get_node_manifest_registry, get_node_registry


PACKAGE = Path('core/nodes/classification/svm-image-classifier')


def load_node_module():
    path = PACKAGE / 'node.py'
    spec = importlib.util.spec_from_file_location('test_svm_image_classifier_node', path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_svm_manifest_runtime_actions_and_artifacts_have_exact_parity() -> None:
    manifest = get_node_manifest_registry()['svm-image-classifier']
    runtime = get_node_registry()['svm-image-classifier']

    assert manifest.id == runtime.id == 'svm-image-classifier'
    assert manifest.package_version == '1.0.0'
    assert manifest.execution_target == 'local-cpu'
    assert manifest.custom_inspector_key == 'svm-image-classifier'
    assert set(manifest.actions) == {'train', 'evaluate', 'infer', 'export'}
    assert all(action.cancellable for action in manifest.actions.values())
    assert manifest.actions['train'].dataset_inputs == ('training-dataset', 'test-dataset')
    assert {
        item.key: item.schema for item in manifest.artifact_contracts['outputs']
    } == {
        'model': 'aoi.sklearn-pipeline.v1',
        'metrics': 'aoi.classification-metrics.v1',
        'report': 'aoi.table.v1',
        'confusion-matrix': 'aoi.confusion-matrix.v1',
        'failed-images': 'aoi.failed-images.v1',
    }
    assert runtime.input_keys == runtime.output_keys == ()


def test_svm_defaults_preserve_script_intent_and_documentation_is_bilingual() -> None:
    manifest = get_node_manifest_registry()['svm-image-classifier']
    defaults = {parameter.key: parameter.default_value for parameter in manifest.definition.parameters}

    assert defaults['imageWidth'] == defaults['imageHeight'] == 128
    assert defaults['hogBlockWidth'] == defaults['hogBlockHeight'] == 16
    assert defaults['hogBlockStrideX'] == defaults['hogBlockStrideY'] == 8
    assert defaults['hogCellWidth'] == defaults['hogCellHeight'] == 8
    assert defaults['hogBins'] == 9
    assert defaults['useScaler'] is True
    assert defaults['kernel'] == 'rbf'
    assert defaults['c'] == 10
    assert defaults['gamma'] == 'scale'

    metadata = json.loads((PACKAGE / 'documentation.json').read_text(encoding='utf-8'))
    assert metadata['documentationVersion'] == 1
    assert 'svm-image-classifier' in metadata['en']['overview']
    assert 'svm-image-classifier' in metadata['vi']['overview']
    assert '## Node structure' in (PACKAGE / 'README.md').read_text(encoding='utf-8')
    assert '## Cấu trúc node' in (PACKAGE / 'README.md.vn').read_text(encoding='utf-8')


def test_svm_parameter_validation_rejects_invalid_hog_geometry_kernel_and_target() -> None:
    module = load_node_module()
    defaults = module.DEFAULT_PARAMETERS

    assert module.validate_parameters(defaults, execution_target='local-cpu') == defaults
    invalid_cases = [
        ({**defaults, 'imageWidth': 0}, 'positive'),
        ({**defaults, 'hogBlockWidth': 15}, 'divisible'),
        ({**defaults, 'hogBlockStrideX': 7}, 'stride'),
        ({**defaults, 'hogCellWidth': 6}, 'cell'),
        ({**defaults, 'hogWindowWidth': 64, 'imageWidth': 128}, 'window'),
        ({**defaults, 'c': 0}, 'C'),
        ({**defaults, 'kernel': 'linear', 'gamma': 0.1}, 'gamma'),
        ({**defaults, 'kernel': 'rbf', 'degree': 4}, 'degree'),
        ({**defaults, 'maxSamples': 100_001}, 'samples'),
    ]
    for parameters, message in invalid_cases:
        with pytest.raises(ValueError, match=message):
            module.validate_parameters(parameters, execution_target='local-cpu')
    with pytest.raises(ValueError, match='execution target'):
        module.validate_parameters(defaults, execution_target='local-gpu')


def test_svm_runtime_requires_explicit_training_action_input() -> None:
    runtime = get_node_registry()['svm-image-classifier']
    with pytest.raises(ValueError, match='action'):
        runtime.execute({}, {})