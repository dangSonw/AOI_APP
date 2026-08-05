from dataclasses import dataclass
from enum import StrEnum
from typing import TypeAlias


ParameterValue: TypeAlias = bool | int | float | str


class DataType(StrEnum):
    IMAGE = 'image'
    IMAGE_SET = 'image-set'
    MASK = 'mask'
    ROI_SET = 'roi-set'
    KEYPOINTS = 'keypoints'
    CONTOURS = 'contours'
    FEATURES = 'features'
    DETECTIONS = 'detections'
    ANOMALY_MAP = 'anomaly-map'
    SCORE = 'score'
    TRANSFORM = 'transform'
    DECISION = 'decision'


class PortDirection(StrEnum):
    INPUT = 'input'
    OUTPUT = 'output'


class ParameterKind(StrEnum):
    BOOLEAN = 'boolean'
    INTEGER = 'integer'
    NUMBER = 'number'
    TEXT = 'text'
    SELECT = 'select'


@dataclass(frozen=True, slots=True)
class PortDefinition:
    key: str
    label: str
    direction: PortDirection
    data_type: DataType
    required: bool = True
    variadic: bool = False


@dataclass(frozen=True, slots=True)
class ParameterDefinition:
    key: str
    label: str
    kind: ParameterKind
    default_value: ParameterValue
    required: bool = True
    minimum: float | None = None
    maximum: float | None = None
    options: tuple[ParameterValue, ...] = ()
    description: str = ''


@dataclass(frozen=True, slots=True)
class AlgorithmDefinition:
    id: str
    name: str
    description: str
    category: str
    documentation_group: str
    inputs: tuple[PortDefinition, ...]
    outputs: tuple[PortDefinition, ...]
    parameters: tuple[ParameterDefinition, ...] = ()
    availability: str = 'configuration-only'
    documentation_reference: str | None = None