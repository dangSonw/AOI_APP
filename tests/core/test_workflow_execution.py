from dataclasses import replace
from datetime import datetime, timezone

import numpy as np

from core.pipeline import create_default_workflow, execute_workflow
from core.algorithms import get_algorithm_definition
from core.pipeline.models import Connection, Point, PortInstance, Workflow, WorkflowNode


def test_default_workflow_executes_saved_dag_and_returns_preview() -> None:
    workflow = create_default_workflow()
    source = np.zeros((96, 128, 3), dtype=np.uint8)
    source[24:72, 32:96] = 220

    result = execute_workflow(workflow, source_image=source)

    assert result.final_image is not None
    assert result.final_image.shape[:2] == (96, 128)
    nodes_by_id = {node.id: node for node in workflow.nodes}
    assert [record.algorithm_id for record in result.records] == [
        nodes_by_id[node_id].algorithm_id for node_id in workflow.execution_order
    ]
    assert all(record.status == 'completed' for record in result.records)


def test_workflow_executor_rejects_unimplemented_test_node() -> None:
    workflow = create_default_workflow()
    first = workflow.nodes[0]
    unsupported = replace(first, algorithm_id='patchcore')
    broken = replace(workflow, nodes=(unsupported, *workflow.nodes[1:]))

    result = execute_workflow(broken, source_image=np.zeros((8, 8, 3), dtype=np.uint8))

    assert result.records[0].status == 'faulted'
    assert result.records[0].error_code == 'node-not-implemented'


def _runtime_node(node_id: str, algorithm_id: str) -> WorkflowNode:
    definition = get_algorithm_definition(algorithm_id)
    assert definition is not None
    return WorkflowNode(
        id=node_id,
        algorithm_id=algorithm_id,
        display_name=definition.name,
        position=Point(0, 0),
        parameters={parameter.key: parameter.default_value for parameter in definition.parameters},
        ports=tuple(
            PortInstance(
                id=f'{node_id}-{port.key}', template_key=port.key, direction=port.direction,
                data_type=port.data_type, display_label=port.label, required=port.required,
                variadic=port.variadic, variadic_instance_index=0 if port.variadic else None,
            )
            for port in (*definition.inputs, *definition.outputs)
        ),
    )


def test_transform_output_does_not_replace_latest_viewable_image() -> None:
    image_input = _runtime_node('input', 'image-input')
    registration = _runtime_node('registration', 'ecc-registration')
    connections = (
        Connection('image-edge', image_input.id, 'input-image', registration.id, 'registration-image'),
        Connection('reference-edge', image_input.id, 'input-image', registration.id, 'registration-reference'),
    )
    workflow = Workflow(
        'preview-contract', 'Preview contract', 1, 0, datetime.now(timezone.utc),
        (image_input, registration), connections, (image_input.id, registration.id),
    )
    source = np.random.default_rng(7).integers(0, 256, (48, 64, 3), dtype=np.uint8)

    result = execute_workflow(workflow, source_image=source)

    assert all(record.status == 'completed' for record in result.records)
    assert result.final_image is not None
    assert result.final_image.shape == source.shape