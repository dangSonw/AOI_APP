import hashlib
from io import BytesIO

import numpy as np
import pytest

from core.nodes import ArtifactBinding, NodeExecutionContext, get_node_runtime
from core.nodes.errors import NodeExecutionCancelled


def _npy_bytes(value: np.ndarray) -> bytes:
    stream = BytesIO()
    np.save(stream, value, allow_pickle=False)
    return stream.getvalue()


def _npz_bytes(**values: np.ndarray) -> bytes:
    stream = BytesIO()
    np.savez(stream, **values)
    return stream.getvalue()


def _context(key: str, content: bytes, media_type: str) -> NodeExecutionContext:
    binding = ArtifactBinding(hashlib.sha256(content).hexdigest(), media_type, len(content))
    return NodeExecutionContext(artifacts={key: binding}, resolve_artifact=lambda _: content)


def _invoke(node_id: str, inputs, parameters, context: NodeExecutionContext | None = None):
    runtime = get_node_runtime(node_id)
    assert runtime is not None
    return runtime.invoke(inputs, parameters, context=context)


@pytest.mark.parametrize('node_id,parameters', [
    ('absolute-difference', {'referenceAsset': 'golden'}),
    ('ssim', {'windowSize': 11}),
    ('normalized-cross-correlation', {}),
    ('edge-difference', {'threshold': 0.2}),
    ('gradient-difference', {}),
])
def test_golden_image_comparators_score_identical_image_as_normal(node_id: str, parameters: dict) -> None:
    image = np.tile(np.arange(32, dtype=np.uint8), (32, 1))
    content = _npy_bytes(image)

    outputs = _invoke(
        node_id, {'image': image}, parameters,
        _context('golden-image', content, 'application/x-numpy'),
    )

    anomaly_map = outputs['anomaly-map']
    assert anomaly_map.shape == image.shape
    assert anomaly_map.dtype == np.float32
    assert np.all(np.isfinite(anomaly_map))
    assert 0.0 <= float(anomaly_map.min()) <= float(anomaly_map.max()) <= 1.0
    assert outputs['score'] == pytest.approx(0.0, abs=1e-6)


@pytest.mark.parametrize('node_id,parameters', [
    ('absolute-difference', {'referenceAsset': 'golden'}),
    ('ssim', {'windowSize': 7}),
    ('normalized-cross-correlation', {}),
    ('edge-difference', {'threshold': 0.1}),
    ('gradient-difference', {}),
])
def test_golden_image_comparators_localize_synthetic_defect(node_id: str, parameters: dict) -> None:
    golden = np.zeros((48, 48), dtype=np.uint8)
    golden[8:40, 8:40] = 80
    observed = golden.copy()
    observed[20:28, 20:28] = 255

    outputs = _invoke(
        node_id, {'image': observed}, parameters,
        _context('golden-image', _npy_bytes(golden), 'application/x-numpy'),
    )

    anomaly_map = outputs['anomaly-map']
    assert outputs['score'] > 0.0
    assert float(anomaly_map[20:28, 20:28].mean()) > float(anomaly_map[:8, :8].mean())


def test_median_mad_uses_verified_statistics_archive() -> None:
    median = np.full((24, 24), 0.25, dtype=np.float32)
    mad = np.full((24, 24), 0.02, dtype=np.float32)
    observed = median.copy()
    observed[10:14, 10:14] = 0.9
    content = _npz_bytes(median=median, mad=mad)

    outputs = _invoke(
        'median-mad-robust-difference', {'image': observed}, {'epsilon': 0.001},
        _context('golden-statistics', content, 'application/x-numpy-archive'),
    )

    anomaly_map = outputs['anomaly-map']
    assert anomaly_map.dtype == np.float32
    assert float(anomaly_map[10:14, 10:14].mean()) > 0.9
    assert float(anomaly_map[:8, :8].max()) == pytest.approx(0.0)
    assert 0.0 < outputs['score'] < 1.0


def test_per_pixel_mahalanobis_uses_mean_and_covariance_archive() -> None:
    height, width = 16, 20
    mean = np.full((height, width, 3), 0.25, dtype=np.float32)
    covariance = np.broadcast_to(np.eye(3, dtype=np.float32) * 0.01, (height, width, 3, 3)).copy()
    observed = mean.copy()
    observed[6:10, 8:12, 0] = 1.0
    content = _npz_bytes(mean=mean, covariance=covariance)

    outputs = _invoke(
        'per-pixel-mahalanobis-distance', {'image': observed}, {'regularization': 0.001},
        _context('distribution-statistics', content, 'application/x-numpy-archive'),
    )

    anomaly_map = outputs['anomaly-map']
    assert anomaly_map.shape == (height, width)
    assert float(anomaly_map[6:10, 8:12].mean()) > 0.9
    assert float(anomaly_map[:4, :4].max()) == pytest.approx(0.0)


def test_template_matching_returns_detection_in_existing_detection_shape() -> None:
    image = np.zeros((64, 64), dtype=np.uint8)
    template = np.zeros((12, 10), dtype=np.uint8)
    template[2:10, 3:7] = 255
    image[31:43, 22:32] = template

    outputs = _invoke(
        'template-matching', {'image': image}, {'method': 'ccoeff-normed'},
        _context('template-image', _npy_bytes(template), 'application/x-numpy'),
    )

    assert outputs['score'] == pytest.approx(0.0, abs=1e-6)
    assert outputs['detections'] == [{
        'x': 22, 'y': 31, 'width': 10, 'height': 12,
        'score': pytest.approx(1.0), 'label': 'template-match',
    }]


def test_binary_xor_and_score_fusion_are_context_free() -> None:
    mask = np.zeros((10, 10), dtype=np.uint8)
    reference = mask.copy()
    mask[2:4, 2:7] = 255

    xor = _invoke('binary-xor', {'mask': mask, 'reference': reference}, {})
    maximum = _invoke('golden-score-fusion', {'scores': [0.1, 0.7, 0.2]}, {'method': 'maximum'})
    mean = _invoke('golden-score-fusion', {'scores': [0.1, 0.7, 0.2]}, {'method': 'mean'})

    assert xor['difference-mask'].dtype == np.uint8
    assert xor['score'] == pytest.approx(0.1)
    assert maximum['score'] == pytest.approx(0.7)
    assert mean['score'] == pytest.approx(1.0 / 3.0)


@pytest.mark.parametrize('mutation,error', [
    (lambda image: image.astype(np.float32) + np.nan, 'finite'),
    (lambda image: image[:, :-1], 'shape'),
    (lambda image: image.astype(np.int16), 'dtype'),
])
def test_golden_image_artifact_rejects_invalid_values(mutation, error: str) -> None:
    image = np.zeros((16, 16), dtype=np.uint8)
    invalid = mutation(image)

    with pytest.raises(ValueError, match=error):
        _invoke(
            'absolute-difference', {'image': image}, {'referenceAsset': 'golden'},
            _context('golden-image', _npy_bytes(invalid), 'application/x-numpy'),
        )


def test_contextual_golden_node_rejects_direct_legacy_execution() -> None:
    runtime = get_node_runtime('absolute-difference')
    assert runtime is not None

    with pytest.raises(Exception, match='execution context'):
        runtime.invoke({'image': np.zeros((8, 8), dtype=np.uint8)}, {'referenceAsset': 'golden'})


def test_golden_manifests_declare_typed_artifact_contracts() -> None:
    from core.nodes import get_node_manifest_registry

    manifests = get_node_manifest_registry()
    assert tuple((item.key, item.schema) for item in manifests['absolute-difference'].artifact_contracts['inputs']) == (
        ('golden-image:application/x-numpy', None),
    )
    assert tuple((item.key, item.schema) for item in manifests['median-mad-robust-difference'].artifact_contracts['inputs']) == (
        ('golden-statistics:application/x-numpy-archive', None),
    )
    assert tuple((item.key, item.schema) for item in manifests['per-pixel-mahalanobis-distance'].artifact_contracts['inputs']) == (
        ('distribution-statistics:application/x-numpy-archive', None),
    )


def test_ssim_rejects_oversized_image_before_processing() -> None:
    image = np.zeros((4000, 8001), dtype=np.uint8)
    with pytest.raises(ValueError, match='32,000,000-pixel'):
        _invoke('ssim', {'image': image}, {'windowSize': 11}, _context('golden-image', _npy_bytes(image), 'application/x-numpy'))


def test_ssim_honours_cancellation_checkpoint() -> None:
    image = np.zeros((16, 16), dtype=np.uint8)
    context = NodeExecutionContext(
        artifacts=_context('golden-image', _npy_bytes(image), 'application/x-numpy').artifacts,
        resolve_artifact=lambda _: _npy_bytes(image),
        is_cancelled=lambda: True,
    )
    with pytest.raises(NodeExecutionCancelled):
        _invoke('ssim', {'image': image}, {'windowSize': 11}, context)