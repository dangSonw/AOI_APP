import cv2
import numpy as np
import pytest

from core.nodes import NodeExecutionContext, get_node_runtime
from core.nodes.errors import NodeExecutionCancelled


def _execute(node_id: str, inputs: dict[str, object], parameters: dict[str, object]):
    runtime = get_node_runtime(node_id)
    assert runtime is not None
    return runtime.execute(inputs, parameters)


def test_affine_estimation_and_warp_are_separate_composable_nodes() -> None:
    source = np.float32([[0, 0], [2, 0], [0, 2], [2, 2]])
    destination = source + np.float32([1, 2])
    transform = _execute(
        'estimate-affine-transform',
        {'source-points': source, 'destination-points': destination},
        {'method': 'ransac', 'ransacThreshold': 3.0},
    )['transform']
    image = np.zeros((5, 5), dtype=np.uint8)
    image[0, 0] = 255
    warped = _execute(
        'warp-affine', {'image': image, 'transform': transform},
        {'width': 5, 'height': 5, 'interpolation': 'nearest', 'borderMode': 'constant', 'borderValue': [0, 0, 0]},
    )['processed-image']

    assert transform.shape == (2, 3)
    assert np.allclose(transform[:, 2], [1, 2], atol=0.01)
    assert warped[2, 1] == 255


def test_perspective_estimation_returns_homography() -> None:
    source = np.float32([[0, 0], [3, 0], [3, 3], [0, 3]])
    destination = np.float32([[1, 1], [4, 1], [4, 4], [1, 4]])

    transform = _execute(
        'estimate-perspective-transform',
        {'source-points': source, 'destination-points': destination},
        {'method': 'ransac', 'ransacThreshold': 3.0},
    )['transform']

    projected = cv2.perspectiveTransform(source.reshape(-1, 1, 2), transform).reshape(-1, 2)
    assert transform.shape == (3, 3)
    assert np.allclose(projected, destination, atol=0.01)


def test_distance_watershed_hull_and_contour_metrics_produce_typed_outputs() -> None:
    mask = np.zeros((20, 20), dtype=np.uint8)
    mask[5:15, 5:15] = 255
    distance = _execute('distance-transform', {'mask': mask}, {'metric': 'l2', 'maskSize': 3})['distance-map']
    image = np.zeros((20, 20, 3), dtype=np.uint8)
    image[5:15, 5:15] = 255
    segmented = _execute('watershed', {'image': image, 'mask': mask}, {})['segmented-mask']
    contour = np.array([[[2, 2]], [[10, 2]], [[8, 6]], [[10, 10]], [[2, 10]]], dtype=np.int32)
    hulls = _execute('convex-hull', {'contours': [contour]}, {})['hulls']
    metrics = _execute('contour-metrics', {'contours': [contour]}, {})['metrics']

    assert distance.shape == mask.shape
    assert distance.dtype == np.float32
    assert segmented.shape == mask.shape
    assert segmented.dtype == np.uint8
    assert len(hulls) == 1 and cv2.contourArea(hulls[0]) >= cv2.contourArea(contour)
    assert metrics[0]['area'] == pytest.approx(cv2.contourArea(contour))
    assert {'perimeter', 'centroidX', 'centroidY', 'solidity'} <= metrics[0].keys()


@pytest.mark.parametrize(
    ('node_id', 'operation', 'expected'),
    [
        ('image-arithmetic', 'add', 30),
        ('image-arithmetic', 'subtract', 0),
        ('image-arithmetic', 'multiply', 200),
        ('image-bitwise', 'and', 0),
        ('image-bitwise', 'or', 30),
        ('image-bitwise', 'xor', 30),
    ],
)
def test_image_arithmetic_and_bitwise_operations_saturate_and_preserve_shape(
    node_id: str,
    operation: str,
    expected: int,
) -> None:
    first = np.full((3, 4), 10, dtype=np.uint8)
    second = np.full((3, 4), 20, dtype=np.uint8)

    output = _execute(node_id, {'image': first, 'operand': second}, {'operation': operation})['processed-image']

    assert output.shape == first.shape
    assert output.dtype == np.uint8
    assert np.all(output == expected)


def test_extended_runtime_rejects_mismatched_images_and_invalid_points() -> None:
    with pytest.raises(ValueError, match='shape'):
        _execute(
            'image-arithmetic',
            {'image': np.zeros((2, 2), np.uint8), 'operand': np.zeros((3, 3), np.uint8)},
            {'operation': 'add'},
        )
    with pytest.raises(ValueError, match='at least three'):
        _execute(
            'estimate-affine-transform',
            {'source-points': [[0, 0]], 'destination-points': [[1, 1]]},
            {'method': 'ransac', 'ransacThreshold': 3.0},
        )


def test_watershed_rejects_unsupported_channels_and_oversized_images() -> None:
    with pytest.raises(ValueError, match='one or three channels'):
        _execute('watershed', {'image': np.zeros((8, 8, 2), np.uint8), 'mask': np.zeros((8, 8), np.uint8)}, {})
    with pytest.raises(ValueError, match='32,000,000-pixel'):
        _execute('watershed', {'image': np.zeros((4000, 8001), np.uint8), 'mask': np.zeros((4000, 8001), np.uint8)}, {})


def test_watershed_context_honours_cancellation() -> None:
    runtime = get_node_runtime('watershed')
    assert runtime is not None
    context = NodeExecutionContext(is_cancelled=lambda: True)
    with pytest.raises(NodeExecutionCancelled):
        runtime.invoke({'image': np.zeros((8, 8), np.uint8), 'mask': np.zeros((8, 8), np.uint8)}, {}, context=context)