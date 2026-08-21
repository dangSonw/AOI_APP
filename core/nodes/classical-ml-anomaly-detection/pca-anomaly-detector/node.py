from __future__ import annotations



from collections.abc import Mapping


import cv2

import numpy as np


from sklearn.decomposition import PCA





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

def execute_pca(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    image = _image(inputs)
    value = parameters['trainingSamples']
    if not isinstance(value, list) or len(value) < 2:
        raise ValueError('Training samples must be a JSON list containing at least two samples.')
    try:
        training = np.asarray([sample['features'] for sample in value if isinstance(sample, Mapping)], dtype=np.float64) / 255.0
    except (KeyError, TypeError) as error:
        raise ValueError('Training samples must contain BGR feature vectors.') from error
    if training.ndim != 2 or training.shape[1] != 3 or not np.isfinite(training).all():
        raise ValueError('Training samples must contain finite BGR feature vectors.')
    components = int(parameters['components'])
    if components < 1 or components > min(training.shape):
        raise ValueError('PCA components cannot exceed the training sample or feature count.')
    model = PCA(n_components=components).fit(training)
    pixels = image.reshape(-1, 3).astype(np.float64) / 255.0
    reconstructed = model.inverse_transform(model.transform(pixels))
    training_reconstructed = model.inverse_transform(model.transform(training))
    errors = np.mean((pixels - reconstructed) ** 2, axis=1)
    baseline = max(float(np.percentile(np.mean((training - training_reconstructed) ** 2, axis=1), 95)), EPSILON)
    normalized = np.clip(errors / baseline, 0.0, 1.0).astype(np.float32).reshape(image.shape[:2])
    score = float(np.percentile(normalized, float(parameters['scorePercentile'])))
    return {'anomaly-map': normalized, 'score': float(np.clip(score, 0.0, 1.0))}

from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse

NODE_ID = 'pca-anomaly-detector'
USE = NodeUse.DEBUG
INPUT_KEYS = ('image',)
OUTPUT_KEYS = ('anomaly-map', 'score')


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    return execute_pca(inputs, parameters)
