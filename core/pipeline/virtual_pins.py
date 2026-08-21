from dataclasses import dataclass

from core.algorithms import DataType

from .models import ConnectionKind, PortChannel, Workflow, WorkflowNode


INPUT_PIN_ID = 'input-pin'
OUTPUT_PIN_ID = 'output-pin'
VIRTUAL_PIN_IDS = frozenset({INPUT_PIN_ID, OUTPUT_PIN_ID})


@dataclass(frozen=True, slots=True)
class VirtualPinGroup:
    name: str
    input_nodes: tuple[WorkflowNode, ...]
    output_nodes: tuple[WorkflowNode, ...]
    concrete_types: frozenset[DataType]

    @property
    def inferred_type(self) -> DataType:
        if len(self.concrete_types) == 1:
            return next(iter(self.concrete_types))
        return DataType.GENERIC


def normalize_virtual_pin_name(node: WorkflowNode) -> str:
    return node.display_name.strip()


def resolve_virtual_pin_groups(workflow: Workflow) -> tuple[VirtualPinGroup, ...]:
    grouped: dict[str, dict[str, list[WorkflowNode]]] = {}
    for node in workflow.nodes:
        if node.algorithm_id not in VIRTUAL_PIN_IDS:
            continue
        name = normalize_virtual_pin_name(node)
        group = grouped.setdefault(name, {'inputs': [], 'outputs': []})
        group['inputs' if node.algorithm_id == INPUT_PIN_ID else 'outputs'].append(node)

    nodes = {node.id: node for node in workflow.nodes}
    ports = {
        (node.id, port.id): port
        for node in workflow.nodes
        for port in node.ports
    }
    result: list[VirtualPinGroup] = []
    for name, members in grouped.items():
        concrete_types: set[DataType] = set()
        member_ids = {node.id for node in (*members['inputs'], *members['outputs'])}
        for node in (*members['inputs'], *members['outputs']):
            concrete_types.update(
                port.data_type
                for port in node.ports
                if port.channel is PortChannel.DATA and port.data_type is not DataType.GENERIC
            )
        for connection in workflow.connections:
            if connection.kind is not ConnectionKind.DATA:
                continue
            source_node = nodes.get(connection.source_node_id)
            target_node = nodes.get(connection.target_node_id)
            source_port = ports.get((connection.source_node_id, connection.source_port_id))
            target_port = ports.get((connection.target_node_id, connection.target_port_id))
            if source_node is None or target_node is None or source_port is None or target_port is None:
                continue
            if target_node.id in member_ids and target_node.algorithm_id == INPUT_PIN_ID:
                if source_port.data_type is not DataType.GENERIC:
                    concrete_types.add(source_port.data_type)
            if source_node.id in member_ids and source_node.algorithm_id == OUTPUT_PIN_ID:
                if target_port.data_type is not DataType.GENERIC:
                    concrete_types.add(target_port.data_type)
        result.append(VirtualPinGroup(
            name=name,
            input_nodes=tuple(members['inputs']),
            output_nodes=tuple(members['outputs']),
            concrete_types=frozenset(concrete_types),
        ))
    return tuple(result)


def virtual_pin_dependencies(workflow: Workflow) -> tuple[tuple[str, str], ...]:
    return tuple(
        (group.input_nodes[0].id, output_node.id)
        for group in resolve_virtual_pin_groups(workflow)
        if group.name and len(group.input_nodes) == 1
        for output_node in group.output_nodes
    )


def resolve_virtual_pin_types(workflow: Workflow) -> dict[str, DataType]:
    return {
        node.id: group.inferred_type
        for group in resolve_virtual_pin_groups(workflow)
        for node in (*group.input_nodes, *group.output_nodes)
    }