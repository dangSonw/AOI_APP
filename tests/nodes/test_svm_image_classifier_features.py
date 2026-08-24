from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from core.nodes import NodeExecutionCancelled
from tests.nodes.test_svm_image_classifier_contract import load_node_module


def item(path: Path, logical: str, class_name: str, class_id: int):
    return SimpleNamespace(path=path, logical_path=logical, class_name=class_name, class_id=class_id,
                           width_px=16, height_px=16, media_type='image/png')


def image(path: Path, value: int) -> None:
    assert cv2.imwrite(str(path), np.full((16, 16, 3), value, dtype=np.uint8))


def handle(items, mapping=None):
    return SimpleNamespace(items=tuple(items), class_mapping=mapping or {'cats': 0, 'dogs': 1},
                           dataset_id='animals', version='sha256:' + 'a' * 64)


def test_extracts_deterministic_hog_features_in_class_and_logical_order(tmp_path: Path) -> None:
    module = load_node_module()
    cat, dog = tmp_path / 'cat.png', tmp_path / 'dog.png'
    image(cat, 32); image(dog, 224)
    dataset = handle([item(dog, 'dogs/z.png', 'dogs', 1), item(cat, 'cats/a.png', 'cats', 0)])

    features, labels, diagnostics = module.extract_dataset_features(dataset, module.DEFAULT_PARAMETERS)

    assert labels.tolist() == [0, 1]
    assert features.shape == (2, 8100)
    assert np.isfinite(features).all()
    assert diagnostics == {'loaded': 2, 'failed': []}
    second = module.extract_dataset_features(dataset, module.DEFAULT_PARAMETERS)[0]
    assert np.array_equal(features, second)


def test_rejects_or_skips_invalid_images_without_exposing_host_paths(tmp_path: Path) -> None:
    module = load_node_module()
    corrupt = tmp_path / 'secret-corrupt.png'; corrupt.write_bytes(b'not-image')
    bad = item(corrupt, 'cats/bad.png', 'cats', 0)
    with pytest.raises(ValueError, match='cats/bad.png') as error:
        module.extract_dataset_features(handle([bad]), module.DEFAULT_PARAMETERS)
    assert str(tmp_path) not in str(error.value)

    valid = tmp_path / 'dog.png'; image(valid, 200)
    parameters = {**module.DEFAULT_PARAMETERS, 'invalidImagePolicy': 'skip'}
    features, labels, diagnostics = module.extract_dataset_features(
        handle([bad, item(valid, 'dogs/ok.png', 'dogs', 1)]), parameters,
    )
    assert features.shape[0] == labels.shape[0] == 1
    assert diagnostics['failed'][0]['logicalId'] == 'cats/bad.png'
    assert str(tmp_path) not in str(diagnostics)


@pytest.mark.parametrize(('dataset', 'message'), [
    (handle([], {'cats': 0}), 'two classes'),
    (handle([], {'cats': 0, 'dogs': 2}), 'contiguous'),
])
def test_rejects_empty_or_invalid_class_contracts(dataset, message: str) -> None:
    module = load_node_module()
    with pytest.raises(ValueError, match=message):
        module.extract_dataset_features(dataset, module.DEFAULT_PARAMETERS)


def test_enforces_extension_dimension_sample_and_cancellation_limits(tmp_path: Path) -> None:
    module = load_node_module()
    source = tmp_path / 'sample.gif'; source.write_bytes(b'gif')
    with pytest.raises(ValueError, match='extension'):
        module.extract_dataset_features(handle([item(source, 'cats/sample.gif', 'cats', 0)]), module.DEFAULT_PARAMETERS)

    png = tmp_path / 'sample.png'; image(png, 100)
    oversized = item(png, 'cats/sample.png', 'cats', 0); oversized.width_px = 5000
    with pytest.raises(ValueError, match='pixels'):
        module.extract_dataset_features(handle([oversized]), {**module.DEFAULT_PARAMETERS, 'maxImagePixels': 100})
    with pytest.raises(ValueError, match='samples'):
        module.extract_dataset_features(handle([item(png, 'cats/a.png', 'cats', 0)] * 3), {**module.DEFAULT_PARAMETERS, 'maxSamples': 2})
    with pytest.raises(NodeExecutionCancelled):
        module.extract_dataset_features(handle([item(png, 'cats/a.png', 'cats', 0)]), module.DEFAULT_PARAMETERS, is_cancelled=lambda: True)