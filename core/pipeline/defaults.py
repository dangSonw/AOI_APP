from datetime import datetime, timezone

from core.algorithms import get_algorithm_definition

from .models import Connection, Point, PortInstance, Workflow, WorkflowNode
from .ordering import stable_topological_order


def _id(prefix: int, index: int) -> str:
    return f'{prefix:08d}-0000-4000-8000-{index:012d}'


def _node(index: int, algorithm_id: str, x: float, y: float) -> WorkflowNode:
    definition = get_algorithm_definition(algorithm_id)
    if definition is None:
        raise ValueError(f'Unknown default algorithm: {algorithm_id}')
    node_id = _id(3, index)
    ports = tuple(
        PortInstance(
            id=_id(4, index * 100 + port_index),
            template_key=port.key,
            direction=port.direction,
            data_type=port.data_type,
            display_label=port.label,
            required=port.required,
            variadic=port.variadic,
            variadic_instance_index=0 if port.variadic else None,
        )
        for port_index, port in enumerate((*definition.inputs, *definition.outputs), start=1)
    )
    return WorkflowNode(
        id=node_id,
        algorithm_id=algorithm_id,
        display_name=definition.name,
        position=Point(x, y),
        parameters={parameter.key: parameter.default_value for parameter in definition.parameters},
        ports=ports,
    )


def _port(node: WorkflowNode, key: str) -> str:
    return next(port.id for port in node.ports if port.template_key == key)


def _connection(index: int, source: WorkflowNode, source_key: str, target: WorkflowNode, target_key: str) -> Connection:
    return Connection(_id(5, index), source.id, _port(source, source_key), target.id, _port(target, target_key))


def create_default_workflow(
    recipe_slug: str = 'rev-c-mainboard',
    recipe_name: str = 'Rev C · Mainboard',
) -> Workflow:
    image = _node(1, 'image-input', 0, 180)
    registration = _node(2, 'ecc-registration', 260, 180)
    robust = _node(3, 'median-mad-robust-difference', 560, 40)
    patchcore = _node(4, 'patchcore', 560, 180)
    components = _node(5, 'golden-component-matching', 560, 320)
    fusion = _node(6, 'decision-fusion', 860, 180)
    output = _node(7, 'decision-output', 1120, 180)
    nodes = (image, registration, robust, patchcore, components, fusion, output)
    connections = (
        _connection(1, image, 'image', registration, 'image'),
        _connection(2, image, 'image', registration, 'reference'),
        _connection(3, registration, 'registered-image', robust, 'image'),
        _connection(4, registration, 'registered-image', patchcore, 'image'),
        _connection(5, registration, 'registered-image', components, 'image'),
        _connection(6, robust, 'score', fusion, 'scores'),
        _connection(7, patchcore, 'score', fusion, 'scores'),
        _connection(8, components, 'score', fusion, 'scores'),
        _connection(9, fusion, 'decision', output, 'decision'),
    )
    workflow = Workflow(recipe_slug, recipe_name, 1, 0, datetime.now(timezone.utc), nodes, connections, ())
    return Workflow(
        workflow.recipe_slug,
        workflow.recipe_name,
        workflow.version,
        workflow.revision,
        workflow.updated_at,
        workflow.nodes,
        workflow.connections,
        stable_topological_order(workflow, tuple(node.id for node in nodes)),
    )