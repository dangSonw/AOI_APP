from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import cv2
import numpy as np

from .models import NodeInputs, NodeOutputs, NodeParameters


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


def _implementation(parameters: NodeParameters) -> str:
    implementation = str(parameters['implementation'])
    if implementation not in {'scikit-learn', 'manual-python'}:
        raise ValueError(f'Unsupported implementation: {implementation}.')
    return implementation


def _sklearn(module: str, name: str) -> type:
    try:
        imported = __import__(module, fromlist=[name])
        return getattr(imported, name)
    except (ImportError, AttributeError) as error:
        raise RuntimeError(
            'The scikit-learn implementation requires scikit-learn==1.7.1. '
            'Install backend/requirements.txt or choose manual-python.',
        ) from error


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
        raise ValueError('Classifier training samples must contain at least two distinct labels.')
    class_to_index = {label: index for index, label in enumerate(classes)}
    return np.asarray(features, dtype=np.float64), np.asarray([class_to_index[label] for label in labels]), classes


def _normal_samples(value: object) -> np.ndarray:
    if not isinstance(value, list) or len(value) < 2:
        raise ValueError('Normal training samples must contain at least two feature vectors.')
    vectors: list[list[float]] = []
    for index, sample in enumerate(value):
        if not isinstance(sample, Mapping) or not isinstance(sample.get('features'), list):
            raise ValueError(f'Normal sample {index} must contain a features list.')
        vector = np.asarray(sample['features'], dtype=np.float64)
        if vector.shape != (3,) or not np.isfinite(vector).all():
            raise ValueError(f'Normal sample {index} features must contain three finite BGR values.')
        if np.any(vector < 0) or np.any(vector > 255):
            raise ValueError(f'Normal sample {index} features must be between 0 and 255.')
        vectors.append((vector / 255.0).tolist())
    return np.asarray(vectors, dtype=np.float64)


def _object_queries(image: np.ndarray, detections: object) -> tuple[np.ndarray, list[dict[str, Any]]]:
    if not isinstance(detections, list):
        raise ValueError('Input detections must be a list.')
    height, width = image.shape[:2]
    queries: list[np.ndarray] = []
    copied: list[dict[str, Any]] = []
    for index, detection in enumerate(detections):
        if not isinstance(detection, Mapping) or not {'x', 'y', 'width', 'height'} <= detection.keys():
            raise ValueError(f'Detection {index} must contain x, y, width, and height.')
        x, y = int(detection['x']), int(detection['y'])
        box_width, box_height = int(detection['width']), int(detection['height'])
        if x < 0 or y < 0 or box_width < 1 or box_height < 1 or x + box_width > width or y + box_height > height:
            raise ValueError(f'Detection {index} bounding box must be inside the image.')
        queries.append(image[y:y + box_height, x:x + box_width].reshape(-1, 3).mean(axis=0) / 255.0)
        copied.append(dict(detection))
    return np.asarray(queries, dtype=np.float64).reshape(-1, 3), copied


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits, axis=1, keepdims=True)
    exponentials = np.exp(shifted)
    return exponentials / np.maximum(exponentials.sum(axis=1, keepdims=True), EPSILON)


def _classified(detections: list[dict[str, Any]], probabilities: np.ndarray, classes: Sequence[str]) -> NodeOutputs:
    output: list[dict[str, Any]] = []
    for detection, row in zip(detections, probabilities, strict=True):
        class_index = int(np.argmax(row))
        detection.update({
            'label': classes[class_index],
            'confidence': float(np.clip(row[class_index], 0.0, 1.0)),
            'classScores': {label: float(np.clip(row[index], 0.0, 1.0)) for index, label in enumerate(classes)},
        })
        output.append(detection)
    return {'classified-detections': output}


def kmeans_segment(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    image = _image(inputs)
    color_space = str(parameters['colorSpace'])
    conversions = {'bgr': None, 'lab': cv2.COLOR_BGR2LAB, 'hsv': cv2.COLOR_BGR2HSV}
    if color_space not in conversions:
        raise ValueError(f'Unsupported color space: {color_space}.')
    converted = image if conversions[color_space] is None else cv2.cvtColor(image, conversions[color_space])
    pixels = converted.reshape(-1, 3).astype(np.float64) / 255.0
    clusters = int(parameters['clusters'])
    if clusters < 2 or clusters > len(pixels):
        raise ValueError('Clusters must be at least two and cannot exceed the pixel count.')
    seed, iterations, tolerance = int(parameters['randomSeed']), int(parameters['maximumIterations']), float(parameters['tolerance'])
    maximum_pixels = int(parameters['maximumTrainingPixels'])
    rng = np.random.default_rng(seed)
    training = pixels if len(pixels) <= maximum_pixels else pixels[rng.choice(len(pixels), maximum_pixels, replace=False)]
    if _implementation(parameters) == 'scikit-learn':
        KMeans = _sklearn('sklearn.cluster', 'KMeans')
        model = KMeans(n_clusters=clusters, init='k-means++', n_init=10, max_iter=iterations, tol=tolerance, random_state=seed)
        model.fit(training)
        labels = np.concatenate([model.predict(pixels[start:start + PIXEL_BATCH_SIZE]) for start in range(0, len(pixels), PIXEL_BATCH_SIZE)])
        centroids = model.cluster_centers_
    else:
        centroids = training[rng.choice(len(training), clusters, replace=False)].copy()
        for _ in range(iterations):
            distances = np.sum((training[:, None, :] - centroids[None, :, :]) ** 2, axis=2)
            assignments = np.argmin(distances, axis=1)
            updated = np.vstack([
                training[assignments == index].mean(axis=0) if np.any(assignments == index) else centroids[index]
                for index in range(clusters)
            ])
            if float(np.max(np.linalg.norm(updated - centroids, axis=1))) <= tolerance:
                centroids = updated
                break
            centroids = updated
        labels = np.concatenate([
            np.argmin(np.sum((pixels[start:start + PIXEL_BATCH_SIZE, None, :] - centroids[None, :, :]) ** 2, axis=2), axis=1)
            for start in range(0, len(pixels), PIXEL_BATCH_SIZE)
        ])
    brightness_order = np.argsort(np.mean(centroids, axis=1), kind='stable')
    normalized_ids = np.empty(clusters, dtype=np.int64)
    normalized_ids[brightness_order] = np.arange(clusters)
    labels = normalized_ids[labels]
    foreground = parameters['foregroundClusters']
    if not isinstance(foreground, list) or not foreground or any(not isinstance(item, int) or item < 0 or item >= clusters for item in foreground):
        raise ValueError('Foreground clusters must be a non-empty JSON list of valid cluster IDs.')
    mask = np.where(np.isin(labels, foreground), 255, 0).astype(np.uint8).reshape(image.shape[:2])
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return {'mask': mask, 'contours': contours}


def nearest_centroid_classify(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    image = _image(inputs)
    samples, targets, classes = _supervised_samples(parameters['trainingSamples'])
    queries, detections = _object_queries(image, inputs.get('detections'))
    if not detections:
        return {'classified-detections': []}
    metric = str(parameters['distanceMetric'])
    if metric not in {'euclidean', 'manhattan'}:
        raise ValueError(f'Unsupported distance metric: {metric}.')
    if _implementation(parameters) == 'scikit-learn':
        NearestCentroid = _sklearn('sklearn.neighbors', 'NearestCentroid')
        model = NearestCentroid(metric=metric).fit(samples, targets)
        probabilities = model.predict_proba(queries)
    else:
        centroids = np.vstack([samples[targets == index].mean(axis=0) for index in range(len(classes))])
        delta = queries[:, None, :] - centroids[None, :, :]
        distances = np.sqrt(np.sum(delta * delta, axis=2)) if metric == 'euclidean' else np.sum(np.abs(delta), axis=2)
        inverse = 1.0 / np.maximum(distances, EPSILON)
        probabilities = inverse / inverse.sum(axis=1, keepdims=True)
    return _classified(detections, probabilities, classes)


def gaussian_nb_classify(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    image = _image(inputs)
    samples, targets, classes = _supervised_samples(parameters['trainingSamples'])
    queries, detections = _object_queries(image, inputs.get('detections'))
    if not detections:
        return {'classified-detections': []}
    smoothing = float(parameters['varianceSmoothing'])
    if smoothing <= 0:
        raise ValueError('Variance smoothing must be positive.')
    if _implementation(parameters) == 'scikit-learn':
        GaussianNB = _sklearn('sklearn.naive_bayes', 'GaussianNB')
        probabilities = GaussianNB(var_smoothing=smoothing).fit(samples, targets).predict_proba(queries)
    else:
        counts = np.asarray([np.count_nonzero(targets == index) for index in range(len(classes))], dtype=np.float64)
        means = np.vstack([samples[targets == index].mean(axis=0) for index in range(len(classes))])
        variances = np.vstack([samples[targets == index].var(axis=0) for index in range(len(classes))])
        variances += smoothing * max(float(np.var(samples, axis=0).max()), EPSILON)
        log_likelihood = -0.5 * np.sum(
            np.log(2.0 * np.pi * variances)[None, :, :] + (queries[:, None, :] - means[None, :, :]) ** 2 / variances[None, :, :], axis=2,
        ) + np.log(counts / counts.sum())[None, :]
        probabilities = _softmax(log_likelihood)
    return _classified(detections, probabilities, classes)


def logistic_classify(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    image = _image(inputs)
    samples, targets, classes = _supervised_samples(parameters['trainingSamples'])
    queries, detections = _object_queries(image, inputs.get('detections'))
    if not detections:
        return {'classified-detections': []}
    regularization = float(parameters['regularizationStrength'])
    iterations, tolerance = int(parameters['maximumIterations']), float(parameters['tolerance'])
    if regularization < 0 or iterations < 1 or tolerance <= 0:
        raise ValueError('Regularization, maximum iterations, and tolerance are invalid.')
    if _implementation(parameters) == 'scikit-learn':
        LogisticRegression = _sklearn('sklearn.linear_model', 'LogisticRegression')
        c_value = 1.0 / max(regularization, EPSILON)
        model = LogisticRegression(C=c_value, max_iter=iterations, tol=tolerance, random_state=int(parameters['randomSeed']))
        probabilities = model.fit(samples, targets).predict_proba(queries)
    else:
        learning_rate = float(parameters['learningRate'])
        if learning_rate <= 0:
            raise ValueError('Learning rate must be positive.')
        mean, scale = samples.mean(axis=0), np.maximum(samples.std(axis=0), EPSILON)
        standardized, standardized_queries = (samples - mean) / scale, (queries - mean) / scale
        design = np.column_stack([np.ones(len(samples)), standardized])
        query_design = np.column_stack([np.ones(len(queries)), standardized_queries])
        weights = np.zeros((design.shape[1], len(classes)), dtype=np.float64)
        expected = np.eye(len(classes))[targets]
        for _ in range(iterations):
            probabilities_train = _softmax(design @ weights)
            gradient = design.T @ (probabilities_train - expected) / len(samples)
            gradient[1:] += regularization * weights[1:]
            updated = weights - learning_rate * gradient
            if float(np.max(np.abs(updated - weights))) <= tolerance:
                weights = updated
                break
            weights = updated
        probabilities = _softmax(query_design @ weights)
    return _classified(detections, probabilities, classes)


def pca_anomaly(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    image = _image(inputs)
    training = _normal_samples(parameters['trainingSamples'])
    components = int(parameters['components'])
    if components < 1 or components > min(training.shape):
        raise ValueError('PCA components cannot exceed the training sample or feature count.')
    pixels = image.reshape(-1, 3).astype(np.float64) / 255.0
    if _implementation(parameters) == 'scikit-learn':
        PCA = _sklearn('sklearn.decomposition', 'PCA')
        model = PCA(n_components=components).fit(training)
        reconstructed = model.inverse_transform(model.transform(pixels))
        training_reconstructed = model.inverse_transform(model.transform(training))
    else:
        mean = training.mean(axis=0)
        _, _, right = np.linalg.svd(training - mean, full_matrices=False)
        basis = right[:components]
        reconstructed = (pixels - mean) @ basis.T @ basis + mean
        training_reconstructed = (training - mean) @ basis.T @ basis + mean
    errors = np.mean((pixels - reconstructed) ** 2, axis=1)
    baseline = max(float(np.percentile(np.mean((training - training_reconstructed) ** 2, axis=1), 95)), EPSILON)
    normalized = np.clip(errors / baseline, 0.0, 1.0).astype(np.float32).reshape(image.shape[:2])
    score = float(np.percentile(normalized, float(parameters['scorePercentile'])))
    return {'anomaly-map': normalized, 'score': float(np.clip(score, 0.0, 1.0))}