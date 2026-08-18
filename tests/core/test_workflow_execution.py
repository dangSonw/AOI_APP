from dataclasses import replace
from datetime import datetime, timezone

import numpy as np
import pytest

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


def test_workflow_passes_context_only_to_contextual_executor(monkeypatch: pytest.MonkeyPatch) -> None:
    from core.nodes import NodeExecutionContext
    from core.pipeline import execution

    workflow = create_default_workflow()
    source = np.zeros((12, 16, 3), dtype=np.uint8)
    original_get_runtime = execution.get_node_runtime
    received_contexts = []

    def get_runtime(node_id: str):
        runtime = original_get_runtime(node_id)
        assert runtime is not None
        if node_id != 'image-input':
            return runtime

        def execute_with_context(inputs, parameters, context):
            received_contexts.append(context)
            return runtime.execute(inputs, parameters)

        return replace(runtime, execute_with_context=execute_with_context)

    monkeypatch.setattr(execution, 'get_node_runtime', get_runtime)
    context = NodeExecutionContext()

    result = execute_workflow(workflow, source_image=source, context=context)

    assert all(record.status == 'completed' for record in result.records)
    assert received_contexts == [context]


def test_workflow_stops_before_node_execution_when_context_is_cancelled() -> None:
    from core.nodes import NodeExecutionContext

    result = execute_workflow(
        create_default_workflow(),
        source_image=np.zeros((8, 8, 3), dtype=np.uint8),
        context=NodeExecutionContext(is_cancelled=lambda: True),
    )

    assert len(result.records) == 1
    assert result.records[0].status == 'cancelled'
    assert result.records[0].error_code == 'node-execution-cancelled'


def test_workflow_observer_reports_running_and_completed_with_instance_identity() -> None:
    events = []
    workflow = create_default_workflow()

    result = execute_workflow(
        workflow,
        source_image=np.zeros((8, 8, 3), dtype=np.uint8),
        observer=events.append,
    )

    assert events[0].status == 'running'
    assert events[0].node_instance_id == workflow.nodes[0].id
    assert events[0].algorithm_id == workflow.nodes[0].algorithm_id
    assert events[0].duration_ms is None
    assert events[1].status == 'completed'
    assert events[1].duration_ms is not None
    assert events[1].duration_ms >= 0
    assert tuple(event for event in events if event.status != 'running') == result.records


def test_failure_control_output_faults_node_without_emitting_success(monkeypatch: pytest.MonkeyPatch) -> None:
    from core.pipeline import execution

    workflow = create_default_workflow()
    original_get_runtime = execution.get_node_runtime

    def get_runtime(node_id: str):
        runtime = original_get_runtime(node_id)
        assert runtime is not None
        if node_id != workflow.nodes[0].algorithm_id:
            return runtime
        return replace(runtime, execute=lambda inputs, parameters: {
            **runtime.execute(inputs, parameters),
            '__control__': 'failure',
        })

    monkeypatch.setattr(execution, 'get_node_runtime', get_runtime)

    result = execute_workflow(workflow, source_image=np.zeros((8, 8, 3), dtype=np.uint8))

    assert result.records[0].status == 'faulted'
    assert result.records[0].error_code == 'node-reported-failure'