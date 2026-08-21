from __future__ import annotations



from collections.abc import Mapping, Sequence

from typing import Any

import cv2

import numpy as np




from sklearn.naive_bayes import GaussianNB



EPSILON = 1e-9

PIXEL_BATCH_SIZE = 65_536

def _image(inputs: NodeInputs) -> np.ndarray:
    image = inputs.get('image')
    if not isinstance(image, np.ndarray) or image.size == 0 or image.ndim not in {2, 3}:
        raise ValueError('Input image must be a non-empty grayscale or BGR NumPy image.')
    if image.ndim == 3 and image.shape[2] != 3:
        raise ValueError('Input image must contain one grayscale channel or three BGR channels.')
    if not np.isfinite(image).all():
        raise ValueError('Input image must contain only finite values.')
    return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR) if image.ndim == 2 else image

def _object_queries(image: np.ndarray, value: object) -> tuple[np.ndarray, list[dict[str, Any]]]:
    if not isinstance(value, list):
        raise ValueError('Input detections must be a list.')
    height, width = image.shape[:2]
    features: list[np.ndarray] = []
    detections: list[dict[str, Any]] = []
    for index, detection in enumerate(value):
        if not isinstance(detection, Mapping) or not {'x', 'y', 'width', 'height'} <= detection.keys():
            raise ValueError(f'Detection {index} must contain x, y, width, and height.')
        x, y = int(detection['x']), int(detection['y'])
        box_width, box_height = int(detection['width']), int(detection['height'])
        if x < 0 or y < 0 or box_width < 1 or box_height < 1 or x + box_width > width or y + box_height > height:
            raise ValueError(f'Detection {index} bounding box must be inside the image.')
        features.append(image[y:y + box_height, x:x + box_width].reshape(-1, 3).mean(axis=0) / 255.0)
        detections.append(dict(detection))
    return np.asarray(features, dtype=np.float32), detections

def _classified(detections: Sequence[Mapping[str, Any]], probabilities: np.ndarray, classes: Sequence[str]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for detection, row in zip(detections, probabilities, strict=True):
        scores = {label: float(row[index]) for index, label in enumerate(classes)}
        label = max(scores, key=lambda item: (scores[item], item))
        result = dict(detection)
        result.update({'label': label, 'confidence': scores[label], 'classScores': scores})
        output.append(result)
    return output

def _supervised_samples(value: object) -> tuple[np.ndarray, np.ndarray, list[str]]:
    if not isinstance(value, list) or len(value) < 2:
        raise ValueError('Training samples must be a JSON list containing at least two samples.')
    features: list[list[float]] = []
    labels: list[str] = []
    for index, sample in enumerate(value):
        if not isinstance(sample, Mapping):
            raise ValueError(f'Training sample {index} must be an object.')
        label, color = sample.get('label'), sample.get('color')
        if not isinstance(label, str) or not label.strip():
            raise ValueError(f'Training sample {index} requires a non-empty label.')
        if not isinstance(color, list) or len(color) != 3:
            raise ValueError(f'Training sample {index} color must be [B, G, R].')
        vector = np.asarray(color, dtype=np.float64)
        if not np.isfinite(vector).all() or np.any(vector < 0) or np.any(vector > 255):
            raise ValueError(f'Training sample {index} color values must be finite numbers from 0 to 255.')
        labels.append(label.strip())
        features.append((vector / 255.0).tolist())
    classes = sorted(set(labels))
    if len(classes) < 2:
        raise ValueError('Training samples must contain at least two distinct labels.')
    targets = np.asarray([classes.index(label) for label in labels], dtype=np.int64)
    return np.asarray(features, dtype=np.float64), targets, classes

def execute_gaussian_nb(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    image = _image(inputs)
    samples, targets, classes = _supervised_samples(parameters['trainingSamples'])
    queries, detections = _object_queries(image, inputs.get('detections'))
    if not detections:
        return {'classified-detections': []}
    smoothing = float(parameters['varianceSmoothing'])
    if smoothing <= 0:
        raise ValueError('Variance smoothing must be positive.')
    model = GaussianNB(var_smoothing=smoothing).fit(samples, targets)
    return {'classified-detections': _classified(detections, model.predict_proba(queries), classes)}

from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse

NODE_ID = 'gaussian-naive-bayes-object-classifier'
USE = NodeUse.DEBUG
INPUT_KEYS = ('image', 'detections')
OUTPUT_KEYS = ('classified-detections',)


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    return execute_gaussian_nb(inputs, parameters)
