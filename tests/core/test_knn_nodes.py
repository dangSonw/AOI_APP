import numpy as np
import pytest

from core.nodes import get_node_runtime


TRAINING_SAMPLES = [
    {'label': 'dark', 'color': [0, 0, 0]},
    {'label': 'dark', 'color': [32, 32, 32]},
    {'label': 'bright', 'color': [224, 224, 224]},
    {'label': 'bright', 'color': [255, 255, 255]},
]


def _parameters(implementation: str) -> dict[str, object]:
    return {
        'implementation': implementation,
        'neighbors': 3,
        'distanceMetric': 'euclidean',
        'distanceWeighted': True,
        'trainingSamples': TRAINING_SAMPLES,
    }


@pytest.mark.parametrize('implementation', ['opencv', 'manual-python'])
def test_knn_object_classifier_labels_detected_regions(implementation: str) -> None:
    image = np.zeros((12, 24, 3), dtype=np.uint8)
    image[:, 12:] = 255
    detections = [
        {'x': 0, 'y': 0, 'width': 12, 'height': 12, 'area': 144},
        {'x': 12, 'y': 0, 'width': 12, 'height': 12, 'area': 144},
    ]

    runtime = get_node_runtime('knn-object-classifier')
    assert runtime is not None
    result = runtime.execute({'image': image, 'detections': detections}, _parameters(implementation))

    classified = result['classified-detections']
    assert [item['label'] for item in classified] == ['dark', 'bright']
    assert all(0.0 <= item['confidence'] <= 1.0 for item in classified)
    assert all(len(item['neighbors']) == 3 for item in classified)
    assert 'label' not in detections[0]


@pytest.mark.parametrize('implementation', ['opencv', 'manual-python'])
def test_knn_image_segmentation_returns_mask_and_object_contour(implementation: str) -> None:
    image = np.zeros((20, 20, 3), dtype=np.uint8)
    image[5:15, 6:14] = 255
    parameters = {
        **_parameters(implementation),
        'foregroundLabels': ['bright'],
        'minimumConfidence': 0.5,
    }

    runtime = get_node_runtime('knn-image-segmentation')
    assert runtime is not None
    result = runtime.execute({'image': image}, parameters)

    mask = result['mask']
    contours = result['contours']
    assert mask.dtype == np.uint8
    assert mask.shape == image.shape[:2]
    assert np.count_nonzero(mask) == 80
    assert len(contours) == 1


def test_knn_implementations_produce_matching_masks() -> None:
    image = np.zeros((8, 8, 3), dtype=np.uint8)
    image[:, 4:] = 255
    runtime = get_node_runtime('knn-image-segmentation')
    assert runtime is not None

    outputs = [
        runtime.execute(
            {'image': image},
            {**_parameters(implementation), 'foregroundLabels': ['bright'], 'minimumConfidence': 0.5},
        )['mask']
        for implementation in ('opencv', 'manual-python')
    ]

    assert np.array_equal(outputs[0], outputs[1])


def test_knn_nodes_reject_invalid_configuration_and_detections() -> None:
    image = np.zeros((8, 8, 3), dtype=np.uint8)
    classifier = get_node_runtime('knn-object-classifier')
    segmenter = get_node_runtime('knn-image-segmentation')
    assert classifier is not None and segmenter is not None

    with pytest.raises(ValueError, match='cannot exceed'):
        classifier.execute(
            {'image': image, 'detections': []},
            {**_parameters('manual-python'), 'neighbors': 5},
        )
    with pytest.raises(ValueError, match='inside the image'):
        classifier.execute(
            {'image': image, 'detections': [{'x': 7, 'y': 7, 'width': 2, 'height': 2}]},
            _parameters('manual-python'),
        )
    with pytest.raises(ValueError, match='missing from training samples'):
        segmenter.execute(
            {'image': image},
            {**_parameters('manual-python'), 'foregroundLabels': ['unknown'], 'minimumConfidence': 0.5},
        )


def test_opencv_knn_rejects_manual_only_manhattan_metric() -> None:
    runtime = get_node_runtime('knn-image-segmentation')
    assert runtime is not None

    with pytest.raises(ValueError, match='only Euclidean'):
        runtime.execute(
            {'image': np.zeros((2, 2, 3), dtype=np.uint8)},
            {
                **_parameters('opencv'),
                'distanceMetric': 'manhattan',
                'foregroundLabels': ['bright'],
                'minimumConfidence': 0.5,
            },
        )