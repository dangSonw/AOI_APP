from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum

from core.algorithms import DataType, ParameterValue, PortDirection


@dataclass(frozen=True, slots=True)
class Point:
    x: float
    y: float


class PortChannel(StrEnum):
    DATA = 'data'
    CONTROL = 'control'


class PortOrigin(StrEnum):
    SYSTEM = 'system'
    DEFAULT = 'default'
    CUSTOM = 'custom'


class RuntimeBindingMode(StrEnum):
    SLOT = 'slot'
    PASSTHROUGH = 'passthrough'
    NONE = 'none'


@dataclass(frozen=True, slots=True)
class PortInstance:
    id: str
    template_key: str
    direction: PortDirection
    data_type: DataType
    display_label: str
    required: bool
    variadic: bool = False
    variadic_instance_index: int | None = None
    channel: PortChannel = PortChannel.DATA
    origin: PortOrigin = PortOrigin.DEFAULT
    runtime_binding: RuntimeBindingMode = RuntimeBindingMode.SLOT
    runtime_key: str | None = None
    passthrough_input_port_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, 'channel', PortChannel(self.channel))
        object.__setattr__(self, 'origin', PortOrigin(self.origin))
        object.__setattr__(self, 'runtime_binding', RuntimeBindingMode(self.runtime_binding))
        if self.runtime_binding is RuntimeBindingMode.SLOT and self.runtime_key is None:
            object.__setattr__(self, 'runtime_key', self.template_key)
        if self.channel is PortChannel.CONTROL:
            object.__setattr__(self, 'data_type', DataType.GENERIC)
            object.__setattr__(self, 'runtime_binding', RuntimeBindingMode.NONE)
            object.__setattr__(self, 'runtime_key', None)
            object.__setattr__(self, 'passthrough_input_port_id', None)


@dataclass(frozen=True, slots=True)
class WorkflowNode:
    id: str
    algorithm_id: str
    display_name: str
    position: Point
    parameters: dict[str, ParameterValue]
    ports: tuple[PortInstance, ...]


class ConnectionKind(StrEnum):
    DATA = 'data'
    CONTROL = 'control'


@dataclass(frozen=True, slots=True)
class Connection:
    id: str
    source_node_id: str
    source_port_id: str
    target_node_id: str
    target_port_id: str
    kind: ConnectionKind = ConnectionKind.DATA
    max_traversals: int | None = None
    waypoints: tuple[Point, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, 'kind', ConnectionKind(self.kind))
        if self.max_traversals is not None and self.max_traversals < 1:
            raise ValueError('Maximum traversals must be at least one.')
        if self.kind is ConnectionKind.DATA and self.max_traversals is not None:
            raise ValueError('Only control connections can limit traversals.')


@dataclass(frozen=True, slots=True)
class Workflow:
    recipe_slug: str
    recipe_name: str
    version: int
    revision: int
    updated_at: datetime
    nodes: tuple[WorkflowNode, ...]
    connections: tuple[Connection, ...]
    execution_order: tuple[str, ...]
    migration_notices: tuple[str, ...] = ()

    def with_connections(self, connections: tuple[Connection, ...]) -> 'Workflow':
        return replace(self, connections=connections)


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    message: str
    node_id: str | None = None
    port_id: str | None = None
    connection_id: str | None = None