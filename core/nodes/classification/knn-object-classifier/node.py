from __future__ import annotations


from collections import defaultdict

from collections.abc import Mapping, Sequence

from typing import Any

import cv2

import numpy as np







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

def _training_samples(value: object) -> tuple[np.ndarray, list[str]]:
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
        if (
            not isinstance(color, list)
            or len(color) != 3
            or any(isinstance(channel, bool) or not isinstance(channel, (int, float)) for channel in color)
            or any(float(channel) < 0.0 or float(channel) > 255.0 for channel in color)
        ):
            raise ValueError(f'Training sample {index} color must contain three BGR values from 0 to 255.')
        labels.append(label.strip())
        features.append([float(channel) / 255.0 for channel in color])
    return np.asarray(features, dtype=np.float32), labels

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

def _knn_neighbors(queries: np.ndarray, samples: np.ndarray, k: int, metric: str) -> tuple[np.ndarray, np.ndarray]:
    if k < 1 or k > len(samples):
        raise ValueError('Neighbors must be between one and the number of training samples.')
    norms = {'euclidean': cv2.NORM_L2, 'manhattan': cv2.NORM_L1}
    try:
        norm = norms[metric]
    except KeyError as error:
        raise ValueError(f'Unsupported distance metric: {metric}.') from error
    matches = cv2.BFMatcher(norm).knnMatch(
        np.ascontiguousarray(queries, dtype=np.float32),
        np.ascontiguousarray(samples, dtype=np.float32),
        k=k,
    )
    if len(matches) != len(queries) or any(len(row) != k for row in matches):
        raise RuntimeError('OpenCV BFMatcher could not return the requested K nearest neighbors.')
    indices = np.asarray([[match.trainIdx for match in row] for row in matches], dtype=np.int64)
    distances = np.asarray([[match.distance for match in row] for row in matches], dtype=np.float32)
    return indices, distances

def _knn_vote(indices: np.ndarray, distances: np.ndarray, labels: Sequence[str], weighted: bool) -> tuple[list[str], np.ndarray]:
    predictions: list[str] = []
    confidences = np.empty(len(indices), dtype=np.float32)
    for row_index, (row_indices, row_distances) in enumerate(zip(indices, distances, strict=True)):
        weights = 1.0 / np.maximum(row_distances, EPSILON) if weighted else np.ones_like(row_distances)
        totals: dict[str, float] = defaultdict(float)
        closest: dict[str, float] = defaultdict(lambda: float('inf'))
        for sample_index, distance, weight in zip(row_indices, row_distances, weights, strict=True):
            label = labels[int(sample_index)]
            totals[label] += float(weight)
            closest[label] = min(closest[label], float(distance))
        winner = min(totals, key=lambda label: (-totals[label], closest[label], label))
        predictions.append(winner)
        confidences[row_index] = totals[winner] / max(sum(totals.values()), EPSILON)
    return predictions, confidences

def _knn_classify(queries: np.ndarray, samples: np.ndarray, labels: Sequence[str], parameters: NodeParameters) -> tuple[list[str], np.ndarray, np.ndarray, np.ndarray]:
    indices, distances = _knn_neighbors(queries, samples, int(parameters['neighbors']), str(parameters['distanceMetric']))
    predictions, confidences = _knn_vote(indices, distances, labels, bool(parameters['distanceWeighted']))
    return predictions, confidences, indices, distances

def _knn_object_validate(parameters: NodeParameters, sample_count: int) -> None:
    k = int(parameters['neighbors'])
    if k < 1:
        raise ValueError('Neighbors must be at least one.')
    if k > sample_count:
        raise ValueError('Neighbors cannot exceed the number of training samples.')

def execute_knn_object(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    image = _image(inputs)
    samples, labels = _training_samples(parameters['trainingSamples'])
    _knn_object_validate(parameters, len(samples))
    queries, detections = _object_queries(image, inputs.get('detections'))
    if not detections:
        return {'classified-detections': []}
    predictions, confidences, indices, distances = _knn_classify(queries, samples, labels, parameters)
    output: list[dict[str, Any]] = []
    for detection, label, confidence, row_indices, row_distances in zip(detections, predictions, confidences, indices, distances, strict=True):
        result = dict(detection)
        result.update({
            'label': label,
            'confidence': float(confidence),
            'neighbors': [
                {'label': labels[int(sample_index)], 'distance': float(distance)}
                for sample_index, distance in zip(row_indices, row_distances, strict=True)
            ],
        })
        output.append(result)
    return {'classified-detections': output}

from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse

NODE_ID = 'knn-object-classifier'
USE = NodeUse.DEBUG
INPUT_KEYS = ('image', 'detections')
OUTPUT_KEYS = ('classified-detections',)


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    return execute_knn_object(inputs, parameters)
