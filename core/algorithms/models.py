from dataclasses import dataclass
from enum import StrEnum
from typing import TypeAlias


JsonScalar: TypeAlias = None | bool | int | float | str
ParameterValue: TypeAlias = JsonScalar | list['ParameterValue'] | dict[str, 'ParameterValue']


def is_json_parameter_value(value: object, *, maximum_depth: int = 8, maximum_items: int = 1000, _depth: int = 0) -> bool:
    if _depth > maximum_depth:
        return False
    if value is None or isinstance(value, (bool, int, float, str)):
        return True
    if isinstance(value, list):
        return len(value) <= maximum_items and all(
            is_json_parameter_value(item, maximum_depth=maximum_depth, maximum_items=maximum_items, _depth=_depth + 1)
            for item in value
        )
    if isinstance(value, dict):
        return len(value) <= maximum_items and all(
            isinstance(key, str) and is_json_parameter_value(item, maximum_depth=maximum_depth, maximum_items=maximum_items, _depth=_depth + 1)
            for key, item in value.items()
        )
    return False


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
    JSON = 'json'
    REFERENCE = 'reference'


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
    manifest_version: int = 1
    package_version: str = '1.0.0'
    execution_target: str = 'local-cpu'
    inspector_kind: str = 'generic'
    custom_inspector_key: str | None = None
