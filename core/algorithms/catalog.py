from .models import (
    AlgorithmDefinition,
    DataType,
    ParameterDefinition,
    ParameterKind,
    PortDefinition,
    PortDirection,
)


def _input(key: str, label: str, data_type: DataType, *, required: bool = True, variadic: bool = False) -> PortDefinition:
    return PortDefinition(key, label, PortDirection.INPUT, data_type, required, variadic)


def _output(key: str, label: str, data_type: DataType) -> PortDefinition:
    return PortDefinition(key, label, PortDirection.OUTPUT, data_type)


def _number(key: str, label: str, default: float, minimum: float, maximum: float) -> ParameterDefinition:
    return ParameterDefinition(key, label, ParameterKind.NUMBER, default, minimum=minimum, maximum=maximum)


def _integer(key: str, label: str, default: int, minimum: int, maximum: int) -> ParameterDefinition:
    return ParameterDefinition(key, label, ParameterKind.INTEGER, default, minimum=minimum, maximum=maximum)


def _select(key: str, label: str, default: str, *options: str) -> ParameterDefinition:
    return ParameterDefinition(key, label, ParameterKind.SELECT, default, options=options)


def _boolean(key: str, label: str, default: bool) -> ParameterDefinition:
    return ParameterDefinition(key, label, ParameterKind.BOOLEAN, default)


def _text(key: str, label: str, default: str) -> ParameterDefinition:
    return ParameterDefinition(key, label, ParameterKind.TEXT, default)


def _algorithm(
    algorithm_id: str,
    name: str,
    description: str,
    category: str,
    group: str,
    inputs: tuple[PortDefinition, ...],
    outputs: tuple[PortDefinition, ...],
    parameters: tuple[ParameterDefinition, ...] = (),
    reference: str | None = None,
) -> AlgorithmDefinition:
    return AlgorithmDefinition(
        id=algorithm_id,
        name=name,
        description=description,
        category=category,
        documentation_group=group,
        inputs=inputs,
        outputs=outputs,
        parameters=parameters,
        documentation_reference=reference,
    )


IMAGE = (_input('image', 'Image', DataType.IMAGE),)
IMAGE_OUT = (_output('image', 'Image', DataType.IMAGE),)
PROCESSED_IMAGE_OUT = (_output('processed-image', 'Processed image', DataType.IMAGE),)
ANOMALY_OUTPUTS = (
    _output('anomaly-map', 'Anomaly map', DataType.ANOMALY_MAP),
    _output('score', 'Score', DataType.SCORE),
)
SCORE = (_input('score', 'Score', DataType.SCORE),)
SCORE_OUT = (_output('score', 'Score', DataType.SCORE),)


_CATALOG = (
    _algorithm('image-input', 'Image input', 'Provides an image selected by the recipe.', 'Acquisition', 'Acquisition and pipeline components', (), IMAGE_OUT, (_text('source', 'Source', 'recipe-image'),)),
    _algorithm('camera-capture', 'Camera capture', 'Describes a configured camera acquisition step.', 'Acquisition', 'Acquisition and pipeline components', (), IMAGE_OUT, (_text('cameraId', 'Camera ID', 'top-camera'), _integer('exposureUs', 'Exposure (μs)', 8000, 1, 1000000))),
    _algorithm('roi-extraction', 'ROI extraction', 'Extracts configured regions from an image.', 'Pipeline', 'Acquisition and pipeline components', IMAGE + (_input('regions', 'Regions', DataType.ROI_SET),), (_output('images', 'ROI images', DataType.IMAGE_SET),)),
    _algorithm('global-local-stream-split', 'Global/local stream split', 'Creates global and local image streams.', 'Pipeline', 'Acquisition and pipeline components', IMAGE, (_output('global', 'Global image', DataType.IMAGE), _output('local', 'Local images', DataType.IMAGE_SET)), (_integer('tileSize', 'Tile size', 256, 16, 4096),)),
    _algorithm('score-normalization', 'Score normalization', 'Normalizes a score to a configured range.', 'Pipeline', 'Acquisition and pipeline components', SCORE, (_output('normalized-score', 'Normalized score', DataType.SCORE),), (_number('minimum', 'Minimum', 0.0, -1000000.0, 1000000.0), _number('maximum', 'Maximum', 1.0, -1000000.0, 1000000.0))),
    _algorithm('connected-component-evidence-filter', 'Connected-component evidence filter', 'Filters spatial evidence by component geometry.', 'Pipeline', 'Acquisition and pipeline components', (_input('anomaly-map', 'Anomaly map', DataType.ANOMALY_MAP),), (_output('detections', 'Evidence', DataType.DETECTIONS), _output('score', 'Score', DataType.SCORE)), (_integer('minimumArea', 'Minimum area', 4, 1, 1000000),)),
    _algorithm('decision-fusion', 'Decision fusion', 'Combines one or more scores into a review decision.', 'Decision', 'Acquisition and pipeline components', (_input('scores', 'Scores', DataType.SCORE, variadic=True),), (_output('decision', 'Decision', DataType.DECISION),), (_number('reviewThreshold', 'Review threshold', 0.5, 0.0, 1.0), _number('failThreshold', 'Fail threshold', 0.8, 0.0, 1.0))),
    _algorithm('decision-output', 'Decision output', 'Publishes the configured inspection decision.', 'Decision', 'Acquisition and pipeline components', (_input('decision', 'Decision', DataType.DECISION),), (_output('result-decision', 'Result decision', DataType.DECISION),)),

    _algorithm('color-conversion', 'Color conversion', 'Converts image color representation.', 'OpenCV tools', 'OpenCV-supported configurable tools', IMAGE, PROCESSED_IMAGE_OUT, (_select('mode', 'Mode', 'bgr-to-gray', 'bgr-to-gray', 'bgr-to-rgb', 'bgr-to-hsv', 'rgb-to-gray'),)),
    _algorithm('resize', 'Resize', 'Resizes an image to configured dimensions.', 'OpenCV tools', 'OpenCV-supported configurable tools', IMAGE, PROCESSED_IMAGE_OUT, (_integer('width', 'Width', 1024, 1, 16384), _integer('height', 'Height', 1024, 1, 16384), _select('interpolation', 'Interpolation', 'linear', 'nearest', 'linear', 'cubic', 'area'))),
    _algorithm('normalize', 'Normalize', 'Normalizes image intensity values.', 'OpenCV tools', 'OpenCV-supported configurable tools', IMAGE, PROCESSED_IMAGE_OUT, (_number('alpha', 'Alpha', 0.0, -1000000.0, 1000000.0), _number('beta', 'Beta', 1.0, -1000000.0, 1000000.0))),
    _algorithm('clahe', 'CLAHE', 'Configures contrast-limited adaptive histogram equalization.', 'OpenCV tools', 'OpenCV-supported configurable tools', IMAGE, PROCESSED_IMAGE_OUT, (_number('clipLimit', 'Clip limit', 2.0, 0.01, 100.0), _integer('tileGridSize', 'Tile grid size', 8, 1, 256))),
    _algorithm('gaussian-blur', 'Gaussian blur', 'Applies a configured Gaussian smoothing kernel.', 'OpenCV tools', 'OpenCV-supported configurable tools', IMAGE, PROCESSED_IMAGE_OUT, (_integer('kernelSize', 'Kernel size', 5, 1, 255), _number('sigma', 'Sigma', 1.0, 0.0, 1000.0))),
    _algorithm('median-blur', 'Median blur', 'Applies median filtering.', 'OpenCV tools', 'OpenCV-supported configurable tools', IMAGE, PROCESSED_IMAGE_OUT, (_integer('kernelSize', 'Kernel size', 5, 1, 255),)),
    _algorithm('bilateral-filter', 'Bilateral filter', 'Smooths while preserving configured edges.', 'OpenCV tools', 'OpenCV-supported configurable tools', IMAGE, PROCESSED_IMAGE_OUT, (_integer('diameter', 'Diameter', 9, 1, 255), _number('sigmaColor', 'Color sigma', 75.0, 0.0, 10000.0), _number('sigmaSpace', 'Space sigma', 75.0, 0.0, 10000.0))),
    _algorithm('global-threshold', 'Global threshold', 'Applies a fixed global threshold.', 'OpenCV tools', 'OpenCV-supported configurable tools', IMAGE, (_output('mask', 'Mask', DataType.MASK),), (_number('threshold', 'Threshold', 127.0, 0.0, 65535.0),)),
    _algorithm('otsu-threshold', 'Otsu threshold', 'Selects a global threshold using Otsu criteria.', 'OpenCV tools', 'OpenCV-supported configurable tools', IMAGE, (_output('mask', 'Mask', DataType.MASK),)),
    _algorithm('adaptive-threshold', 'Adaptive threshold', 'Applies a local adaptive threshold.', 'OpenCV tools', 'OpenCV-supported configurable tools', IMAGE, (_output('mask', 'Mask', DataType.MASK),), (_integer('blockSize', 'Block size', 11, 3, 255), _number('constant', 'Constant', 2.0, -255.0, 255.0))),
    _algorithm('erode', 'Erode', 'Erodes a spatial mask.', 'OpenCV tools', 'OpenCV-supported configurable tools', (_input('mask', 'Mask', DataType.MASK),), (_output('processed-mask', 'Processed mask', DataType.MASK),), (_integer('iterations', 'Iterations', 1, 1, 100),)),
    _algorithm('dilate', 'Dilate', 'Dilates a spatial mask.', 'OpenCV tools', 'OpenCV-supported configurable tools', (_input('mask', 'Mask', DataType.MASK),), (_output('processed-mask', 'Processed mask', DataType.MASK),), (_integer('iterations', 'Iterations', 1, 1, 100),)),
    _algorithm('morphology-operation', 'Morphology operation', 'Applies a selected morphology operation.', 'OpenCV tools', 'OpenCV-supported configurable tools', (_input('mask', 'Mask', DataType.MASK),), (_output('processed-mask', 'Processed mask', DataType.MASK),), (_select('operation', 'Operation', 'open', 'open', 'close', 'gradient', 'top-hat', 'black-hat'), _integer('kernelSize', 'Kernel size', 3, 1, 255))),
    _algorithm('canny-edges', 'Canny edges', 'Configures Canny edge extraction.', 'OpenCV tools', 'OpenCV-supported configurable tools', IMAGE, (_output('mask', 'Edges', DataType.MASK),), (_number('lowThreshold', 'Low threshold', 50.0, 0.0, 65535.0), _number('highThreshold', 'High threshold', 150.0, 0.0, 65535.0))),
    _algorithm('sobel-gradient', 'Sobel gradient', 'Computes a configured Sobel gradient.', 'OpenCV tools', 'OpenCV-supported configurable tools', IMAGE, PROCESSED_IMAGE_OUT, (_integer('dx', 'X derivative', 1, 0, 4), _integer('dy', 'Y derivative', 0, 0, 4))),
    _algorithm('scharr-gradient', 'Scharr gradient', 'Computes a Scharr gradient.', 'OpenCV tools', 'OpenCV-supported configurable tools', IMAGE, PROCESSED_IMAGE_OUT, (_select('axis', 'Axis', 'x', 'x', 'y'),)),
    _algorithm('laplacian', 'Laplacian', 'Computes the image Laplacian.', 'OpenCV tools', 'OpenCV-supported configurable tools', IMAGE, PROCESSED_IMAGE_OUT, (_integer('kernelSize', 'Kernel size', 3, 1, 31),)),
    _algorithm('find-contours', 'Find contours', 'Extracts vector contours from a mask.', 'OpenCV tools', 'OpenCV-supported configurable tools', (_input('mask', 'Mask', DataType.MASK),), (_output('contours', 'Contours', DataType.CONTOURS),), (_select('retrieval', 'Retrieval', 'external', 'external', 'list', 'tree'),)),
    _algorithm('connected-components', 'Connected components', 'Labels connected mask components.', 'OpenCV tools', 'OpenCV-supported configurable tools', (_input('mask', 'Mask', DataType.MASK),), (_output('detections', 'Components', DataType.DETECTIONS),)),
    _algorithm('hough-lines', 'Hough lines', 'Detects configured line evidence.', 'OpenCV tools', 'OpenCV-supported configurable tools', (_input('mask', 'Edges', DataType.MASK),), (_output('detections', 'Lines', DataType.DETECTIONS),), (_integer('threshold', 'Votes', 80, 1, 100000),)),
    _algorithm('hough-circles', 'Hough circles', 'Detects configured circle evidence.', 'OpenCV tools', 'OpenCV-supported configurable tools', IMAGE, (_output('detections', 'Circles', DataType.DETECTIONS),), (_integer('minimumRadius', 'Minimum radius', 2, 0, 100000), _integer('maximumRadius', 'Maximum radius', 100, 1, 100000))),
    _algorithm('feature-detection-and-matching', 'Feature detection and matching', 'Configures feature extraction and correspondence matching.', 'OpenCV tools', 'OpenCV-supported configurable tools', (_input('image', 'Image', DataType.IMAGE), _input('reference', 'Reference', DataType.IMAGE)), (_output('keypoints', 'Matches', DataType.KEYPOINTS), _output('transform', 'Transform', DataType.TRANSFORM)), (_select('detector', 'Detector', 'orb', 'orb', 'sift', 'akaze'),)),
    _algorithm('camera-undistortion', 'Camera undistortion', 'Applies a configured camera calibration mapping.', 'OpenCV tools', 'OpenCV-supported configurable tools', IMAGE, PROCESSED_IMAGE_OUT, (_text('calibrationId', 'Calibration ID', 'top-camera-default'),)),
    _algorithm('homography-registration', 'Homography registration', 'Registers an image with a homography.', 'OpenCV tools', 'OpenCV-supported configurable tools', (_input('image', 'Image', DataType.IMAGE), _input('reference', 'Reference', DataType.IMAGE)), (_output('registered-image', 'Registered image', DataType.IMAGE), _output('transform', 'Transform', DataType.TRANSFORM)), (_select('method', 'Method', 'ransac', 'ransac', 'lmeds', 'direct'),)),
    _algorithm('ecc-registration', 'ECC registration', 'Registers an image by enhanced correlation coefficient.', 'OpenCV tools', 'OpenCV-supported configurable tools', (_input('image', 'Image', DataType.IMAGE), _input('reference', 'Reference', DataType.IMAGE)), (_output('registered-image', 'Registered image', DataType.IMAGE), _output('transform', 'Transform', DataType.TRANSFORM)), (_select('motionModel', 'Motion model', 'homography', 'translation', 'euclidean', 'affine', 'homography'), _integer('iterations', 'Iterations', 100, 1, 10000))),

    _algorithm('absolute-difference', 'Absolute difference', 'Scores absolute deviation from configured normal reference.', 'Golden/reference', 'Group A — Golden/reference comparison', IMAGE, ANOMALY_OUTPUTS, (_text('referenceAsset', 'Reference asset', 'golden'),)),
    _algorithm('median-mad-robust-difference', 'Median–MAD robust difference', 'Uses median and MAD reference statistics for robust deviation scoring.', 'Golden/reference', 'Group A — Golden/reference comparison', IMAGE, ANOMALY_OUTPUTS, (_number('epsilon', 'Epsilon', 0.001, 0.0000001, 1.0),), 'Median–MAD robust difference'),
    _algorithm('ssim', 'SSIM', 'Scores structural similarity against a configured reference.', 'Golden/reference', 'Group A — Golden/reference comparison', IMAGE, ANOMALY_OUTPUTS, (_integer('windowSize', 'Window size', 11, 3, 255),)),
    _algorithm('normalized-cross-correlation', 'Normalized cross-correlation', 'Scores normalized correlation with a configured reference.', 'Golden/reference', 'Group A — Golden/reference comparison', IMAGE, ANOMALY_OUTPUTS),
    _algorithm('edge-difference', 'Edge difference', 'Compares edge evidence with a configured reference.', 'Golden/reference', 'Group A — Golden/reference comparison', IMAGE, ANOMALY_OUTPUTS, (_number('threshold', 'Edge threshold', 0.2, 0.0, 1.0),)),
    _algorithm('gradient-difference', 'Gradient difference', 'Compares gradient evidence with a configured reference.', 'Golden/reference', 'Group A — Golden/reference comparison', IMAGE, ANOMALY_OUTPUTS),
    _algorithm('binary-xor', 'Binary XOR', 'Compares binary evidence using exclusive OR.', 'Golden/reference', 'Group A — Golden/reference comparison', (_input('mask', 'Mask', DataType.MASK), _input('reference', 'Reference mask', DataType.MASK)), (_output('difference-mask', 'Difference mask', DataType.MASK), _output('score', 'Score', DataType.SCORE))),
    _algorithm('template-matching', 'Template matching', 'Matches configured templates against an image.', 'Golden/reference', 'Group A — Golden/reference comparison', IMAGE, (_output('detections', 'Matches', DataType.DETECTIONS), _output('score', 'Score', DataType.SCORE)), (_select('method', 'Method', 'ccoeff-normed', 'sqdiff', 'sqdiff-normed', 'ccorr-normed', 'ccoeff-normed'),)),
    _algorithm('per-pixel-mahalanobis-distance', 'Per-pixel Mahalanobis distance', 'Scores pixels against configured multivariate normal statistics.', 'Golden/reference', 'Group A — Golden/reference comparison', IMAGE, ANOMALY_OUTPUTS, (_number('regularization', 'Regularization', 0.001, 0.0000001, 1.0),)),
    _algorithm('golden-score-fusion', 'Golden score fusion', 'Fuses configured golden-reference scores.', 'Golden/reference', 'Group A — Golden/reference comparison', (_input('scores', 'Scores', DataType.SCORE, variadic=True),), SCORE_OUT, (_select('method', 'Method', 'maximum', 'maximum', 'mean', 'weighted-mean'),)),

    _algorithm('spade', 'SPADE', 'Configures spatial nearest-neighbor anomaly scoring.', 'Feature distribution', 'Group B — Feature distribution', IMAGE, ANOMALY_OUTPUTS, (_integer('neighbors', 'Neighbors', 5, 1, 1000),), 'SPADE'),
    _algorithm('padim', 'PaDiM', 'Configures patch distribution modeling.', 'Feature distribution', 'Group B — Feature distribution', IMAGE, ANOMALY_OUTPUTS, (_integer('embeddingDimension', 'Embedding dimension', 100, 1, 100000),), 'PaDiM'),
    _algorithm('patchcore', 'PatchCore', 'Configures a representative patch memory bank.', 'Feature distribution', 'Group B — Feature distribution', IMAGE, ANOMALY_OUTPUTS, (_integer('memoryBankSize', 'Memory bank size', 10000, 1, 10000000), _number('coresetRatio', 'Coreset ratio', 0.1, 0.0001, 1.0)), 'PatchCore'),
    _algorithm('anomalydino', 'AnomalyDINO', 'Configures DINO feature anomaly scoring.', 'Feature distribution', 'Group B — Feature distribution', IMAGE, ANOMALY_OUTPUTS, (_select('backbone', 'Backbone', 'dinov2-small', 'dinov2-small', 'dinov2-base', 'dinov2-large'),), 'AnomalyDINO'),

    _algorithm('stfpm', 'STFPM', 'Configures student–teacher feature pyramid matching.', 'Student–teacher', 'Group C — Student–teacher and distillation', IMAGE, ANOMALY_OUTPUTS, (_select('backbone', 'Backbone', 'resnet18', 'resnet18', 'wide-resnet50'),), 'STFPM'),
    _algorithm('rd4ad', 'RD4AD', 'Configures reverse-distillation anomaly detection.', 'Student–teacher', 'Group C — Student–teacher and distillation', IMAGE, ANOMALY_OUTPUTS, (_number('temperature', 'Temperature', 1.0, 0.01, 100.0),), 'RD4AD'),
    _algorithm('efficientad', 'EfficientAD', 'Configures efficient student–teacher anomaly scoring.', 'Student–teacher', 'Group C — Student–teacher and distillation', IMAGE, ANOMALY_OUTPUTS, (_select('modelSize', 'Model size', 'small', 'small', 'medium'),), 'EfficientAD'),

    _algorithm('differnet', 'DifferNet', 'Configures normalizing-flow image anomaly scoring.', 'Normalizing flow', 'Group E — Normalizing flow', IMAGE, ANOMALY_OUTPUTS, (_integer('flowSteps', 'Flow steps', 8, 1, 128),), 'DifferNet'),
    _algorithm('fastflow', 'FastFlow', 'Configures fast feature-space normalizing flows.', 'Normalizing flow', 'Group E — Normalizing flow', IMAGE, ANOMALY_OUTPUTS, (_integer('flowSteps', 'Flow steps', 8, 1, 128),), 'FastFlow'),
    _algorithm('cflow-ad', 'CFLOW-AD', 'Configures conditional normalizing-flow anomaly detection.', 'Normalizing flow', 'Group E — Normalizing flow', IMAGE, ANOMALY_OUTPUTS, (_integer('couplingBlocks', 'Coupling blocks', 8, 1, 128),), 'CFLOW-AD'),

    _algorithm('golden-component-matching', 'Golden component matching', 'Matches configured component instances with golden evidence.', 'Component/logical', 'Group F — Component and logical inspection', IMAGE, (_output('detections', 'Components', DataType.DETECTIONS), _output('score', 'Score', DataType.SCORE)), (_number('matchThreshold', 'Match threshold', 0.8, 0.0, 1.0),), 'Golden component matching'),
    _algorithm('comad', 'ComAD', 'Configures component-aware anomaly detection.', 'Component/logical', 'Group F — Component and logical inspection', IMAGE, ANOMALY_OUTPUTS, (_integer('componentCount', 'Component count', 32, 1, 100000),), 'ComAD'),
    _algorithm('component-relation-graph', 'Component relation graph', 'Scores configured spatial and logical component relations.', 'Component/logical', 'Group F — Component and logical inspection', (_input('detections', 'Components', DataType.DETECTIONS),), (_output('score', 'Score', DataType.SCORE), _output('decision', 'Decision', DataType.DECISION)), (_number('relationTolerance', 'Relation tolerance', 0.1, 0.0, 1.0),), 'Component relation graph'),
    _algorithm('uniad', 'UniAD', 'Configures unified anomaly detection features.', 'Component/logical', 'Group F — Component and logical inspection', IMAGE, ANOMALY_OUTPUTS, (_select('backbone', 'Backbone', 'efficientnet-b4', 'efficientnet-b4', 'resnet50'),), 'UniAD'),
    _algorithm('polarity-and-orientation-inspection', 'Polarity and orientation inspection', 'Checks configured component polarity and orientation evidence.', 'Component/logical', 'Group F — Component and logical inspection', (_input('image', 'Image', DataType.IMAGE), _input('components', 'Components', DataType.DETECTIONS, required=False)), (_output('detections', 'Findings', DataType.DETECTIONS), _output('score', 'Score', DataType.SCORE)), (_number('angleTolerance', 'Angle tolerance', 5.0, 0.0, 180.0),), 'Polarity and orientation inspection'),
)

_CATALOG_BY_ID = {definition.id: definition for definition in _CATALOG}


def get_algorithm_catalog() -> tuple[AlgorithmDefinition, ...]:
    return _CATALOG


def get_algorithm_definition(algorithm_id: str) -> AlgorithmDefinition | None:
    return _CATALOG_BY_ID.get(algorithm_id)