from dataclasses import replace
from datetime import datetime, timezone

import numpy as np
import pytest

from core.algorithms import DataType, get_algorithm_definition
from core.pipeline import (
    Connection, CycleError, Point, PortInstance, Workflow, WorkflowNode,
    execute_workflow, stable_topological_order, validate_workflow,
)


def _uuid(prefix: int, index: int) -> str:
    return f'{prefix:08d}-0000-4000-8000-{index:012d}'


def _node(index: int, algorithm_id: str, *, display_name: str | None = None) -> WorkflowNode:
    definition = get_algorithm_definition(algorithm_id)
    assert definition is not None, f'{algorithm_id} must be registered before virtual pin workflows can be built.'
    return WorkflowNode(
        id=_uuid(1, index),
        algorithm_id=algorithm_id,
        display_name=display_name or definition.name,
        position=Point(index * 160, 0),
        parameters={parameter.key: parameter.default_value for parameter in definition.parameters},
        ports=tuple(
            PortInstance(
                id=_uuid(2, index * 100 + port_index),
                template_key=port.key,
                direction=port.direction,
                data_type=port.data_type,
                display_label=port.label,
                required=port.required,
                variadic=port.variadic,
                variadic_instance_index=0 if port.variadic else None,
            )
            for port_index, port in enumerate((*definition.inputs, *definition.outputs), start=1)
        ),
    )


def _port(node: WorkflowNode, key: str) -> str:
    return next(port.id for port in node.ports if port.template_key == key)


def _connection(
    index: int,
    source: WorkflowNode,
    source_key: str,
    target: WorkflowNode,
    target_key: str,
) -> Connection:
    return Connection(
        id=_uuid(3, index),
        source_node_id=source.id,
        source_port_id=_port(source, source_key),
        target_node_id=target.id,
        target_port_id=_port(target, target_key),
    )


def _workflow(
    nodes: tuple[WorkflowNode, ...],
    connections: tuple[Connection, ...],
    execution_order: tuple[str, ...] | None = None,
) -> Workflow:
    return Workflow(
        recipe_slug='virtual-pins',
        recipe_name='Virtual pins',
        version=1,
        revision=0,
        updated_at=datetime(2026, 8, 19, tzinfo=timezone.utc),
        nodes=nodes,
        connections=connections,
        execution_order=execution_order or tuple(node.id for node in nodes),
    )


def _image_pin_workflow() -> Workflow:
    source = _node(1, 'image-input')
    input_pin = _node(2, 'input-pin', display_name=' Board image ')
    output_pin = _node(3, 'output-pin', display_name='Board image')
    sink = _node(4, 'image-output')
    return _workflow(
        (source, input_pin, output_pin, sink),
        (
            _connection(1, source, 'image', input_pin, 'value'),
            _connection(2, output_pin, 'value', sink, 'image'),
        ),
    )


def test_virtual_pin_names_trim_outer_whitespace_but_remain_case_sensitive() -> None:
    workflow = _image_pin_workflow()

    assert validate_workflow(workflow) == ()

    output_pin = workflow.nodes[2]
    mismatched = replace(
        workflow,
        nodes=(*workflow.nodes[:2], replace(output_pin, display_name='board image'), workflow.nodes[3]),
    )
    messages = [issue.message for issue in validate_workflow(mismatched) if issue.code == 'invalid-parameter']

    assert any('Board image' in message and 'matching Output Pin' in message for message in messages)
    assert any('board image' in message and 'matching Input Pin' in message for message in messages)


def test_virtual_pin_validation_rejects_duplicate_inputs_and_cross_endpoint_type_conflicts() -> None:
    workflow = _image_pin_workflow()
    source, input_pin, output_pin, _ = workflow.nodes
    duplicate_input = _node(5, 'input-pin', display_name='Board image')
    duplicate_workflow = replace(
        workflow,
        nodes=(*workflow.nodes, duplicate_input),
        connections=(*workflow.connections, _connection(3, source, 'image', duplicate_input, 'value')),
        execution_order=(*workflow.execution_order, duplicate_input.id),
    )

    duplicate_messages = [
        issue.message for issue in validate_workflow(duplicate_workflow) if issue.code == 'invalid-parameter'
    ]
    assert any('exactly one Input Pin' in message for message in duplicate_messages)

    decision_sink = _node(6, 'decision-output')
    conflict = _workflow(
        (source, input_pin, output_pin, decision_sink),
        (
            _connection(4, source, 'image', input_pin, 'value'),
            _connection(5, output_pin, 'value', decision_sink, 'decision'),
        ),
    )

    conflicts = [issue for issue in validate_workflow(conflict) if issue.code == 'generic-type-conflict']
    assert len(conflicts) == 1
    assert 'Board image' in conflicts[0].message
    assert 'decision' in conflicts[0].message
    assert 'image' in conflicts[0].message


def test_virtual_pin_dependency_participates_in_ordering_and_cycle_detection() -> None:
    workflow = _image_pin_workflow()
    source, input_pin, output_pin, sink = workflow.nodes

    ordered = stable_topological_order(workflow, (sink.id, output_pin.id, input_pin.id, source.id))

    assert ordered == (source.id, input_pin.id, output_pin.id, sink.id)

    blur = _node(7, 'gaussian-blur')
    loop_input = _node(8, 'input-pin', display_name='Loop')
    loop_output = _node(9, 'output-pin', display_name='Loop')
    cyclic = _workflow(
        (loop_input, loop_output, blur),
        (
            _connection(6, loop_output, 'value', blur, 'image'),
            _connection(7, blur, 'processed-image', loop_input, 'value'),
        ),
    )

    assert 'cycle' in {issue.code for issue in validate_workflow(cyclic)}
    with pytest.raises(CycleError):
        stable_topological_order(cyclic)


def test_one_input_pin_can_feed_multiple_output_pins_without_copying_the_image() -> None:
    source = _node(10, 'image-input')
    input_pin = _node(11, 'input-pin', display_name='Camera')
    first_output = _node(12, 'output-pin', display_name='Camera')
    second_output = _node(13, 'output-pin', display_name='Camera')
    first_sink = _node(14, 'image-output')
    second_sink = _node(15, 'image-output')
    workflow = _workflow(
        (source, input_pin, first_output, first_sink, second_output, second_sink),
        (
            _connection(8, source, 'image', input_pin, 'value'),
            _connection(9, first_output, 'value', first_sink, 'image'),
            _connection(10, second_output, 'value', second_sink, 'image'),
        ),
    )
    image = np.random.default_rng(19).integers(0, 256, (24, 32, 3), dtype=np.uint8)

    assert validate_workflow(workflow) == ()
    result = execute_workflow(workflow, source_image=image)

    assert [record.algorithm_id for record in result.records].count('input-pin') == 1
    assert [record.algorithm_id for record in result.records].count('output-pin') == 2
    assert all(record.status == 'completed' for record in result.records)
    assert result.final_image is image


def test_virtual_pin_ports_remain_generic_while_the_channel_infers_image() -> None:
    workflow = _image_pin_workflow()
    input_pin, output_pin = workflow.nodes[1:3]

    assert input_pin.ports[0].data_type is DataType.GENERIC
    assert output_pin.ports[0].data_type is DataType.GENERIC
    assert validate_workflow(workflow) == ()


def test_virtual_pin_runtime_preserves_boolean_and_score_values() -> None:
    cases = (
        ('logic-not', 'result', False, DataType.BOOLEAN),
        ('mask-coverage-score', 'score', 0.375, DataType.SCORE),
    )
    for offset, (source_algorithm, source_key, value, data_type) in enumerate(cases, start=20):
        source = _node(offset, source_algorithm)
        input_pin = _node(offset + 10, 'input-pin', display_name=f'Channel {data_type.value}')
        output_pin = _node(offset + 20, 'output-pin', display_name=f'Channel {data_type.value}')
        workflow = _workflow(
            (source, input_pin, output_pin),
            (_connection(offset, source, source_key, input_pin, 'value'),),
        )
        source_output = next(port for port in source.ports if port.template_key == source_key)
        output_value = next(port for port in output_pin.ports if port.template_key == 'value')

        from core.pipeline import execution

        runtime = execution.get_node_runtime(source_algorithm)
        assert runtime is not None
        pin_runtime = execution.get_node_runtime('output-pin')
        assert pin_runtime is not None
        assert source_output.data_type is data_type
        assert output_value.data_type is DataType.GENERIC
        assert pin_runtime.execute({'value': value}, {})['value'] is value