from __future__ import annotations

from collections.abc import Sequence
import cv2
import numpy as np
from core.nodes.models import NodeExecutionContext, NodeInputs, NodeOutputs, NodeParameters, NodeUse
from core.vision.image_contract import validate_image

NODE_ID = 'watershed'
USE = NodeUse.DEBUG
INPUT_KEYS = ('image', 'mask')
OUTPUT_KEYS = ('segmented-mask',)

def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    return _execute_watershed_dispatch(inputs, parameters, None)


def execute_with_context(inputs: NodeInputs, parameters: NodeParameters, context: NodeExecutionContext) -> NodeOutputs:
    context.checkpoint()
    return _execute_watershed_dispatch(inputs, parameters, context)


def _execute_watershed_dispatch(inputs: NodeInputs, parameters: NodeParameters, context: NodeExecutionContext | None) -> NodeOutputs:
    if NODE_ID == 'estimate-affine-transform':
        source, destination = _matching_points(inputs, minimum=3)
        method = str(parameters['method'])
        methods = {'ransac': cv2.RANSAC, 'lmeds': cv2.LMEDS}
        if method not in methods:
            raise ValueError('Affine estimation method is unsupported.')
        transform, _ = cv2.estimateAffine2D(source, destination, method=methods[method], ransacReprojThreshold=float(parameters['ransacThreshold']))
        if transform is None:
            raise ValueError('Affine transform could not be estimated.')
        return {'transform': transform.astype(np.float32)}
    if NODE_ID == 'warp-affine':
        image = _image(inputs)
        transform = _array(inputs, 'transform').astype(np.float32)
        if transform.shape != (2, 3):
            raise ValueError('Affine transform must have shape 2 by 3.')
        width, height = (int(parameters['width']), int(parameters['height']))
        if width < 1 or height < 1:
            raise ValueError('Warp dimensions must be positive.')
        return {'processed-image': cv2.warpAffine(image, transform, (width, height), flags=_interpolation(parameters['interpolation']), borderMode=_border_mode(parameters['borderMode']), borderValue=_border_value(parameters['borderValue']))}
    if NODE_ID == 'estimate-perspective-transform':
        source, destination = _matching_points(inputs, minimum=4)
        method = str(parameters['method'])
        methods = {'ransac': cv2.RANSAC, 'lmeds': cv2.LMEDS, 'direct': 0}
        if method not in methods:
            raise ValueError('Perspective estimation method is unsupported.')
        transform, _ = cv2.findHomography(source, destination, method=methods[method], ransacReprojThreshold=float(parameters['ransacThreshold']))
        if transform is None:
            raise ValueError('Perspective transform could not be estimated.')
        return {'transform': transform.astype(np.float32)}
    if NODE_ID == 'distance-transform':
        mask = (_image(inputs, 'mask') > 0).astype(np.uint8)
        metrics = {'l1': cv2.DIST_L1, 'l2': cv2.DIST_L2, 'chessboard': cv2.DIST_C}
        metric = str(parameters['metric'])
        if metric not in metrics:
            raise ValueError('Distance metric is unsupported.')
        mask_size = int(parameters['maskSize'])
        if mask_size not in {3, 5}:
            raise ValueError('Distance mask size must be 3 or 5.')
        return {'distance-map': cv2.distanceTransform(mask, metrics[metric], mask_size).astype(np.float32)}
    if NODE_ID == 'watershed':
        image = _image(inputs)
        mask = (validate_image(inputs.get('mask'), name='Mask') > 0).astype(np.uint8)
        if image.shape[:2] != mask.shape[:2]:
            raise ValueError('Watershed image and mask must have the same shape.')
        if context is not None:
            context.checkpoint()
        canvas = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR) if image.ndim == 2 else image.copy()
        _, markers = cv2.connectedComponents(mask)
        markers = markers.astype(np.int32) + 1
        markers[mask == 0] = 0
        if context is not None:
            context.checkpoint()
        labels = cv2.watershed(canvas, markers)
        if context is not None:
            context.checkpoint()
        return {'segmented-mask': np.where(labels > 1, 255, 0).astype(np.uint8)}
    if NODE_ID == 'convex-hull':
        return {'hulls': [cv2.convexHull(contour) for contour in _contours(inputs)]}
    if NODE_ID == 'contour-metrics':
        metrics = []
        for contour in _contours(inputs):
            area = float(cv2.contourArea(contour))
            perimeter = float(cv2.arcLength(contour, True))
            moments = cv2.moments(contour)
            hull_area = float(cv2.contourArea(cv2.convexHull(contour)))
            metrics.append({'area': area, 'perimeter': perimeter, 'centroidX': float(moments['m10'] / moments['m00']) if moments['m00'] else 0.0, 'centroidY': float(moments['m01'] / moments['m00']) if moments['m00'] else 0.0, 'solidity': area / hull_area if hull_area else 0.0})
        return {'metrics': metrics}
    if NODE_ID in {'image-arithmetic', 'image-bitwise'}:
        image = _image(inputs)
        operand = _image(inputs, 'operand')
        if image.shape != operand.shape:
            raise ValueError('Image and operand must have the same shape.')
        operation = str(parameters['operation'])
        operations = {'image-arithmetic': {'add': cv2.add, 'subtract': cv2.subtract, 'multiply': cv2.multiply}, 'image-bitwise': {'and': cv2.bitwise_and, 'or': cv2.bitwise_or, 'xor': cv2.bitwise_xor}}[NODE_ID]
        if operation not in operations:
            raise ValueError(f'{NODE_ID} operation is unsupported.')
        return {'processed-image': operations[operation](image, operand)}
    raise ValueError(f'Extended OpenCV node {NODE_ID} is not implemented.')

def _array(inputs: NodeInputs, key: str) -> np.ndarray:
    value = inputs.get(key)
    if not isinstance(value, np.ndarray):
        value = np.asarray(value)
    if value.size == 0:
        raise ValueError(f'Input {key} must be a non-empty array.')
    return value

def _image(inputs: NodeInputs, key: str='image') -> np.ndarray:
    return validate_image(_array(inputs, key), name=f'Input {key}')

def _points(inputs: NodeInputs, key: str, *, minimum: int) -> np.ndarray:
    points = np.asarray(inputs.get(key), dtype=np.float32)
    if points.ndim == 3 and points.shape[1:] == (1, 2):
        points = points.reshape(-1, 2)
    if points.ndim != 2 or points.shape[1] != 2 or len(points) < minimum:
        minimum_label = {3: 'three', 4: 'four'}.get(minimum, str(minimum))
        raise ValueError(f'Input {key} must contain at least {minimum_label} two-dimensional points.')
    return points

def _matching_points(inputs: NodeInputs, *, minimum: int) -> tuple[np.ndarray, np.ndarray]:
    source = _points(inputs, 'source-points', minimum=minimum)
    destination = _points(inputs, 'destination-points', minimum=minimum)
    if source.shape != destination.shape:
        raise ValueError('Source and destination points must have the same shape.')
    return (source, destination)

def _interpolation(value: object) -> int:
    try:
        return {'nearest': cv2.INTER_NEAREST, 'linear': cv2.INTER_LINEAR, 'cubic': cv2.INTER_CUBIC}[str(value)]
    except KeyError as error:
        raise ValueError('Interpolation method is unsupported.') from error

def _border_mode(value: object) -> int:
    try:
        return {'constant': cv2.BORDER_CONSTANT, 'replicate': cv2.BORDER_REPLICATE, 'reflect': cv2.BORDER_REFLECT_101, 'wrap': cv2.BORDER_WRAP}[str(value)]
    except KeyError as error:
        raise ValueError('Border mode is unsupported.') from error

def _border_value(value: object) -> tuple[int, int, int]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != 3:
        raise ValueError('Border value must contain three BGR channels.')
    channels = tuple((int(channel) for channel in value))
    if any((channel < 0 or channel > 255 for channel in channels)):
        raise ValueError('Border channels must be between 0 and 255.')
    return channels

def _contours(inputs: NodeInputs) -> list[np.ndarray]:
    contours = inputs.get('contours')
    if not isinstance(contours, list):
        raise ValueError('Input contours must be a list.')
    return [np.asarray(contour, dtype=np.int32) for contour in contours]
