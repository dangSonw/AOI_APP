from __future__ import annotations





import cv2

import numpy as np

from sklearn.cluster import KMeans






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

def execute_kmeans(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
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
    maximum_pixels = int(parameters['maximumTrainingPixels'])
    rng = np.random.default_rng(int(parameters['randomSeed']))
    training = pixels if len(pixels) <= maximum_pixels else pixels[rng.choice(len(pixels), maximum_pixels, replace=False)]
    model = KMeans(
        n_clusters=clusters,
        n_init=10,
        max_iter=int(parameters['maximumIterations']),
        tol=float(parameters['tolerance']),
        random_state=int(parameters['randomSeed']),
    ).fit(training)
    labels = np.concatenate([model.predict(pixels[start:start + PIXEL_BATCH_SIZE]) for start in range(0, len(pixels), PIXEL_BATCH_SIZE)])
    brightness_order = np.argsort(np.mean(model.cluster_centers_, axis=1), kind='stable')
    normalized_ids = np.empty(clusters, dtype=np.int64)
    normalized_ids[brightness_order] = np.arange(clusters)
    labels = normalized_ids[labels]
    foreground = parameters['foregroundClusters']
    if not isinstance(foreground, list) or not foreground or any(not isinstance(item, int) or item < 0 or item >= clusters for item in foreground):
        raise ValueError('Foreground clusters must be a non-empty JSON list of valid cluster IDs.')
    mask = np.where(np.isin(labels, foreground), 255, 0).astype(np.uint8).reshape(image.shape[:2])
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return {'mask': mask, 'contours': list(contours)}

from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse

NODE_ID = 'kmeans-image-segmentation'
USE = NodeUse.DEBUG
INPUT_KEYS = ('image',)
OUTPUT_KEYS = ('mask', 'contours')


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    return execute_kmeans(inputs, parameters)
