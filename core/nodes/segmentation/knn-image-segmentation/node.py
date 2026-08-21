from __future__ import annotations

from collections import defaultdict

from collections.abc import Mapping, Sequence


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

def execute_knn_segmentation(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    image = _image(inputs)
    samples, labels = _training_samples(parameters['trainingSamples'])
    foreground_labels = parameters['foregroundLabels']
    if not isinstance(foreground_labels, list) or not foreground_labels or not all(isinstance(label, str) and label for label in foreground_labels):
        raise ValueError('Foreground labels must be a non-empty JSON list of labels.')
    unknown_labels = set(foreground_labels) - set(labels)
    if unknown_labels:
        raise ValueError(f'Foreground labels are missing from training samples: {sorted(unknown_labels)}.')
    minimum_confidence = float(parameters['minimumConfidence'])
    if not 0.0 <= minimum_confidence <= 1.0:
        raise ValueError('Minimum confidence must be between zero and one.')
    pixels = image.reshape(-1, 3).astype(np.float32) / 255.0
    mask_values = np.zeros(len(pixels), dtype=np.uint8)
    foreground = set(foreground_labels)
    for start in range(0, len(pixels), PIXEL_BATCH_SIZE):
        stop = min(start + PIXEL_BATCH_SIZE, len(pixels))
        predictions, confidences, _, _ = _knn_classify(pixels[start:stop], samples, labels, parameters)
        mask_values[start:stop] = np.fromiter(
            (255 if label in foreground and confidence >= minimum_confidence else 0 for label, confidence in zip(predictions, confidences, strict=True)),
            dtype=np.uint8,
            count=stop - start,
        )
    mask = mask_values.reshape(image.shape[:2])
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return {'mask': mask, 'contours': list(contours)}

from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse

NODE_ID = 'knn-image-segmentation'
USE = NodeUse.DEBUG
INPUT_KEYS = ('image',)
OUTPUT_KEYS = ('mask', 'contours')


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    return execute_knn_segmentation(inputs, parameters)
