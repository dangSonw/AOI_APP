import numpy as np
import pytest

from core.nodes import get_node_runtime


SAMPLES = [
    {'label': 'dark', 'color': [10, 10, 10]},
    {'label': 'dark', 'color': [40, 40, 40]},
    {'label': 'bright', 'color': [215, 215, 215]},
    {'label': 'bright', 'color': [250, 250, 250]},
]


def _objects() -> tuple[np.ndarray, list[dict[str, int]]]:
    image = np.zeros((10, 20, 3), dtype=np.uint8)
    image[:, :10] = 20
    image[:, 10:] = 235
    return image, [
        {'x': 0, 'y': 0, 'width': 10, 'height': 10},
        {'x': 10, 'y': 0, 'width': 10, 'height': 10},
    ]


@pytest.mark.parametrize('implementation', ['scikit-learn', 'manual-python'])
@pytest.mark.parametrize(
    ('node_id', 'extra'),
    [
        ('nearest-centroid-object-classifier', {'distanceMetric': 'euclidean'}),
        ('gaussian-naive-bayes-object-classifier', {'varianceSmoothing': 1e-9}),
        ('logistic-object-classifier', {
            'regularizationStrength': 0.01, 'learningRate': 0.1, 'maximumIterations': 1000,
            'tolerance': 1e-7, 'randomSeed': 42,
        }),
    ],
)
def test_supervised_ml_nodes_classify_dark_and_bright_objects(
    implementation: str,
    node_id: str,
    extra: dict[str, object],
) -> None:
    image, detections = _objects()
    runtime = get_node_runtime(node_id)
    assert runtime is not None

    output = runtime.execute(
        {'image': image, 'detections': detections},
        {'implementation': implementation, 'trainingSamples': SAMPLES, **extra},
    )['classified-detections']

    assert [item['label'] for item in output] == ['dark', 'bright']
    assert all(0.0 <= item['confidence'] <= 1.0 for item in output)
    assert all(set(item['classScores']) == {'dark', 'bright'} for item in output)
    assert 'label' not in detections[0]


@pytest.mark.parametrize('implementation', ['scikit-learn', 'manual-python'])
def test_kmeans_segmentation_returns_binary_mask_and_contour(implementation: str) -> None:
    image = np.zeros((20, 20, 3), dtype=np.uint8)
    image[5:15, 6:14] = 255
    runtime = get_node_runtime('kmeans-image-segmentation')
    assert runtime is not None

    result = runtime.execute({'image': image}, {
        'implementation': implementation, 'clusters': 2, 'colorSpace': 'bgr',
        'foregroundClusters': [1], 'maximumTrainingPixels': 10000,
        'maximumIterations': 100, 'tolerance': 1e-4, 'randomSeed': 42,
    })

    assert result['mask'].dtype == np.uint8
    assert set(np.unique(result['mask'])) <= {0, 255}
    assert np.count_nonzero(result['mask']) == 80
    assert len(result['contours']) == 1


@pytest.mark.parametrize('implementation', ['scikit-learn', 'manual-python'])
def test_pca_anomaly_detector_highlights_unseen_color(implementation: str) -> None:
    image = np.full((8, 8, 3), 40, dtype=np.uint8)
    image[2:6, 2:6] = [0, 0, 255]
    runtime = get_node_runtime('pca-anomaly-detector')
    assert runtime is not None

    result = runtime.execute({'image': image}, {
        'implementation': implementation,
        'components': 1,
        'scorePercentile': 99.0,
        'trainingSamples': [
            {'features': [20, 20, 20]}, {'features': [40, 40, 40]},
            {'features': [60, 60, 60]}, {'features': [80, 80, 80]},
        ],
    })

    anomaly_map = result['anomaly-map']
    assert anomaly_map.shape == image.shape[:2]
    assert anomaly_map.dtype == np.float32
    assert anomaly_map[3, 3] > anomaly_map[0, 0]
    assert 0.0 <= result['score'] <= 1.0


def test_ml_nodes_reject_invalid_training_samples_and_implementation() -> None:
    image, detections = _objects()
    classifier = get_node_runtime('nearest-centroid-object-classifier')
    segmenter = get_node_runtime('kmeans-image-segmentation')
    assert classifier is not None and segmenter is not None

    with pytest.raises(ValueError, match='two distinct labels'):
        classifier.execute(
            {'image': image, 'detections': detections},
            {'implementation': 'manual-python', 'distanceMetric': 'euclidean', 'trainingSamples': [
                {'label': 'same', 'color': [0, 0, 0]}, {'label': 'same', 'color': [255, 255, 255]},
            ]},
        )
    with pytest.raises(ValueError, match='Unsupported implementation'):
        segmenter.execute({'image': image}, {
            'implementation': 'unknown', 'clusters': 2, 'colorSpace': 'bgr',
            'foregroundClusters': [1], 'maximumTrainingPixels': 1000,
            'maximumIterations': 10, 'tolerance': 1e-4, 'randomSeed': 42,
        })