from datetime import datetime, timezone
from uuid import UUID

from core.algorithms import get_algorithm_definition
from core.pipeline import Connection, Point, PortInstance, Workflow, WorkflowNode


NODE_IDS = {
    'source': '00000000-0000-4000-8000-000000000001',
    'left': '00000000-0000-4000-8000-000000000002',
    'right': '00000000-0000-4000-8000-000000000003',
    'merge': '00000000-0000-4000-8000-000000000004',
}


def _port_id(node_id: str, index: int) -> str:
    node_number = UUID(node_id).int & ((1 << 48) - 1)
    return f'20000000-0000-4000-8000-{node_number * 100 + index:012d}'


def make_node(name: str, algorithm_id: str, x: float) -> WorkflowNode:
    definition = get_algorithm_definition(algorithm_id)
    assert definition is not None
    node_id = NODE_IDS[name]
    ports = tuple(
        PortInstance(
            id=_port_id(node_id, index),
            template_key=port.key,
            direction=port.direction,
            data_type=port.data_type,
            display_label=port.label,
            required=port.required,
            variadic=port.variadic,
            variadic_instance_index=0 if port.variadic else None,
        )
        for index, port in enumerate((*definition.inputs, *definition.outputs))
    )
    return WorkflowNode(
        id=node_id,
        algorithm_id=algorithm_id,
        display_name=definition.name,
        position=Point(x=x, y=100),
        parameters={parameter.key: parameter.default_value for parameter in definition.parameters},
        ports=ports,
    )


def port_id(node: WorkflowNode, template_key: str) -> str:
    return next(port.id for port in node.ports if port.template_key == template_key)


def connection(index: int, source: WorkflowNode, source_key: str, target: WorkflowNode, target_key: str) -> Connection:
    return Connection(
        id=f'10000000-0000-4000-8000-{index:012d}',
        source_node_id=source.id,
        source_port_id=port_id(source, source_key),
        target_node_id=target.id,
        target_port_id=port_id(target, target_key),
    )


def branched_workflow() -> Workflow:
    source = make_node('source', 'image-input', 0)
    left = make_node('left', 'patchcore', 240)
    right = make_node('right', 'anomalydino', 240)
    merge = make_node('merge', 'decision-fusion', 500)
    connections = (
        connection(1, source, 'image', left, 'image'),
        connection(2, source, 'image', right, 'image'),
        connection(3, left, 'score', merge, 'scores'),
        connection(4, right, 'score', merge, 'scores'),
    )
    return Workflow(
        recipe_slug='test-recipe',
        recipe_name='Test recipe',
        version=1,
        revision=0,
        updated_at=datetime(2026, 8, 5, tzinfo=timezone.utc),
        nodes=(source, left, right, merge),
        connections=connections,
        execution_order=(source.id, right.id, left.id, merge.id),
    )