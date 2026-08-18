from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

import cv2
import numpy as np

from .models import NodeInputs, NodeOutputs, NodeParameters


_EPSILON = 1e-12
_PIXEL_BATCH_SIZE = 65_536


def _image(inputs: NodeInputs) -> np.ndarray:
    image = inputs.get('image')
    if not isinstance(image, np.ndarray) or image.size == 0 or image.ndim not in {2, 3}:
        raise ValueError('Input image must be a non-empty grayscale or BGR NumPy image.')
    if image.ndim == 3 and image.shape[2] != 3:
        raise ValueError('Input image must have one grayscale channel or three BGR channels.')
    return image


def _bgr(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    return image


def _training_samples(value: object) -> tuple[np.ndarray, list[str]]:
    if not isinstance(value, list) or not value:
        raise ValueError('Training samples must be a non-empty JSON list.')
    features: list[list[float]] = []
    labels: list[str] = []
    for index, sample in enumerate(value):
        if not isinstance(sample, Mapping):
            raise ValueError(f'Training sample {index} must be an object.')
        label = sample.get('label')
        color = sample.get('color')
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


def _validate_k(parameters: NodeParameters, sample_count: int) -> int:
    k = int(parameters['neighbors'])
    if k < 1:
        raise ValueError('Neighbors must be at least one.')
    if k > sample_count:
        raise ValueError('Neighbors cannot exceed the number of training samples.')
    return k


def _manual_neighbors(
    queries: np.ndarray,
    samples: np.ndarray,
    k: int,
    metric: str,
) -> tuple[np.ndarray, np.ndarray]:
    differences = queries[:, None, :] - samples[None, :, :]
    if metric == 'euclidean':
        distances = np.sqrt(np.sum(differences * differences, axis=2))
    elif metric == 'manhattan':
        distances = np.sum(np.abs(differences), axis=2)
    else:
        raise ValueError(f'Unsupported manual KNN distance metric: {metric}.')
    indices = np.argpartition(distances, kth=k - 1, axis=1)[:, :k]
    selected_distances = np.take_along_axis(distances, indices, axis=1)
    order = np.argsort(selected_distances, axis=1, kind='stable')
    return np.take_along_axis(indices, order, axis=1), np.take_along_axis(selected_distances, order, axis=1)


def _opencv_neighbors(
    queries: np.ndarray,
    samples: np.ndarray,
    k: int,
) -> tuple[np.ndarray, np.ndarray]:
    matches = cv2.BFMatcher(cv2.NORM_L2).knnMatch(queries, samples, k=k)
    if len(matches) != len(queries) or any(len(row) != k for row in matches):
        raise RuntimeError('OpenCV BFMatcher could not return the requested K nearest neighbors.')
    neighbor_ids = np.asarray([[match.trainIdx for match in row] for row in matches], dtype=np.int64)
    distances = np.asarray([[match.distance for match in row] for row in matches], dtype=np.float32)
    return neighbor_ids, distances


def _neighbors(
    queries: np.ndarray,
    samples: np.ndarray,
    k: int,
    implementation: str,
    metric: str,
) -> tuple[np.ndarray, np.ndarray]:
    queries = np.ascontiguousarray(queries, dtype=np.float32)
    if implementation == 'opencv':
        if metric != 'euclidean':
            raise ValueError('The OpenCV implementation supports only Euclidean distance.')
        return _opencv_neighbors(queries, samples, k)
    if implementation == 'manual-python':
        return _manual_neighbors(queries, samples, k, metric)
    raise ValueError(f'Unsupported KNN implementation: {implementation}.')


def _vote(
    neighbor_indices: np.ndarray,
    distances: np.ndarray,
    labels: Sequence[str],
    weighted: bool,
) -> tuple[list[str], np.ndarray]:
    predictions: list[str] = []
    confidences = np.empty(len(neighbor_indices), dtype=np.float32)
    for row_index, (indices, row_distances) in enumerate(zip(neighbor_indices, distances, strict=True)):
        weights = 1.0 / np.maximum(row_distances, _EPSILON) if weighted else np.ones_like(row_distances)
        totals: dict[str, float] = defaultdict(float)
        closest: dict[str, float] = defaultdict(lambda: float('inf'))
        for sample_index, distance, weight in zip(indices, row_distances, weights, strict=True):
            label = labels[int(sample_index)]
            totals[label] += float(weight)
            closest[label] = min(closest[label], float(distance))
        winner = min(totals, key=lambda label: (-totals[label], closest[label], label))
        predictions.append(winner)
        confidences[row_index] = totals[winner] / max(sum(totals.values()), _EPSILON)
    return predictions, confidences


def _classify(
    queries: np.ndarray,
    samples: np.ndarray,
    labels: Sequence[str],
    parameters: NodeParameters,
) -> tuple[list[str], np.ndarray, np.ndarray, np.ndarray]:
    k = _validate_k(parameters, len(samples))
    indices, distances = _neighbors(
        queries, samples, k, str(parameters['implementation']), str(parameters['distanceMetric']),
    )
    predictions, confidences = _vote(indices, distances, labels, bool(parameters['distanceWeighted']))
    return predictions, confidences, indices, distances


def classify_objects(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    image = _bgr(_image(inputs))
    detections = inputs.get('detections')
    if not isinstance(detections, list):
        raise ValueError('Input detections must be a list.')
    samples, labels = _training_samples(parameters['trainingSamples'])
    _validate_k(parameters, len(samples))
    if not detections:
        return {'classified-detections': []}

    height, width = image.shape[:2]
    features: list[np.ndarray] = []
    normalized_detections: list[dict[str, Any]] = []
    for index, detection in enumerate(detections):
        if not isinstance(detection, Mapping) or not {'x', 'y', 'width', 'height'} <= detection.keys():
            raise ValueError(f'Detection {index} must contain x, y, width, and height.')
        x, y = int(detection['x']), int(detection['y'])
        box_width, box_height = int(detection['width']), int(detection['height'])
        if x < 0 or y < 0 or box_width < 1 or box_height < 1 or x + box_width > width or y + box_height > height:
            raise ValueError(f'Detection {index} bounding box must be inside the image.')
        features.append(image[y:y + box_height, x:x + box_width].reshape(-1, 3).mean(axis=0) / 255.0)
        normalized_detections.append(dict(detection))

    query_features = np.asarray(features, dtype=np.float32)
    predictions, confidences, neighbor_indices, distances = _classify(query_features, samples, labels, parameters)
    output: list[dict[str, Any]] = []
    for detection, label, confidence, indices, row_distances in zip(
        normalized_detections, predictions, confidences, neighbor_indices, distances, strict=True,
    ):
        detection.update({
            'label': label,
            'confidence': float(confidence),
            'neighbors': [
                {'label': labels[int(sample_index)], 'distance': float(distance)}
                for sample_index, distance in zip(indices, row_distances, strict=True)
            ],
        })
        output.append(detection)
    return {'classified-detections': output}


def segment_image(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    image = _bgr(_image(inputs))
    samples, labels = _training_samples(parameters['trainingSamples'])
    foreground_labels = parameters['foregroundLabels']
    if not isinstance(foreground_labels, list) or not foreground_labels or not all(
        isinstance(label, str) and label for label in foreground_labels
    ):
        raise ValueError('Foreground labels must be a non-empty JSON list of labels.')
    unknown_labels = set(foreground_labels) - set(labels)
    if unknown_labels:
        raise ValueError(f'Foreground labels are missing from training samples: {sorted(unknown_labels)}.')
    minimum_confidence = float(parameters['minimumConfidence'])
    if minimum_confidence < 0.0 or minimum_confidence > 1.0:
        raise ValueError('Minimum confidence must be between zero and one.')

    pixels = image.reshape(-1, 3).astype(np.float32) / 255.0
    mask_values = np.zeros(len(pixels), dtype=np.uint8)
    foreground = set(foreground_labels)
    for start in range(0, len(pixels), _PIXEL_BATCH_SIZE):
        stop = min(start + _PIXEL_BATCH_SIZE, len(pixels))
        predictions, confidences, _, _ = _classify(pixels[start:stop], samples, labels, parameters)
        mask_values[start:stop] = np.fromiter(
            (255 if label in foreground and confidence >= minimum_confidence else 0 for label, confidence in zip(predictions, confidences, strict=True)),
            dtype=np.uint8,
            count=stop - start,
        )
    mask = mask_values.reshape(image.shape[:2])
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return {'mask': mask, 'contours': contours}