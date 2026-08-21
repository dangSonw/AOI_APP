from __future__ import annotations

from io import BytesIO
from zipfile import ZIP_STORED, BadZipFile, ZipFile
import cv2
import numpy as np
from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse

NODE_ID = 'golden-score-fusion'
USE = NodeUse.DEBUG
INPUT_KEYS = ('scores',)
OUTPUT_KEYS = ('score',)

def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    raw_scores = inputs.get('scores')
    if not isinstance(raw_scores, list) or not raw_scores:
        raise ValueError('Golden score fusion requires at least one score.')
    scores = np.asarray(raw_scores, dtype=np.float64)
    if scores.ndim != 1 or not np.all(np.isfinite(scores)) or np.any((scores < 0.0) | (scores > 1.0)):
        raise ValueError('Golden scores must be finite numbers between zero and one.')
    method = str(parameters['method'])
    if method == 'maximum':
        score = float(scores.max())
    elif method in {'mean', 'weighted-mean'}:
        score = float(scores.mean())
    else:
        raise ValueError('Golden score fusion method is unsupported.')
    return {'score': score}

NUMPY_MEDIA_TYPE = 'application/x-numpy'

NUMPY_ARCHIVE_MEDIA_TYPE = 'application/x-numpy-archive'

MAX_ARRAY_BYTES = 512 * 1024 * 1024

MAX_ARCHIVE_MEMBERS = 8

def require_execution_context(node_id: str) -> NodeOutputs:
    raise NodeExecutionContextRequired(f'Node runtime {node_id} requires an execution context.')

def _read_npy_header(content: bytes) -> tuple[tuple[int, ...], np.dtype, int]:
    stream = BytesIO(content)
    try:
        version = np.lib.format.read_magic(stream)
        if version == (1, 0):
            shape, _, dtype = np.lib.format.read_array_header_1_0(stream)
        elif version in {(2, 0), (3, 0)}:
            shape, _, dtype = np.lib.format.read_array_header_2_0(stream)
        else:
            raise ValueError('NumPy artifact format version is unsupported.')
    except (EOFError, ValueError) as error:
        raise ValueError('NumPy artifact header is invalid.') from error
    return (tuple((int(item) for item in shape)), np.dtype(dtype), stream.tell())

def _load_npy(content: bytes, *, name: str) -> np.ndarray:
    shape, dtype, data_offset = _read_npy_header(content)
    if dtype.hasobject:
        raise ValueError(f'{name} must not contain Python objects.')
    element_count = int(np.prod(shape, dtype=np.int64)) if shape else 1
    data_bytes = element_count * dtype.itemsize
    if element_count < 1 or data_bytes > MAX_ARRAY_BYTES or data_bytes > len(content) - data_offset:
        raise ValueError(f'{name} exceeds bounded NumPy artifact size.')
    try:
        value = np.load(BytesIO(content), allow_pickle=False)
    except (EOFError, OSError, ValueError) as error:
        raise ValueError(f'{name} is not a valid NumPy array artifact.') from error
    if not isinstance(value, np.ndarray):
        raise ValueError(f'{name} must contain one NumPy array.')
    return value

def _load_npz(content: bytes, *, name: str) -> dict[str, np.ndarray]:
    try:
        with ZipFile(BytesIO(content)) as archive:
            members = archive.infolist()
            if not members or len(members) > MAX_ARCHIVE_MEMBERS:
                raise ValueError(f'{name} has an invalid member count.')
            arrays: dict[str, np.ndarray] = {}
            total_size = 0
            for member in members:
                if member.is_dir() or not member.filename.endswith('.npy') or '/' in member.filename:
                    raise ValueError(f'{name} contains an unsupported member.')
                if member.compress_type != ZIP_STORED:
                    raise ValueError(f'{name} members must be stored without compression.')
                total_size += member.file_size
                if member.file_size > MAX_ARRAY_BYTES or total_size > MAX_ARRAY_BYTES:
                    raise ValueError(f'{name} exceeds bounded archive size.')
                key = member.filename[:-4]
                if not key or key in arrays:
                    raise ValueError(f'{name} contains duplicate array names.')
                arrays[key] = _load_npy(archive.read(member), name=f'{name}.{key}')
            return arrays
    except BadZipFile as error:
        raise ValueError(f'{name} is not a valid NumPy archive artifact.') from error

def _image(value: object, *, name: str='Image') -> np.ndarray:
    if not isinstance(value, np.ndarray) or value.size == 0 or value.ndim not in {2, 3}:
        raise ValueError(f'{name} must be a non-empty two- or three-dimensional NumPy image.')
    if value.ndim == 3 and value.shape[2] not in {1, 3}:
        raise ValueError(f'{name} must have one or three channels.')
    if value.dtype.kind not in {'u', 'f'} or value.dtype.itemsize > 8:
        raise ValueError(f'{name} dtype is unsupported.')
    if not np.all(np.isfinite(value)):
        raise ValueError(f'{name} values must be finite.')
    if value.dtype.kind == 'f' and (float(value.min()) < 0.0 or float(value.max()) > 1.0):
        raise ValueError(f'{name} floating values must be between zero and one.')
    return value

def _normalized(value: np.ndarray) -> np.ndarray:
    if value.dtype.kind == 'u':
        maximum = float(np.iinfo(value.dtype).max)
        return value.astype(np.float32) / maximum
    return value.astype(np.float32)

def _gray(value: np.ndarray) -> np.ndarray:
    normalized = _normalized(value)
    if normalized.ndim == 2:
        return normalized
    if normalized.shape[2] == 1:
        return normalized[:, :, 0]
    return cv2.cvtColor(normalized, cv2.COLOR_BGR2GRAY)

def _map(value: np.ndarray) -> np.ndarray:
    if value.ndim == 3:
        value = value.mean(axis=2)
    return np.clip(value, 0.0, 1.0).astype(np.float32)

def _outputs(anomaly_map: np.ndarray) -> NodeOutputs:
    bounded = _map(anomaly_map)
    return {'anomaly-map': bounded, 'score': float(bounded.mean())}

def _golden_image(inputs: NodeInputs, context: NodeExecutionContext) -> tuple[np.ndarray, np.ndarray]:
    observed = _image(inputs.get('image'))
    content = context.read_artifact('golden-image', expected_media_types=(NUMPY_MEDIA_TYPE,))
    reference = _image(_load_npy(content, name='Golden image'), name='Golden image')
    if reference.shape != observed.shape:
        raise ValueError('Golden image shape must match observed image shape.')
    if reference.dtype != observed.dtype:
        raise ValueError('Golden image dtype must match observed image dtype.')
    return (observed, reference)

def _absolute_difference(observed: np.ndarray, reference: np.ndarray) -> NodeOutputs:
    return _outputs(np.abs(_normalized(observed) - _normalized(reference)))

def _ssim(observed: np.ndarray, reference: np.ndarray, window_size: int) -> NodeOutputs:
    if window_size < 3 or window_size % 2 == 0 or window_size > min(observed.shape[:2]):
        raise ValueError('SSIM window size must be odd and fit inside the image.')
    first = _gray(observed)
    second = _gray(reference)
    sigma = max(0.5, 1.5 * window_size / 11.0)
    kernel = (window_size, window_size)
    mean_first = cv2.GaussianBlur(first, kernel, sigma)
    mean_second = cv2.GaussianBlur(second, kernel, sigma)
    variance_first = cv2.GaussianBlur(first * first, kernel, sigma) - mean_first * mean_first
    variance_second = cv2.GaussianBlur(second * second, kernel, sigma) - mean_second * mean_second
    covariance = cv2.GaussianBlur(first * second, kernel, sigma) - mean_first * mean_second
    c1 = 0.01 ** 2
    c2 = 0.03 ** 2
    numerator = (2.0 * mean_first * mean_second + c1) * (2.0 * covariance + c2)
    denominator = (mean_first * mean_first + mean_second * mean_second + c1) * (variance_first + variance_second + c2)
    similarity = np.divide(numerator, denominator, out=np.ones_like(numerator), where=denominator > 0)
    return _outputs((1.0 - np.clip(similarity, -1.0, 1.0)) / 2.0)

def _normalized_cross_correlation(observed: np.ndarray, reference: np.ndarray) -> NodeOutputs:
    first = _gray(observed)
    second = _gray(reference)
    window_size = min(11, min(first.shape))
    if window_size % 2 == 0:
        window_size -= 1
    if window_size < 3:
        raise ValueError('Normalized cross-correlation requires images at least three pixels wide and high.')
    kernel = (window_size, window_size)
    mean_first = cv2.boxFilter(first, -1, kernel, normalize=True)
    mean_second = cv2.boxFilter(second, -1, kernel, normalize=True)
    covariance = cv2.boxFilter(first * second, -1, kernel, normalize=True) - mean_first * mean_second
    variance_first = cv2.boxFilter(first * first, -1, kernel, normalize=True) - mean_first * mean_first
    variance_second = cv2.boxFilter(second * second, -1, kernel, normalize=True) - mean_second * mean_second
    denominator = np.sqrt(np.maximum(variance_first, 0.0) * np.maximum(variance_second, 0.0))
    similarity = np.divide(covariance, denominator, out=np.zeros_like(covariance), where=denominator > 1e-08)
    equal_flat = (denominator <= 1e-08) & (np.abs(mean_first - mean_second) <= 1e-06)
    similarity[equal_flat] = 1.0
    return _outputs((1.0 - np.clip(similarity, -1.0, 1.0)) / 2.0)

def _edge_difference(observed: np.ndarray, reference: np.ndarray, threshold: float) -> NodeOutputs:
    if threshold < 0.0 or threshold > 1.0:
        raise ValueError('Edge threshold must be between zero and one.')
    high = max(1, int(round(threshold * 255.0)))
    low = max(0, high // 2)
    first = cv2.Canny((_gray(observed) * 255.0).astype(np.uint8), low, high)
    second = cv2.Canny((_gray(reference) * 255.0).astype(np.uint8), low, high)
    return _outputs(cv2.bitwise_xor(first, second).astype(np.float32) / 255.0)

def _gradient_difference(observed: np.ndarray, reference: np.ndarray) -> NodeOutputs:

    def magnitude(value: np.ndarray) -> np.ndarray:
        gray = _gray(value)
        horizontal = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        vertical = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        return cv2.magnitude(horizontal, vertical)
    return _outputs(np.abs(magnitude(observed) - magnitude(reference)) / (4.0 * np.sqrt(2.0)))

def _median_mad(inputs: NodeInputs, parameters: NodeParameters, context: NodeExecutionContext) -> NodeOutputs:
    observed = _image(inputs.get('image'))
    arrays = _load_npz(context.read_artifact('golden-statistics', expected_media_types=(NUMPY_ARCHIVE_MEDIA_TYPE,)), name='Golden statistics')
    if set(arrays) != {'median', 'mad'}:
        raise ValueError('Golden statistics must contain exactly median and mad arrays.')
    median, mad = (arrays['median'], arrays['mad'])
    if median.shape != observed.shape or mad.shape != observed.shape:
        raise ValueError('Median and MAD shape must match observed image shape.')
    if median.dtype.kind != 'f' or mad.dtype.kind != 'f':
        raise ValueError('Median and MAD dtype must be floating point.')
    if not np.all(np.isfinite(median)) or not np.all(np.isfinite(mad)) or np.any(mad < 0):
        raise ValueError('Median and MAD values must be finite and MAD must be non-negative.')
    normalized = _normalized(observed)
    epsilon = float(parameters['epsilon'])
    if epsilon <= 0.0:
        raise ValueError('Median–MAD epsilon must be positive.')
    robust_z = np.abs(normalized - median.astype(np.float32)) / (1.4826 * mad.astype(np.float32) + epsilon)
    return _outputs(1.0 - np.exp(-robust_z))

def _mahalanobis(inputs: NodeInputs, parameters: NodeParameters, context: NodeExecutionContext) -> NodeOutputs:
    observed = _image(inputs.get('image'))
    arrays = _load_npz(context.read_artifact('distribution-statistics', expected_media_types=(NUMPY_ARCHIVE_MEDIA_TYPE,)), name='Distribution statistics')
    if set(arrays) != {'mean', 'covariance'}:
        raise ValueError('Distribution statistics must contain exactly mean and covariance arrays.')
    normalized = _normalized(observed)
    samples = normalized[:, :, None] if normalized.ndim == 2 else normalized
    mean = arrays['mean']
    if mean.ndim == 2:
        mean = mean[:, :, None]
    channels = samples.shape[2]
    covariance = arrays['covariance']
    if mean.shape != samples.shape or covariance.shape != (*samples.shape[:2], channels, channels):
        raise ValueError('Mean and covariance shape must match observed image channels.')
    if mean.dtype.kind != 'f' or covariance.dtype.kind != 'f':
        raise ValueError('Mean and covariance dtype must be floating point.')
    if not np.all(np.isfinite(mean)) or not np.all(np.isfinite(covariance)):
        raise ValueError('Mean and covariance values must be finite.')
    regularization = float(parameters['regularization'])
    if regularization <= 0.0:
        raise ValueError('Mahalanobis regularization must be positive.')
    regularized = covariance.astype(np.float64) + np.eye(channels) * regularization
    difference = samples.astype(np.float64) - mean.astype(np.float64)
    try:
        solved = np.linalg.solve(regularized, difference[..., None])[..., 0]
    except np.linalg.LinAlgError as error:
        raise ValueError('Covariance is not positive definite after regularization.') from error
    squared_distance = np.maximum(np.einsum('...i,...i->...', difference, solved), 0.0)
    return _outputs(1.0 - np.exp(-0.5 * squared_distance))

def _template_matching(inputs: NodeInputs, parameters: NodeParameters, context: NodeExecutionContext) -> NodeOutputs:
    image = _image(inputs.get('image'))
    template = _image(_load_npy(context.read_artifact('template-image', expected_media_types=(NUMPY_MEDIA_TYPE,)), name='Template image'), name='Template image')
    if image.dtype != template.dtype or image.ndim != template.ndim or image.shape[2:] != template.shape[2:]:
        raise ValueError('Template image dtype and channels must match observed image.')
    if template.shape[0] > image.shape[0] or template.shape[1] > image.shape[1]:
        raise ValueError('Template image must fit inside observed image.')
    methods = {'sqdiff': cv2.TM_SQDIFF, 'sqdiff-normed': cv2.TM_SQDIFF_NORMED, 'ccorr-normed': cv2.TM_CCORR_NORMED, 'ccoeff-normed': cv2.TM_CCOEFF_NORMED}
    method_name = str(parameters['method'])
    if method_name not in methods:
        raise ValueError('Template matching method is unsupported.')
    result = cv2.matchTemplate(image, template, methods[method_name])
    minimum, maximum, minimum_location, maximum_location = cv2.minMaxLoc(result)
    if method_name == 'sqdiff':
        quality = 1.0 if minimum <= 1e-12 else 1.0 / (1.0 + minimum)
        location = minimum_location
    elif method_name == 'sqdiff-normed':
        quality = 1.0 - minimum
        location = minimum_location
    else:
        quality = maximum
        location = maximum_location
    quality = min(max(float(quality), 0.0), 1.0)
    detection = {'x': int(location[0]), 'y': int(location[1]), 'width': int(template.shape[1]), 'height': int(template.shape[0]), 'score': quality, 'label': 'template-match'}
    return {'detections': [detection], 'score': 1.0 - quality}

def execute_golden_with_context(node_id: str, inputs: NodeInputs, parameters: NodeParameters, context: NodeExecutionContext) -> NodeOutputs:
    context.checkpoint()
    if node_id == 'median-mad-robust-difference':
        return _median_mad(inputs, parameters, context)
    if node_id == 'per-pixel-mahalanobis-distance':
        return _mahalanobis(inputs, parameters, context)
    if node_id == 'template-matching':
        return _template_matching(inputs, parameters, context)
    observed, reference = _golden_image(inputs, context)
    if node_id == 'absolute-difference':
        return _absolute_difference(observed, reference)
    if node_id == 'ssim':
        return _ssim(observed, reference, int(parameters['windowSize']))
    if node_id == 'normalized-cross-correlation':
        return _normalized_cross_correlation(observed, reference)
    if node_id == 'edge-difference':
        return _edge_difference(observed, reference, float(parameters['threshold']))
    if node_id == 'gradient-difference':
        return _gradient_difference(observed, reference)
    raise ValueError(f'Golden node {node_id} has no contextual implementation.')

def execute_binary_xor(inputs: NodeInputs) -> NodeOutputs:
    first = _image(inputs.get('mask'), name='Mask')
    second = _image(inputs.get('reference'), name='Reference mask')
    if first.shape != second.shape:
        raise ValueError('Mask and reference mask shape must match.')
    difference = np.logical_xor(first != 0, second != 0)
    if difference.ndim == 3:
        difference = np.any(difference, axis=2)
    return {'difference-mask': difference.astype(np.uint8) * 255, 'score': float(difference.mean())}
