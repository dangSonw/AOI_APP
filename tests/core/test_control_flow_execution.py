from dataclasses import replace
from datetime import datetime, timezone

import numpy as np


def test_connections_distinguish_data_from_bounded_control_flow() -> None:
    from core.pipeline import Connection, ConnectionKind

    data = Connection('data', 'source', 'image', 'target', 'image')
    control = Connection(
        'control', 'source', 'completed', 'target', 'control-in',
        kind=ConnectionKind.CONTROL, max_traversals=3,
    )

    assert data.kind is ConnectionKind.DATA
    assert data.max_traversals is None
    assert control.kind is ConnectionKind.CONTROL
    assert control.max_traversals == 3


def _node(node_id: str, algorithm_id: str, *, parameters=None):
    from core.algorithms import get_algorithm_definition
    from core.algorithms import DataType, PortDirection
    from core.pipeline import Point, PortChannel, PortInstance, PortOrigin, WorkflowNode

    definition = get_algorithm_definition(algorithm_id)
    assert definition is not None
    return WorkflowNode(
        id=node_id,
        algorithm_id=algorithm_id,
        display_name=definition.name,
        position=Point(0, 0),
        parameters=parameters or {
            parameter.key: parameter.default_value for parameter in definition.parameters
        },
        ports=tuple([
            PortInstance(
                id=f'{node_id}-{port.key}', template_key=port.key,
                direction=port.direction, data_type=port.data_type,
                display_label=port.label, required=port.required,
                variadic=port.variadic,
                variadic_instance_index=0 if port.variadic else None,
            )
            for port in (*definition.inputs, *definition.outputs)
        ] + [
            PortInstance(
                id=f'{node_id}-{key}', template_key=key, direction=direction,
                data_type=DataType.GENERIC, display_label=key.capitalize(), required=False,
                channel=PortChannel.CONTROL, origin=PortOrigin.SYSTEM,
            )
            for key, direction in (
                ('trigger', PortDirection.INPUT),
                ('success', PortDirection.OUTPUT),
                ('failure', PortDirection.OUTPUT),
            )
        ] + [
            PortInstance(
                id=f'{node_id}-{port.key}', template_key=port.key, direction=port.direction,
                data_type=DataType.GENERIC, display_label=port.label, required=port.required,
                variadic=port.variadic,
                variadic_instance_index=0 if port.variadic else None,
                channel=PortChannel.CONTROL, origin=PortOrigin.DEFAULT,
            )
            for port in definition.control_ports
        ]),
    )


def _data(index, source, source_key, target, target_key):
    from core.pipeline import Connection

    return Connection(
        f'data-{index}', source.id, f'{source.id}-{source_key}',
        target.id, f'{target.id}-{target_key}',
    )


def _control(index, source, output, target, *, maximum=None):
    from core.pipeline import Connection, ConnectionKind

    return Connection(
        f'control-{index}', source.id, f'{source.id}-{output}', target.id, f'{target.id}-trigger',
        kind=ConnectionKind.CONTROL, max_traversals=maximum,
    )


def _control_workflow(*, bounded: bool = True, limit: int = 3):
    from core.pipeline import Workflow

    source = _node('source', 'image-input')
    counter = _node('counter', 'counter-limit', parameters={'limit': limit})
    delay = _node('delay', 'delay', parameters={'milliseconds': 0})
    output = _node('output', 'image-output')
    connections = (
        _data(1, source, 'image', delay, 'image'),
        _data(2, delay, 'delayed-image', output, 'image'),
        _control(1, source, 'success', counter),
        _control(2, counter, 'under-limit', delay),
        _control(3, delay, 'success', counter, maximum=max(1, limit - 1) if bounded else None),
        _control(4, counter, 'limit-reached', output),
    )
    return Workflow(
        'control-flow', 'Control flow', 1, 0, datetime.now(timezone.utc),
        (source, counter, delay, output),
        connections,
        (source.id, counter.id, delay.id, output.id),
    )


def test_validation_rejects_unbounded_control_cycles() -> None:
    from core.pipeline import validate_workflow

    unbounded_codes = {issue.code for issue in validate_workflow(_control_workflow(bounded=False))}
    assert 'unbounded-control-cycle' in unbounded_codes


def test_validation_requires_a_bound_for_each_independent_control_cycle() -> None:
    from core.pipeline import validate_workflow

    workflow = _control_workflow()
    output = workflow.nodes[-1]
    unbounded_self_cycle = _control(99, output, 'success', output)

    issues = validate_workflow(replace(
        workflow, connections=(*workflow.connections, unbounded_self_cycle),
    ))

    assert 'unbounded-control-cycle' in {issue.code for issue in issues}


def test_token_scheduler_counts_visits_until_limit_then_completes() -> None:
    from core.pipeline import execute_workflow

    result = execute_workflow(
        _control_workflow(), source_image=np.zeros((8, 8, 3), dtype=np.uint8),
    )

    assert [record.algorithm_id for record in result.records] == [
        'image-input', 'counter-limit', 'delay', 'counter-limit', 'delay',
        'counter-limit', 'image-output',
    ]
    counters = [record for record in result.records if record.algorithm_id == 'counter-limit']
    assert [record.visit_index for record in counters] == [1, 2, 3]
    assert [record.outputs['count'] for record in counters] == [1, 2, 3]
    assert [record.activation_sequence for record in result.records] == list(range(1, 8))
    assert all(record.activation_id for record in result.records)
    assert all(record.status == 'completed' for record in result.records)


def test_token_scheduler_replay_order_and_activation_ids_are_deterministic() -> None:
    from core.pipeline import execute_workflow

    workflow = _control_workflow()
    source = np.zeros((8, 8, 3), dtype=np.uint8)

    first = execute_workflow(workflow, source_image=source)
    replay = execute_workflow(workflow, source_image=source)

    assert [record.activation_id for record in replay.records] == [
        record.activation_id for record in first.records
    ]
    assert [record.node_instance_id for record in replay.records] == [
        record.node_instance_id for record in first.records
    ]
    assert [record.outputs for record in replay.records] == [
        record.outputs for record in first.records
    ]


def test_counter_limit_can_complete_without_traversing_feedback_edge() -> None:
    from core.pipeline import execute_workflow

    workflow = _control_workflow()
    workflow = replace(
        workflow,
        nodes=tuple(
            replace(node, parameters={'limit': 1}) if node.algorithm_id == 'counter-limit' else node
            for node in workflow.nodes
        ),
    )

    result = execute_workflow(workflow, source_image=np.zeros((8, 8, 3), dtype=np.uint8))

    assert [record.algorithm_id for record in result.records] == [
        'image-input', 'counter-limit', 'image-output',
    ]


def test_token_scheduler_checks_cancellation_during_control_cycle() -> None:
    from core.nodes import NodeExecutionContext
    from core.pipeline import execute_workflow

    probes = 0

    def cancelled() -> bool:
        nonlocal probes
        probes += 1
        return probes >= 6

    result = execute_workflow(
        _control_workflow(), source_image=np.zeros((8, 8, 3), dtype=np.uint8),
        context=NodeExecutionContext(is_cancelled=cancelled),
    )

    assert result.records[-1].status == 'cancelled'
    assert result.records[-1].error_code == 'node-execution-cancelled'
    assert result.records[-1].activation_sequence == len(result.records)


def test_token_scheduler_faults_at_global_activation_cap() -> None:
    from core.pipeline import execute_workflow

    workflow = _control_workflow()
    feedback = next(
        connection for connection in workflow.connections
        if connection.kind.value == 'control' and connection.source_port_id == 'delay-success'
    )
    workflow = replace(
        workflow,
        nodes=tuple(
            replace(node, parameters={'limit': 10_001}) if node.algorithm_id == 'counter-limit' else node
            for node in workflow.nodes
        ), connections=tuple(
            replace(connection, max_traversals=10_001) if connection.id == feedback.id else connection
            for connection in workflow.connections
        ),
    )

    result = execute_workflow(workflow, source_image=np.zeros((1, 1, 3), dtype=np.uint8))

    assert result.records[-1].status == 'faulted'
    assert result.records[-1].error_code == 'node-execution-error'
    assert '10000 node steps' in (result.records[-1].error_message or '')


def test_acyclic_workflow_keeps_legacy_executor_path() -> None:
    from core.pipeline import execute_workflow

    workflow = _control_workflow()
    legacy = replace(
        workflow,
        nodes=tuple(node for node in workflow.nodes if node.algorithm_id != 'counter-limit'),
        connections=(
            _data(10, workflow.nodes[0], 'image', workflow.nodes[2], 'image'),
            _data(11, workflow.nodes[2], 'delayed-image', workflow.nodes[-1], 'image'),
        ),
        execution_order=tuple(
            node.id for node in workflow.nodes if node.algorithm_id != 'counter-limit'
        ),
    )

    result = execute_workflow(legacy, source_image=np.zeros((8, 8, 3), dtype=np.uint8))

    assert [record.algorithm_id for record in result.records] == ['image-input', 'delay', 'image-output']