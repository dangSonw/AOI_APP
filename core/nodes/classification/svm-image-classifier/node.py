from __future__ import annotations

import math
import hashlib
from io import BytesIO
import json
from pathlib import Path
import pickle
import platform
from types import MappingProxyType
from typing import Any, Callable, Mapping, NamedTuple
import zipfile

import cv2
import numpy as np
import sklearn
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from core.nodes.errors import NodeExecutionCancelled, NodeNotImplementedError
from core.nodes.models import ModelBinding, NodeExecutionContext, NodeInputs, NodeOutputs, NodeParameters, NodeUse
from core.visualization.contracts import TablePayload


NODE_ID = 'svm-image-classifier'
USE = NodeUse.RELEASE
INPUT_KEYS: tuple[str, ...] = ()
OUTPUT_KEYS: tuple[str, ...] = ()

DEFAULT_PARAMETERS = MappingProxyType({
    'imageWidth': 128,
    'imageHeight': 128,
    'hogWindowWidth': 128,
    'hogWindowHeight': 128,
    'hogBlockWidth': 16,
    'hogBlockHeight': 16,
    'hogBlockStrideX': 8,
    'hogBlockStrideY': 8,
    'hogCellWidth': 8,
    'hogCellHeight': 8,
    'hogBins': 9,
    'useScaler': True,
    'kernel': 'rbf',
    'c': 10.0,
    'gamma': 'scale',
    'degree': 3,
    'classWeight': 'none',
    'probability': False,
    'invalidImagePolicy': 'fail',
    'maxSamples': 10_000,
    'maxImagePixels': 16_777_216,
    'randomSeed': 42,
})
ALLOWED_IMAGE_EXTENSIONS = frozenset({'.jpg', '.jpeg', '.png', '.bmp'})
MODEL_SCHEMA = 'aoi.sklearn-pipeline.v1'


def _integer(parameters: Mapping[str, Any], key: str, *, minimum: int, maximum: int) -> int:
    value = parameters.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f'{key} must be a positive integer from {minimum} to {maximum}.')
    return value


def validate_parameters(
    parameters: Mapping[str, Any],
    *,
    execution_target: str,
) -> Mapping[str, Any]:
    if execution_target != 'local-cpu':
        raise ValueError('SVM image classifier execution target must be local-cpu.')
    if set(parameters) != set(DEFAULT_PARAMETERS):
        raise ValueError('SVM image classifier parameters must match the declared manifest keys.')

    image_width = _integer(parameters, 'imageWidth', minimum=1, maximum=4096)
    image_height = _integer(parameters, 'imageHeight', minimum=1, maximum=4096)
    window_width = _integer(parameters, 'hogWindowWidth', minimum=1, maximum=4096)
    window_height = _integer(parameters, 'hogWindowHeight', minimum=1, maximum=4096)
    block_width = _integer(parameters, 'hogBlockWidth', minimum=2, maximum=1024)
    block_height = _integer(parameters, 'hogBlockHeight', minimum=2, maximum=1024)
    stride_x = _integer(parameters, 'hogBlockStrideX', minimum=1, maximum=1024)
    stride_y = _integer(parameters, 'hogBlockStrideY', minimum=1, maximum=1024)
    cell_width = _integer(parameters, 'hogCellWidth', minimum=1, maximum=512)
    cell_height = _integer(parameters, 'hogCellHeight', minimum=1, maximum=512)
    _integer(parameters, 'hogBins', minimum=1, maximum=64)
    try:
        _integer(parameters, 'maxSamples', minimum=2, maximum=100_000)
    except ValueError as error:
        raise ValueError('Maximum samples must be an integer from 2 to 100000.') from error
    _integer(parameters, 'maxImagePixels', minimum=1, maximum=100_000_000)
    _integer(parameters, 'randomSeed', minimum=0, maximum=2_147_483_647)

    if window_width != image_width or window_height != image_height:
        raise ValueError('HOG window dimensions must equal the resized image dimensions.')
    if block_width % cell_width or block_height % cell_height:
        raise ValueError('HOG block dimensions must be divisible by cell dimensions.')
    if stride_x % cell_width or stride_y % cell_height:
        raise ValueError('HOG block stride must be divisible by cell dimensions.')
    if block_width > window_width or block_height > window_height:
        raise ValueError('HOG block dimensions cannot exceed the window dimensions.')
    if (window_width - block_width) % stride_x or (window_height - block_height) % stride_y:
        raise ValueError('HOG window minus block dimensions must be divisible by block stride.')

    if not isinstance(parameters['useScaler'], bool) or not isinstance(parameters['probability'], bool):
        raise ValueError('SVM scaler and probability settings must be boolean.')
    kernel = parameters['kernel']
    if kernel not in {'linear', 'rbf', 'poly', 'sigmoid'}:
        raise ValueError('SVM kernel is unsupported.')
    c_value = parameters['c']
    if isinstance(c_value, bool) or not isinstance(c_value, (int, float)) or not math.isfinite(c_value) or c_value <= 0:
        raise ValueError('SVM C must be a positive finite number.')
    gamma = parameters['gamma']
    if gamma not in {'scale', 'auto'} and (
        isinstance(gamma, bool)
        or not isinstance(gamma, (int, float))
        or not math.isfinite(gamma)
        or gamma <= 0
    ):
        raise ValueError('SVM gamma must be scale, auto, or a positive finite number.')
    if kernel == 'linear' and gamma != 'scale':
        raise ValueError('SVM gamma must remain scale for the linear kernel.')
    degree = parameters['degree']
    if isinstance(degree, bool) or not isinstance(degree, int) or not 1 <= degree <= 10:
        raise ValueError('SVM degree must be an integer from 1 to 10.')
    if kernel != 'poly' and degree != 3:
        raise ValueError('SVM degree must remain 3 unless the poly kernel is selected.')
    if parameters['classWeight'] not in {'none', 'balanced'}:
        raise ValueError('SVM class weight must be none or balanced.')
    if parameters['invalidImagePolicy'] not in {'fail', 'skip'}:
        raise ValueError('Invalid image policy must be fail or skip.')
    return parameters


def _hog_descriptor(parameters: Mapping[str, Any]) -> cv2.HOGDescriptor:
    return cv2.HOGDescriptor(
        _winSize=(int(parameters['hogWindowWidth']), int(parameters['hogWindowHeight'])),
        _blockSize=(int(parameters['hogBlockWidth']), int(parameters['hogBlockHeight'])),
        _blockStride=(int(parameters['hogBlockStrideX']), int(parameters['hogBlockStrideY'])),
        _cellSize=(int(parameters['hogCellWidth']), int(parameters['hogCellHeight'])),
        _nbins=int(parameters['hogBins']),
    )


def _class_mapping(dataset: object) -> dict[str, int]:
    raw_mapping = getattr(dataset, 'class_mapping', None)
    if not isinstance(raw_mapping, Mapping) or len(raw_mapping) < 2:
        raise ValueError('Immutable dataset must declare at least two classes.')
    mapping = {str(name): int(class_id) for name, class_id in raw_mapping.items()}
    if sorted(mapping.values()) != list(range(len(mapping))):
        raise ValueError('Immutable dataset class IDs must be unique and contiguous from zero.')
    if any(not name for name in mapping):
        raise ValueError('Immutable dataset class names cannot be empty.')
    return mapping


def _safe_failure(logical_id: str, reason: str) -> dict[str, str]:
    return {'logicalId': logical_id, 'reason': reason}


def extract_dataset_features(
    dataset: object,
    parameters: Mapping[str, Any],
    *,
    is_cancelled: Callable[[], bool] = lambda: False,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    validate_parameters(parameters, execution_target='local-cpu')
    mapping = _class_mapping(dataset)
    raw_items = getattr(dataset, 'items', None)
    if not isinstance(raw_items, tuple):
        raw_items = tuple(raw_items) if raw_items is not None else ()
    if not raw_items:
        raise ValueError('Immutable dataset contains no image samples.')
    if len(raw_items) > int(parameters['maxSamples']):
        raise ValueError('Immutable dataset exceeds the maximum samples limit.')

    items = sorted(raw_items, key=lambda value: (int(value.class_id), str(value.logical_path)))
    descriptor = _hog_descriptor(parameters)
    features: list[np.ndarray] = []
    labels: list[int] = []
    failed: list[dict[str, str]] = []
    policy = str(parameters['invalidImagePolicy'])
    max_pixels = int(parameters['maxImagePixels'])
    image_size = (int(parameters['imageWidth']), int(parameters['imageHeight']))

    for item in items:
        if is_cancelled():
            raise NodeExecutionCancelled('SVM image feature extraction was cancelled.')
        logical_id = str(item.logical_path)
        failure = ''
        if Path(logical_id).suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS:
            failure = 'Image extension is unsupported.'
        elif mapping.get(str(item.class_name)) != int(item.class_id):
            failure = 'Image class metadata does not match the dataset class mapping.'
        elif int(item.width_px) * int(item.height_px) > max_pixels:
            failure = 'Image metadata exceeds the decoded pixels limit.'
        else:
            try:
                content = Path(item.path).read_bytes()
                decoded = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
            except OSError:
                decoded = None
            if decoded is None or decoded.size == 0:
                failure = 'Image content could not be decoded.'
            elif int(decoded.shape[0]) * int(decoded.shape[1]) > max_pixels:
                failure = 'Decoded image exceeds the pixels limit.'
            else:
                resized = cv2.resize(decoded, image_size, interpolation=cv2.INTER_AREA)
                gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
                feature = descriptor.compute(gray)
                if feature is None or feature.size == 0 or not np.isfinite(feature).all():
                    failure = 'HOG feature extraction produced invalid values.'
                else:
                    features.append(feature.reshape(-1).astype(np.float32, copy=False))
                    labels.append(int(item.class_id))
        if failure:
            safe_failure = _safe_failure(logical_id, failure)
            if policy == 'fail':
                raise ValueError(f'Invalid dataset image {logical_id}: {failure}')
            failed.append(safe_failure)

    if not features:
        raise ValueError('Immutable dataset contains no valid image samples after filtering.')
    return (
        np.stack(features).astype(np.float32, copy=False),
        np.asarray(labels, dtype=np.int64),
        {'loaded': len(features), 'failed': failed},
    )


class SvmTrainingResult(NamedTuple):
    artifact: bytes
    metrics: dict[str, float]
    report: dict[str, Any]
    confusion_matrix: dict[str, Any]
    failed_images: dict[str, Any]
    predictions: np.ndarray


class LoadedSvmModel(NamedTuple):
    pipeline: Pipeline
    metadata: dict[str, Any]


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf-8')


def _pipeline(parameters: Mapping[str, Any]) -> Pipeline:
    steps: list[tuple[str, Any]] = []
    if bool(parameters['useScaler']):
        steps.append(('scaler', StandardScaler()))
    steps.append(('svm', SVC(
        kernel=str(parameters['kernel']), C=float(parameters['c']), gamma=parameters['gamma'],
        degree=int(parameters['degree']),
        class_weight=None if parameters['classWeight'] == 'none' else 'balanced',
        probability=bool(parameters['probability']), random_state=int(parameters['randomSeed']),
    )))
    return Pipeline(steps)


def _zip_entry(name: str, content: bytes) -> tuple[zipfile.ZipInfo, bytes]:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_STORED
    info.external_attr = 0o600 << 16
    return info, content


def _serialize_model(
    pipeline: Pipeline,
    *,
    parameters: Mapping[str, Any],
    classes: list[str],
    datasets: list[dict[str, str]],
) -> bytes:
    model_bytes = pickle.dumps(pipeline, protocol=5)
    metadata: dict[str, Any] = {
        'schema': MODEL_SCHEMA,
        'nodeId': NODE_ID,
        'packageVersion': '1.0.0',
        'framework': 'scikit-learn',
        'frameworkVersion': sklearn.__version__,
        'pythonVersion': platform.python_version(),
        'opencvVersion': cv2.__version__,
        'numpyVersion': np.__version__,
        'preprocessing': {
            key: parameters[key] for key in parameters if key.startswith('image') or key.startswith('hog')
        },
        'classes': classes,
        'datasets': datasets,
        'parameters': dict(parameters),
        'modelSha256': hashlib.sha256(model_bytes).hexdigest(),
    }
    metadata['signature'] = hashlib.sha256(_canonical_json(metadata)).hexdigest()
    stream = BytesIO()
    with zipfile.ZipFile(stream, 'w') as archive:
        for entry in (_zip_entry('metadata.json', _canonical_json(metadata)), _zip_entry('model.pkl', model_bytes)):
            archive.writestr(*entry)
    return stream.getvalue()


def train_and_evaluate(
    training_dataset: object,
    test_dataset: object,
    parameters: Mapping[str, Any],
    *,
    is_cancelled: Callable[[], bool] = lambda: False,
) -> SvmTrainingResult:
    validated = validate_parameters(parameters, execution_target='local-cpu')
    train_features, train_labels, train_diagnostics = extract_dataset_features(
        training_dataset, validated, is_cancelled=is_cancelled,
    )
    test_features, test_labels, test_diagnostics = extract_dataset_features(
        test_dataset, validated, is_cancelled=is_cancelled,
    )
    if len(np.unique(train_labels)) < 2:
        raise ValueError('SVM training requires samples from at least two classes.')
    if is_cancelled():
        raise NodeExecutionCancelled('SVM fitting was cancelled.')
    pipeline = _pipeline(validated)
    pipeline.fit(train_features, train_labels)
    if is_cancelled():
        raise NodeExecutionCancelled('SVM evaluation was cancelled.')
    predictions = pipeline.predict(test_features).astype(np.int64, copy=False)
    class_mapping = _class_mapping(training_dataset)
    ordered_classes = [name for name, _ in sorted(class_mapping.items(), key=lambda value: value[1])]
    label_ids = list(range(len(ordered_classes)))
    accuracy = float(accuracy_score(test_labels, predictions))
    if not math.isfinite(accuracy):
        raise ValueError('SVM evaluation produced a non-finite accuracy.')
    raw_report = classification_report(
        test_labels, predictions, labels=label_ids, target_names=ordered_classes,
        output_dict=True, zero_division=0,
    )
    rows = [
        {'label': name, **{key: float(value) for key, value in raw_report[name].items()}}
        for name in ordered_classes
    ]
    report = TablePayload.from_mapping({
        'schema': 'aoi.table.v1',
        'columns': [
            {'key': 'label', 'label': 'Label', 'type': 'string'},
            {'key': 'precision', 'label': 'Precision', 'type': 'number'},
            {'key': 'recall', 'label': 'Recall', 'type': 'number'},
            {'key': 'f1-score', 'label': 'F1 score', 'type': 'number'},
            {'key': 'support', 'label': 'Support', 'type': 'number'},
        ],
        'rows': rows,
    }).to_mapping()
    matrix = confusion_matrix(test_labels, predictions, labels=label_ids).astype(int).tolist()
    datasets = [
        {'role': role, 'datasetId': str(dataset.dataset_id), 'version': str(dataset.version)}
        for role, dataset in (('training', training_dataset), ('test', test_dataset))
    ]
    artifact = _serialize_model(
        pipeline, parameters=validated, classes=ordered_classes, datasets=datasets,
    )
    return SvmTrainingResult(
        artifact=artifact,
        metrics={'accuracy': accuracy},
        report=report,
        confusion_matrix={'schema': 'aoi.confusion-matrix.v1', 'labels': ordered_classes, 'matrix': matrix},
        failed_images={
            'schema': 'aoi.failed-images.v1',
            'items': [*train_diagnostics['failed'], *test_diagnostics['failed']],
        },
        predictions=predictions,
    )


def load_model_artifact(content: bytes, *, expected_sha256: str, trusted: bool) -> LoadedSvmModel:
    if not trusted:
        raise ValueError('Model artifact must come from the trusted verified artifact store.')
    if hashlib.sha256(content).hexdigest() != expected_sha256:
        raise ValueError('Model artifact checksum does not match its immutable binding.')
    try:
        with zipfile.ZipFile(BytesIO(content), 'r') as archive:
            if set(archive.namelist()) != {'metadata.json', 'model.pkl'}:
                raise ValueError('Model artifact entries are invalid.')
            metadata_bytes = archive.read('metadata.json')
            model_bytes = archive.read('model.pkl')
        metadata = json.loads(metadata_bytes)
    except (KeyError, OSError, ValueError, zipfile.BadZipFile, json.JSONDecodeError) as error:
        raise ValueError('Model artifact envelope is malformed.') from error
    if not isinstance(metadata, dict):
        raise ValueError('Model artifact metadata is invalid.')
    signature = metadata.pop('signature', None)
    if signature != hashlib.sha256(_canonical_json(metadata)).hexdigest():
        raise ValueError('Model artifact metadata signature is invalid.')
    if (
        metadata.get('schema') != MODEL_SCHEMA
        or metadata.get('nodeId') != NODE_ID
        or metadata.get('packageVersion') != '1.0.0'
        or metadata.get('frameworkVersion') != sklearn.__version__
        or metadata.get('pythonVersion') != platform.python_version()
        or metadata.get('modelSha256') != hashlib.sha256(model_bytes).hexdigest()
    ):
        raise ValueError('Model artifact signature or runtime compatibility is invalid.')
    try:
        pipeline = pickle.loads(model_bytes)
    except Exception as error:
        raise ValueError('Model artifact payload cannot be loaded.') from error
    if not isinstance(pipeline, Pipeline):
        raise ValueError('Model artifact payload is not a scikit-learn Pipeline.')
    return LoadedSvmModel(pipeline=pipeline, metadata={**metadata, 'signature': signature})


def predict(model: LoadedSvmModel, features: np.ndarray) -> np.ndarray:
    if not isinstance(features, np.ndarray) or features.ndim != 2 or not np.isfinite(features).all():
        raise ValueError('Inference features must be a finite two-dimensional NumPy array.')
    return np.asarray(model.pipeline.predict(features), dtype=np.int64)


def _image_features(image: object, parameters: Mapping[str, Any]) -> np.ndarray:
    validate_parameters(parameters, execution_target='local-cpu')
    if not isinstance(image, np.ndarray) or image.dtype != np.uint8 or image.ndim not in {2, 3} or image.size == 0:
        raise ValueError('Inference image must be a non-empty uint8 NumPy image.')
    if image.ndim == 3 and image.shape[2] not in {1, 3, 4}:
        raise ValueError('Inference image channel count is unsupported.')
    if int(image.shape[0]) * int(image.shape[1]) > int(parameters['maxImagePixels']):
        raise ValueError('Inference image exceeds the pixels limit.')
    resized = cv2.resize(
        image,
        (int(parameters['imageWidth']), int(parameters['imageHeight'])),
        interpolation=cv2.INTER_AREA,
    )
    if resized.ndim == 2:
        gray = resized
    elif resized.shape[2] == 4:
        gray = cv2.cvtColor(resized, cv2.COLOR_BGRA2GRAY)
    else:
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    feature = _hog_descriptor(parameters).compute(gray)
    if feature is None or feature.size == 0 or not np.isfinite(feature).all():
        raise ValueError('Inference HOG feature extraction produced invalid values.')
    return feature.reshape(1, -1).astype(np.float32, copy=False)


def execute_with_context(
    inputs: NodeInputs,
    parameters: NodeParameters,
    context: NodeExecutionContext,
) -> NodeOutputs:
    if inputs.get('action') != 'infer':
        return execute(inputs, parameters)
    raw_binding = inputs.get('model')
    if not isinstance(raw_binding, Mapping):
        raise ValueError('SVM inference requires an immutable model binding.')
    requested = ModelBinding.from_mapping(raw_binding)
    resolved = context.models.get(requested.model_name)
    if resolved is None:
        raise ValueError(f'Model {requested.model_name} is not resolved for inference.')
    if resolved != requested:
        raise ValueError(f'Model {requested.model_name} immutable binding does not match the execution context.')
    content = context.read_artifact(
        requested.model_name,
        expected_media_types=('application/vnd.aoi.sklearn-pipeline+zip', 'application/octet-stream'),
    )
    model = load_model_artifact(content, expected_sha256=requested.artifact_sha256, trusted=True)
    class_id = int(predict(model, _image_features(inputs.get('image'), parameters))[0])
    return {
        'class-id': class_id,
        'model': {
            'modelName': requested.model_name,
            'modelVersion': requested.model_version,
            'artifactSha256': requested.artifact_sha256,
        },
    }


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    action = inputs.get('action')
    if action == 'train':
        cancellation_probe = inputs.get('is-cancelled')
        if cancellation_probe is not None and not callable(cancellation_probe):
            raise ValueError('SVM cancellation probe must be callable.')
        result = train_and_evaluate(
            inputs.get('training-dataset'), inputs.get('test-dataset'), parameters,
            is_cancelled=cancellation_probe if callable(cancellation_probe) else (lambda: False),
        )
        return {
            'model': result.artifact, 'metrics': result.metrics, 'report': result.report,
            'confusion-matrix': result.confusion_matrix, 'failed-images': result.failed_images,
        }
    raise ValueError('SVM image classifier requires an explicit supported action.')