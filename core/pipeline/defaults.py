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
    grayscale = _node(2, 'color-conversion', 240, 180)
    blur = _node(3, 'gaussian-blur', 480, 180)
    threshold = _node(4, 'otsu-threshold', 720, 180)
    morphology = _node(5, 'morphology-operation', 960, 180)
    components = _node(6, 'connected-components', 1200, 80)
    draw = _node(7, 'draw-detections', 1440, 80)
    score = _node(8, 'mask-coverage-score', 1200, 300)
    fusion = _node(9, 'decision-fusion', 1440, 300)
    decision = _node(10, 'decision-output', 1680, 300)
    output = _node(11, 'image-output', 1680, 80)
    nodes = (image, grayscale, blur, threshold, morphology, components, draw, score, fusion, decision, output)
    connections = (
        _connection(1, image, 'image', grayscale, 'image'),
        _connection(2, grayscale, 'processed-image', blur, 'image'),
        _connection(3, blur, 'processed-image', threshold, 'image'),
        _connection(4, threshold, 'mask', morphology, 'mask'),
        _connection(5, morphology, 'processed-mask', components, 'mask'),
        _connection(6, image, 'image', draw, 'image'),
        _connection(7, components, 'detections', draw, 'detections'),
        _connection(8, morphology, 'processed-mask', score, 'mask'),
        _connection(9, score, 'score', fusion, 'scores'),
        _connection(10, fusion, 'decision', decision, 'decision'),
        _connection(11, draw, 'annotated-image', output, 'image'),
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