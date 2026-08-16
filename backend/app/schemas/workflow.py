from datetime import datetime
from typing import Self

from pydantic import Field, JsonValue, field_serializer

from app.schemas.base import ApiSchema
from core.algorithms import (
    AlgorithmDefinition,
    DataType,
    ParameterDefinition,
    ParameterKind,
    PortDefinition,
    PortDirection,
)
from core.pipeline import (
    Connection, ConnectionKind, Point, PortChannel, PortInstance, PortOrigin,
    RuntimeBindingMode, ValidationIssue, Workflow, WorkflowNode,
)
from core.nodes import NodeUse, get_node_runtime


class PortDefinitionSchema(ApiSchema):
    key: str
    label: str
    direction: PortDirection
    data_type: DataType
    required: bool
    variadic: bool

    @classmethod
    def from_core(cls, port: PortDefinition) -> Self:
        return cls.model_validate(port)


class ParameterDefinitionSchema(ApiSchema):
    key: str
    label: str
    kind: ParameterKind
    default_value: JsonValue
    required: bool
    minimum: float | None
    maximum: float | None
    options: tuple[JsonValue, ...]
    description: str

    @classmethod
    def from_core(cls, parameter: ParameterDefinition) -> Self:
        return cls.model_validate(parameter)


class AlgorithmDefinitionSchema(ApiSchema):
    id: str
    name: str
    description: str
    category: str
    documentation_group: str
    availability: str
    use: NodeUse
    inputs: tuple[PortDefinitionSchema, ...]
    outputs: tuple[PortDefinitionSchema, ...]
    control_ports: tuple[PortDefinitionSchema, ...]
    parameters: tuple[ParameterDefinitionSchema, ...]
    documentation_reference: str | None
    manifest_version: int
    package_version: str
    execution_target: str
    inspector_kind: str
    custom_inspector_key: str | None

    @classmethod
    def from_core(cls, definition: AlgorithmDefinition) -> Self:
        runtime = get_node_runtime(definition.id)
        if runtime is None:
            raise ValueError(f'Algorithm {definition.id} does not have a runtime package.')
        return cls(
            id=definition.id,
            name=definition.name,
            description=definition.description,
            category=definition.category,
            documentation_group=definition.documentation_group,
            availability=definition.availability,
            use=runtime.use,
            inputs=tuple(PortDefinitionSchema.from_core(port) for port in definition.inputs),
            outputs=tuple(PortDefinitionSchema.from_core(port) for port in definition.outputs),
            control_ports=tuple(PortDefinitionSchema.from_core(port) for port in definition.control_ports),
            parameters=tuple(ParameterDefinitionSchema.from_core(parameter) for parameter in definition.parameters),
            documentation_reference=definition.documentation_reference,
            manifest_version=definition.manifest_version,
            package_version=definition.package_version,
            execution_target=definition.execution_target,
            inspector_kind=definition.inspector_kind,
            custom_inspector_key=definition.custom_inspector_key,
        )


class AlgorithmDocumentationSchema(ApiSchema):
    algorithm_id: str
    language: str
    content: str


class PointSchema(ApiSchema):
    x: float
    y: float

    def to_core(self) -> Point:
        return Point(self.x, self.y)


class PortInstanceSchema(ApiSchema):
    id: str
    template_key: str
    direction: PortDirection
    data_type: DataType
    display_label: str
    required: bool
    variadic: bool
    variadic_instance_index: int | None = Field(default=None, ge=0)
    channel: PortChannel = PortChannel.DATA
    origin: PortOrigin = PortOrigin.DEFAULT
    runtime_binding: RuntimeBindingMode = RuntimeBindingMode.SLOT
    runtime_key: str | None = None
    passthrough_input_port_id: str | None = None

    def to_core(self) -> PortInstance:
        return PortInstance(
            id=self.id,
            template_key=self.template_key,
            direction=self.direction,
            data_type=self.data_type,
            display_label=self.display_label,
            required=self.required,
            variadic=self.variadic,
            variadic_instance_index=self.variadic_instance_index,
            channel=self.channel,
            origin=self.origin,
            runtime_binding=self.runtime_binding,
            runtime_key=self.runtime_key,
            passthrough_input_port_id=self.passthrough_input_port_id,
        )


class WorkflowNodeSchema(ApiSchema):
    id: str
    algorithm_id: str
    display_name: str
    position: PointSchema
    parameters: dict[str, JsonValue]
    ports: tuple[PortInstanceSchema, ...]

    def to_core(self) -> WorkflowNode:
        return WorkflowNode(
            id=self.id,
            algorithm_id=self.algorithm_id,
            display_name=self.display_name,
            position=self.position.to_core(),
            parameters=dict(self.parameters),
            ports=tuple(port.to_core() for port in self.ports),
        )


class ConnectionSchema(ApiSchema):
    id: str
    source_node_id: str
    source_port_id: str
    target_node_id: str
    target_port_id: str
    kind: ConnectionKind = ConnectionKind.DATA
    max_traversals: int | None = Field(default=None, ge=1)

    def to_core(self) -> Connection:
        return Connection(
            id=self.id,
            source_node_id=self.source_node_id,
            source_port_id=self.source_port_id,
            target_node_id=self.target_node_id,
            target_port_id=self.target_port_id,
            kind=self.kind,
            max_traversals=self.max_traversals,
        )


class WorkflowSchema(ApiSchema):
    recipe_slug: str
    recipe_name: str
    version: int = Field(ge=1)
    revision: int = Field(ge=0)
    updated_at: datetime
    nodes: tuple[WorkflowNodeSchema, ...]
    connections: tuple[ConnectionSchema, ...]
    execution_order: tuple[str, ...]
    migration_notices: tuple[str, ...] = ()

    @field_serializer('updated_at', when_used='json')
    def serialize_updated_at(self, value: datetime) -> str:
        return value.isoformat().replace('+00:00', 'Z')

    @classmethod
    def from_core(cls, workflow: Workflow) -> Self:
        return cls.model_validate(workflow)

    def to_core(self) -> Workflow:
        return Workflow(
            recipe_slug=self.recipe_slug,
            recipe_name=self.recipe_name,
            version=self.version,
            revision=self.revision,
            updated_at=self.updated_at,
            nodes=tuple(node.to_core() for node in self.nodes),
            connections=tuple(connection.to_core() for connection in self.connections),
            execution_order=tuple(self.execution_order),
            migration_notices=tuple(self.migration_notices),
        )


class ValidationIssueSchema(ApiSchema):
    code: str
    message: str
    node_id: str | None = None
    port_id: str | None = None
    connection_id: str | None = None

    @classmethod
    def from_core(cls, issue: ValidationIssue) -> Self:
        return cls.model_validate(issue)