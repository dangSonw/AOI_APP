from __future__ import annotations

from collections.abc import Mapping
import cv2
import numpy as np
from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse

NODE_ID = 'resize'
USE = NodeUse.DEBUG
INPUT_KEYS = ('image',)
OUTPUT_KEYS = ('processed-image',)

def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    image = _image(inputs, 'mask' if NODE_ID in {'erode', 'dilate', 'morphology-operation', 'find-contours', 'hough-lines', 'connected-components'} else 'image')
    if NODE_ID == 'resize':
        return {'processed-image': cv2.resize(image, (int(parameters['width']), int(parameters['height'])), interpolation=_interpolation(parameters['interpolation']))}
    if NODE_ID == 'color-conversion':
        conversions = {'bgr-to-gray': cv2.COLOR_BGR2GRAY, 'bgr-to-rgb': cv2.COLOR_BGR2RGB, 'bgr-to-hsv': cv2.COLOR_BGR2HSV, 'rgb-to-gray': cv2.COLOR_RGB2GRAY}
        return {'processed-image': cv2.cvtColor(image, conversions[str(parameters['mode'])])}
    if NODE_ID == 'normalize':
        return {'processed-image': cv2.normalize(image, None, float(parameters['alpha']), float(parameters['beta']), cv2.NORM_MINMAX)}
    if NODE_ID == 'clahe':
        gray = _gray(_uint8(image))
        clahe = cv2.createCLAHE(float(parameters['clipLimit']), (int(parameters['tileGridSize']),) * 2)
        return {'processed-image': clahe.apply(gray)}
    if NODE_ID == 'gaussian-blur':
        size = _odd(parameters['kernelSize'])
        return {'processed-image': cv2.GaussianBlur(image, (size, size), float(parameters['sigma']))}
    if NODE_ID == 'median-blur':
        return {'processed-image': cv2.medianBlur(image, _odd(parameters['kernelSize'], minimum=3))}
    if NODE_ID == 'bilateral-filter':
        return {'processed-image': cv2.bilateralFilter(image, int(parameters['diameter']), float(parameters['sigmaColor']), float(parameters['sigmaSpace']))}
    if NODE_ID == 'global-threshold':
        _, mask = cv2.threshold(_gray(_uint8(image)), float(parameters['threshold']), 255, cv2.THRESH_BINARY)
        return {'mask': mask}
    if NODE_ID == 'otsu-threshold':
        _, mask = cv2.threshold(_gray(_uint8(image)), 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        return {'mask': mask}
    if NODE_ID == 'adaptive-threshold':
        mask = cv2.adaptiveThreshold(_gray(_uint8(image)), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, _odd(parameters['blockSize'], minimum=3), float(parameters['constant']))
        return {'mask': mask}
    if NODE_ID in {'erode', 'dilate'}:
        operation = cv2.erode if NODE_ID == 'erode' else cv2.dilate
        return {'processed-mask': operation(_uint8(image), np.ones((3, 3), np.uint8), iterations=int(parameters['iterations']))}
    if NODE_ID == 'morphology-operation':
        operations = {'open': cv2.MORPH_OPEN, 'close': cv2.MORPH_CLOSE, 'gradient': cv2.MORPH_GRADIENT, 'top-hat': cv2.MORPH_TOPHAT, 'black-hat': cv2.MORPH_BLACKHAT}
        return {'processed-mask': cv2.morphologyEx(_uint8(image), operations[str(parameters['operation'])], _kernel(parameters['kernelSize']))}
    if NODE_ID == 'canny-edges':
        return {'mask': cv2.Canny(_gray(_uint8(image)), float(parameters['lowThreshold']), float(parameters['highThreshold']))}
    if NODE_ID in {'sobel-gradient', 'scharr-gradient', 'laplacian'}:
        gray = _gray(image)
        if NODE_ID == 'sobel-gradient':
            gradient = cv2.Sobel(gray, cv2.CV_32F, int(parameters['dx']), int(parameters['dy']), ksize=3)
        elif NODE_ID == 'scharr-gradient':
            axis = str(parameters['axis'])
            gradient = cv2.Scharr(gray, cv2.CV_32F, 1 if axis == 'x' else 0, 1 if axis == 'y' else 0)
        else:
            gradient = cv2.Laplacian(gray, cv2.CV_32F, ksize=_odd(parameters['kernelSize']))
        return {'processed-image': cv2.convertScaleAbs(gradient)}
    if NODE_ID == 'find-contours':
        modes = {'external': cv2.RETR_EXTERNAL, 'list': cv2.RETR_LIST, 'tree': cv2.RETR_TREE}
        contours, _ = cv2.findContours(_uint8(image), modes[str(parameters['retrieval'])], cv2.CHAIN_APPROX_SIMPLE)
        return {'contours': contours}
    if NODE_ID == 'connected-components':
        return {'detections': _detections_from_components(image)}
    if NODE_ID == 'hough-lines':
        lines = cv2.HoughLinesP(_uint8(image), 1, np.pi / 180, int(parameters['threshold']), minLineLength=10, maxLineGap=5)
        detections = [] if lines is None else [{'x1': int(line[0][0]), 'y1': int(line[0][1]), 'x2': int(line[0][2]), 'y2': int(line[0][3])} for line in lines]
        return {'detections': detections}
    if NODE_ID == 'hough-circles':
        circles = cv2.HoughCircles(_gray(_uint8(image)), cv2.HOUGH_GRADIENT, 1.2, 10, minRadius=int(parameters['minimumRadius']), maxRadius=int(parameters['maximumRadius']))
        detections = [] if circles is None else [{'centerX': int(round(x)), 'centerY': int(round(y)), 'radius': int(round(radius))} for x, y, radius in circles[0]]
        return {'detections': detections}
    if NODE_ID == 'feature-detection-and-matching':
        keypoints, transform = _feature_registration(image, _image(inputs, 'reference'), str(parameters['detector']))
        return {'keypoints': keypoints, 'transform': transform}
    if NODE_ID == 'homography-registration':
        _, transform = _feature_registration(image, _image(inputs, 'reference'), 'orb')
        reference = _image(inputs, 'reference')
        registered = cv2.warpPerspective(image, transform, (reference.shape[1], reference.shape[0]))
        return {'registered-image': registered, 'transform': transform}
    if NODE_ID == 'ecc-registration':
        registered, transform = _ecc_registration(image, _image(inputs, 'reference'), str(parameters['motionModel']), int(parameters['iterations']))
        return {'registered-image': registered, 'transform': transform}
    if NODE_ID == 'crop-image':
        x, y = (int(parameters['x']), int(parameters['y']))
        width, height = (int(parameters['width']), int(parameters['height']))
        if x < 0 or y < 0 or width < 1 or (height < 1) or (x + width > image.shape[1]) or (y + height > image.shape[0]):
            raise ValueError('Crop region must be fully inside the source image.')
        return {'processed-image': image[y:y + height, x:x + width].copy()}
    if NODE_ID == 'flip-image':
        flip_code = {'horizontal': 1, 'vertical': 0, 'both': -1}[str(parameters['axis'])]
        return {'processed-image': cv2.flip(image, flip_code)}
    if NODE_ID == 'rotate-image':
        angle = float(parameters['angleDegrees'])
        scale = float(parameters['scale'])
        center = (image.shape[1] / 2.0, image.shape[0] / 2.0)
        transform = cv2.getRotationMatrix2D(center, angle, scale)
        width, height = (image.shape[1], image.shape[0])
        if bool(parameters['expandCanvas']):
            cosine, sine = (abs(transform[0, 0]), abs(transform[0, 1]))
            width = max(1, int(round(image.shape[0] * sine + image.shape[1] * cosine)))
            height = max(1, int(round(image.shape[0] * cosine + image.shape[1] * sine)))
            transform[0, 2] += width / 2.0 - center[0]
            transform[1, 2] += height / 2.0 - center[1]
        rotated = cv2.warpAffine(image, transform, (width, height), flags=_interpolation(parameters['interpolation']), borderMode=_border_mode(parameters['borderMode']), borderValue=_color(parameters['borderValue'], name='Border value'))
        return {'processed-image': rotated}
    if NODE_ID == 'pad-image':
        padding = tuple((int(parameters[key]) for key in ('top', 'bottom', 'left', 'right')))
        if any((value < 0 for value in padding)):
            raise ValueError('Padding values cannot be negative.')
        top, bottom, left, right = padding
        padded = cv2.copyMakeBorder(image, top, bottom, left, right, _border_mode(parameters['borderMode']), value=_color(parameters['borderValue'], name='Border value'))
        return {'processed-image': padded}
    if NODE_ID == 'warp-perspective':
        transform = inputs.get('transform')
        if not isinstance(transform, np.ndarray) or transform.shape != (3, 3):
            raise ValueError('Input transform must be a 3 by 3 NumPy matrix.')
        warped = cv2.warpPerspective(image, transform.astype(np.float64), (int(parameters['width']), int(parameters['height'])), flags=_interpolation(parameters['interpolation']), borderMode=_border_mode(parameters['borderMode']), borderValue=_color(parameters['borderValue'], name='Border value'))
        return {'processed-image': warped}
    if NODE_ID == 'histogram-equalization':
        source = _uint8(image)
        if str(parameters['mode']) == 'grayscale':
            return {'processed-image': cv2.equalizeHist(_gray(source))}
        if source.ndim != 3 or source.shape[2] != 3:
            raise ValueError('Luminance equalization requires a three-channel BGR image.')
        luminance = cv2.cvtColor(source, cv2.COLOR_BGR2YCrCb)
        luminance[:, :, 0] = cv2.equalizeHist(luminance[:, :, 0])
        return {'processed-image': cv2.cvtColor(luminance, cv2.COLOR_YCrCb2BGR)}
    if NODE_ID == 'gamma-correction':
        gamma = float(parameters['gamma'])
        if gamma <= 0:
            raise ValueError('Gamma must be greater than zero.')
        lookup = np.clip((np.arange(256, dtype=np.float32) / 255.0) ** gamma * 255.0, 0, 255).astype(np.uint8)
        return {'processed-image': cv2.LUT(_uint8(image), lookup)}
    if NODE_ID == 'in-range-mask':
        color_space = str(parameters['colorSpace'])
        converted = {'bgr': lambda value: value, 'hsv': lambda value: cv2.cvtColor(value, cv2.COLOR_BGR2HSV), 'lab': lambda value: cv2.cvtColor(value, cv2.COLOR_BGR2LAB), 'grayscale': _gray}[color_space](_uint8(image))
        channel_count = 1 if converted.ndim == 2 else converted.shape[2]
        lower = parameters['lowerBound']
        upper = parameters['upperBound']
        if not isinstance(lower, list) or not isinstance(upper, list) or len(lower) != channel_count or (len(upper) != channel_count):
            raise ValueError('Range bounds must match the selected color-space channel count.')
        return {'mask': cv2.inRange(converted, np.array(lower, dtype=np.uint8), np.array(upper, dtype=np.uint8))}
    if NODE_ID == 'apply-mask':
        mask = _uint8(_image(inputs, 'mask'))
        _same_spatial_shape(image, mask, name='Mask')
        return {'processed-image': cv2.bitwise_and(image, image, mask=mask)}
    if NODE_ID == 'blend-images':
        overlay = _image(inputs, 'overlay')
        if image.shape != overlay.shape:
            raise ValueError('Overlay must match image shape and channel count.')
        alpha = float(parameters['alpha'])
        if alpha < 0.0 or alpha > 1.0:
            raise ValueError('Blend alpha must be between zero and one.')
        return {'processed-image': cv2.addWeighted(image, 1.0 - alpha, overlay, alpha, 0.0)}
    if NODE_ID == 'overlay-mask':
        mask = _uint8(_image(inputs, 'mask'))
        _same_spatial_shape(image, mask, name='Mask')
        canvas = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR) if image.ndim == 2 else image.copy()
        opacity = float(parameters['opacity'])
        if opacity < 0.0 or opacity > 1.0:
            raise ValueError('Mask opacity must be between zero and one.')
        overlay = np.empty_like(canvas)
        overlay[:] = _color(parameters['color'], name='Overlay color')
        selected = mask > 0
        canvas[selected] = cv2.addWeighted(canvas, 1.0 - opacity, overlay, opacity, 0.0)[selected]
        return {'annotated-image': canvas}
    if NODE_ID == 'draw-contours':
        contours = inputs.get('contours')
        if not isinstance(contours, list):
            raise ValueError('Input contours must be a list.')
        canvas = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR) if image.ndim == 2 else image.copy()
        contour_index = -1 if bool(parameters['drawAll']) else int(parameters['contourIndex'])
        if contour_index >= len(contours):
            raise ValueError('Contour index is outside the available contour list.')
        cv2.drawContours(canvas, contours, contour_index, _color(parameters['color'], name='Contour color'), int(parameters['thickness']), lineType=cv2.LINE_AA)
        return {'annotated-image': canvas}
    raise ValueError(f'OpenCV node {NODE_ID} is not implemented by the shared runtime.')

def _image(inputs: NodeInputs, key: str='image') -> np.ndarray:
    value = inputs.get(key)
    if not isinstance(value, np.ndarray) or value.size == 0:
        raise ValueError(f'Input {key} must be a non-empty NumPy image.')
    return value

def _gray(image: np.ndarray) -> np.ndarray:
    return image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

def _uint8(image: np.ndarray) -> np.ndarray:
    if image.dtype == np.uint8:
        return image
    return cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

def _odd(value: object, *, minimum: int=1) -> int:
    number = max(minimum, int(value))
    return number if number % 2 else number + 1

def _kernel(size: object) -> np.ndarray:
    width = _odd(size)
    return cv2.getStructuringElement(cv2.MORPH_RECT, (width, width))

def _interpolation(value: object) -> int:
    return {'nearest': cv2.INTER_NEAREST, 'linear': cv2.INTER_LINEAR, 'cubic': cv2.INTER_CUBIC, 'area': cv2.INTER_AREA}[str(value)]

def _border_mode(value: object) -> int:
    return {'constant': cv2.BORDER_CONSTANT, 'replicate': cv2.BORDER_REPLICATE, 'reflect': cv2.BORDER_REFLECT_101, 'wrap': cv2.BORDER_WRAP}[str(value)]

def _color(value: object, *, name: str) -> tuple[int, int, int]:
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f'{name} must contain three BGR channel values.')
    channels = tuple((int(channel) for channel in value))
    if any((channel < 0 or channel > 255 for channel in channels)):
        raise ValueError(f'{name} channels must be between 0 and 255.')
    return channels

def _same_spatial_shape(first: np.ndarray, second: np.ndarray, *, name: str) -> None:
    if first.shape[:2] != second.shape[:2]:
        raise ValueError(f'{name} must match image width and height.')

def _detections_from_components(mask: np.ndarray) -> list[dict[str, float | int]]:
    count, _, stats, centroids = cv2.connectedComponentsWithStats((_uint8(mask) > 0).astype(np.uint8), connectivity=8)
    return [{'x': int(stats[index, cv2.CC_STAT_LEFT]), 'y': int(stats[index, cv2.CC_STAT_TOP]), 'width': int(stats[index, cv2.CC_STAT_WIDTH]), 'height': int(stats[index, cv2.CC_STAT_HEIGHT]), 'area': int(stats[index, cv2.CC_STAT_AREA]), 'centroidX': float(centroids[index, 0]), 'centroidY': float(centroids[index, 1])} for index in range(1, count)]

def _feature_registration(image: np.ndarray, reference: np.ndarray, detector_name: str) -> tuple[list[dict[str, float]], np.ndarray]:
    gray_image = _gray(image)
    gray_reference = _gray(reference)
    if detector_name == 'sift':
        detector = cv2.SIFT_create()
        norm = cv2.NORM_L2
    elif detector_name == 'akaze':
        detector = cv2.AKAZE_create()
        norm = cv2.NORM_HAMMING
    else:
        detector = cv2.ORB_create(nfeatures=2000)
        norm = cv2.NORM_HAMMING
    image_points, image_descriptors = detector.detectAndCompute(gray_image, None)
    reference_points, reference_descriptors = detector.detectAndCompute(gray_reference, None)
    if image_descriptors is None or reference_descriptors is None:
        raise ValueError('Feature registration could not find descriptors.')
    pairs = cv2.BFMatcher(norm).knnMatch(image_descriptors, reference_descriptors, k=2)
    matches = [first for first, second in pairs if first.distance < 0.75 * second.distance]
    if len(matches) < 4:
        raise ValueError('Feature registration requires at least four reliable matches.')
    source = np.float32([image_points[item.queryIdx].pt for item in matches]).reshape(-1, 1, 2)
    target = np.float32([reference_points[item.trainIdx].pt for item in matches]).reshape(-1, 1, 2)
    transform, _ = cv2.findHomography(source, target, cv2.RANSAC, 3.0)
    if transform is None:
        raise ValueError('Feature registration could not estimate a homography.')
    keypoints = [{'x': float(point.pt[0]), 'y': float(point.pt[1])} for point in image_points]
    return (keypoints, transform)

def _ecc_registration(image: np.ndarray, reference: np.ndarray, motion_model: str, iterations: int) -> tuple[np.ndarray, np.ndarray]:
    models = {'translation': cv2.MOTION_TRANSLATION, 'euclidean': cv2.MOTION_EUCLIDEAN, 'affine': cv2.MOTION_AFFINE, 'homography': cv2.MOTION_HOMOGRAPHY}
    model = models[motion_model]
    transform = np.eye(3, dtype=np.float32) if model == cv2.MOTION_HOMOGRAPHY else np.eye(2, 3, dtype=np.float32)
    cv2.findTransformECC(_gray(reference).astype(np.float32) / 255.0, _gray(image).astype(np.float32) / 255.0, transform, model, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, iterations, 1e-06))
    size = (reference.shape[1], reference.shape[0])
    if model == cv2.MOTION_HOMOGRAPHY:
        registered = cv2.warpPerspective(image, transform, size, flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP)
    else:
        registered = cv2.warpAffine(image, transform, size, flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP)
    return (registered, transform)

def draw_detections(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    canvas = _image(inputs).copy()
    if canvas.ndim == 2:
        canvas = cv2.cvtColor(canvas, cv2.COLOR_GRAY2BGR)
    color = _color(parameters.get('color', [0, 255, 0]), name='Detection color')
    thickness = int(parameters.get('thickness', 2))
    show_labels = bool(parameters.get('showLabels', True))
    detections = inputs.get('detections', [])
    if not isinstance(detections, list):
        raise ValueError('Input detections must be a list.')
    for detection in detections:
        if not isinstance(detection, Mapping):
            continue
        if {'x', 'y', 'width', 'height'} <= detection.keys():
            x, y = (int(detection['x']), int(detection['y']))
            width, height = (int(detection['width']), int(detection['height']))
            cv2.rectangle(canvas, (x, y), (x + width - 1, y + height - 1), color, thickness)
            if show_labels:
                label = str(detection.get('label', f'Area {detection.get('area', width * height)}'))
                cv2.putText(canvas, label, (x, max(12, y - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA)
        elif {'centerX', 'centerY', 'radius'} <= detection.keys():
            cv2.circle(canvas, (int(detection['centerX']), int(detection['centerY'])), int(detection['radius']), color, thickness)
        elif {'x1', 'y1', 'x2', 'y2'} <= detection.keys():
            cv2.line(canvas, (int(detection['x1']), int(detection['y1'])), (int(detection['x2']), int(detection['y2'])), color, thickness)
    return {'annotated-image': canvas}

def mask_coverage_score(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    mask = _image(inputs, 'mask')
    score = float(np.count_nonzero(mask)) / float(mask.size)
    return {'score': min(max(score, 0.0), 1.0)}
