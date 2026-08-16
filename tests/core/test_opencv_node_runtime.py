import numpy as np
import pytest

from core.nodes import get_node_runtime


def test_opencv_preprocessing_chain_produces_mask_and_detections() -> None:
    image = np.zeros((64, 64, 3), dtype=np.uint8)
    image[16:48, 16:48] = 255

    gray = get_node_runtime('color-conversion').execute(
        {'image': image}, {'mode': 'bgr-to-gray'},
    )['processed-image']
    blurred = get_node_runtime('gaussian-blur').execute(
        {'image': gray}, {'kernelSize': 5, 'sigma': 1.0},
    )['processed-image']
    mask = get_node_runtime('global-threshold').execute(
        {'image': blurred}, {'threshold': 127.0},
    )['mask']
    detections = get_node_runtime('connected-components').execute(
        {'mask': mask}, {},
    )['detections']

    assert gray.shape == (64, 64)
    assert mask.dtype == np.uint8
    assert len(detections) == 1
    assert detections[0]['x'] == 16
    assert detections[0]['y'] == 16
    assert detections[0]['width'] == 32
    assert detections[0]['height'] == 32
    assert 1000 <= detections[0]['area'] <= 1024
    assert detections[0]['centroidX'] == 31.5
    assert detections[0]['centroidY'] == 31.5


def test_draw_detections_and_image_output_preserve_viewable_image() -> None:
    image = np.zeros((40, 40, 3), dtype=np.uint8)
    detections = [{'x': 5, 'y': 6, 'width': 20, 'height': 10, 'label': 'ROI'}]

    drawn = get_node_runtime('draw-detections').execute(
        {'image': image, 'detections': detections},
        {'color': [0, 255, 0], 'thickness': 2, 'showLabels': True},
    )['annotated-image']
    output = get_node_runtime('image-output').execute({'image': drawn}, {})['preview-image']

    assert output.shape == image.shape
    assert np.count_nonzero(output) > 0


def test_delay_and_bounded_repeat_are_bounded_image_control_nodes() -> None:
    image = np.ones((2, 2), dtype=np.uint8)

    delayed = get_node_runtime('delay').execute({'image': image}, {'milliseconds': 0})
    repeated = get_node_runtime('bounded-repeat').execute(
        {'image': delayed['delayed-image']}, {'iterations': 3},
    )

    assert delayed['delayed-image'] is image
    assert repeated['images'] == [image, image, image]


@pytest.mark.parametrize(
    ('node_id', 'inputs', 'parameters', 'output_key', 'expected_shape'),
    [
        ('crop-image', {'image': np.arange(300, dtype=np.uint8).reshape(10, 10, 3)}, {'x': 2, 'y': 3, 'width': 4, 'height': 5}, 'processed-image', (5, 4, 3)),
        ('flip-image', {'image': np.arange(18, dtype=np.uint8).reshape(2, 3, 3)}, {'axis': 'horizontal'}, 'processed-image', (2, 3, 3)),
        ('rotate-image', {'image': np.zeros((8, 12, 3), dtype=np.uint8)}, {'angleDegrees': 90.0, 'scale': 1.0, 'expandCanvas': True, 'interpolation': 'linear', 'borderMode': 'constant', 'borderValue': [0, 0, 0]}, 'processed-image', (12, 8, 3)),
        ('pad-image', {'image': np.zeros((4, 5, 3), dtype=np.uint8)}, {'top': 1, 'right': 2, 'bottom': 3, 'left': 4, 'borderMode': 'constant', 'borderValue': [0, 0, 0]}, 'processed-image', (8, 11, 3)),
        ('warp-perspective', {'image': np.zeros((4, 5, 3), dtype=np.uint8), 'transform': np.eye(3, dtype=np.float32)}, {'width': 7, 'height': 6, 'interpolation': 'linear', 'borderMode': 'constant', 'borderValue': [0, 0, 0]}, 'processed-image', (6, 7, 3)),
        ('histogram-equalization', {'image': np.full((8, 8), 50, dtype=np.uint8)}, {'mode': 'grayscale'}, 'processed-image', (8, 8)),
        ('gamma-correction', {'image': np.full((8, 8), 50, dtype=np.uint8)}, {'gamma': 2.0}, 'processed-image', (8, 8)),
        ('in-range-mask', {'image': np.full((8, 8, 3), 50, dtype=np.uint8)}, {'colorSpace': 'bgr', 'lowerBound': [40, 40, 40], 'upperBound': [60, 60, 60]}, 'mask', (8, 8)),
        ('apply-mask', {'image': np.full((8, 8, 3), 50, dtype=np.uint8), 'mask': np.full((8, 8), 255, dtype=np.uint8)}, {}, 'processed-image', (8, 8, 3)),
        ('blend-images', {'image': np.full((8, 8, 3), 50, dtype=np.uint8), 'overlay': np.full((8, 8, 3), 100, dtype=np.uint8)}, {'alpha': 0.25}, 'processed-image', (8, 8, 3)),
        ('overlay-mask', {'image': np.full((8, 8, 3), 50, dtype=np.uint8), 'mask': np.full((8, 8), 255, dtype=np.uint8)}, {'color': [0, 0, 255], 'opacity': 0.5}, 'annotated-image', (8, 8, 3)),
        ('draw-contours', {'image': np.zeros((8, 8, 3), dtype=np.uint8), 'contours': [np.array([[[1, 1]], [[6, 1]], [[6, 6]], [[1, 6]]], dtype=np.int32)]}, {'color': [0, 255, 0], 'thickness': 1, 'drawAll': True, 'contourIndex': 0}, 'annotated-image', (8, 8, 3)),
    ],
)
def test_practical_aoi_image_nodes_execute_with_typed_outputs(
    node_id: str,
    inputs: dict[str, object],
    parameters: dict[str, object],
    output_key: str,
    expected_shape: tuple[int, ...],
) -> None:
    runtime = get_node_runtime(node_id)

    assert runtime is not None
    output = runtime.execute(inputs, parameters)[output_key]

    assert isinstance(output, np.ndarray)
    assert output.shape == expected_shape


def test_crop_image_rejects_region_outside_source() -> None:
    runtime = get_node_runtime('crop-image')

    assert runtime is not None
    with pytest.raises(ValueError, match='inside the source image'):
        runtime.execute(
            {'image': np.zeros((8, 8), dtype=np.uint8)},
            {'x': 7, 'y': 7, 'width': 2, 'height': 2},
        )