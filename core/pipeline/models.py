from dataclasses import dataclass, replace
from datetime import datetime

from core.algorithms import DataType, ParameterValue, PortDirection


@dataclass(frozen=True, slots=True)
class Point:
    x: float
    y: float


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


@dataclass(frozen=True, slots=True)
class WorkflowNode:
    id: str
    algorithm_id: str
    display_name: str
    position: Point
    parameters: dict[str, ParameterValue]
    ports: tuple[PortInstance, ...]


@dataclass(frozen=True, slots=True)
class Connection:
    id: str
    source_node_id: str
    source_port_id: str
    target_node_id: str
    target_port_id: str


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

    def with_connections(self, connections: tuple[Connection, ...]) -> 'Workflow':
        return replace(self, connections=connections)


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    message: str
    node_id: str | None = None
    port_id: str | None = None
    connection_id: str | None = None