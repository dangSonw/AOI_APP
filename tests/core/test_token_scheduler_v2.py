from dataclasses import replace

import numpy as np

from core.pipeline import Connection, ConnectionKind, execute_workflow, create_default_workflow

def _port(node, key):
    return next(port for port in node.ports if port.template_key == key)


def test_scheduler_uses_runtime_keys_after_data_ports_are_renamed() -> None:
    workflow = create_default_workflow()
    renamed_nodes = []
    for node in workflow.nodes:
        renamed_nodes.append(replace(
            node,
            ports=tuple(
                replace(port, template_key=f'custom-{index}', display_label=f'Custom {index}')
                if port.channel.value == 'data' else port
                for index, port in enumerate(node.ports)
            ),
        ))
    workflow = replace(workflow, nodes=tuple(renamed_nodes))

    result = execute_workflow(workflow, source_image=np.zeros((16, 16, 3), dtype=np.uint8))

    assert len(result.records) == len(workflow.nodes)
    assert all(record.status == 'completed' for record in result.records)


def test_fault_emits_failure_token_and_does_not_emit_success_token() -> None:
    workflow = create_default_workflow()
    failed = replace(workflow.nodes[0], algorithm_id='patchcore')
    recovery = workflow.nodes[1]
    skipped = workflow.nodes[2]
    failed_failure = _port(failed, 'failure')
    failed_success = _port(failed, 'success')
    recovery_trigger = _port(recovery, 'trigger')
    skipped_trigger = _port(skipped, 'trigger')
    workflow = replace(
        workflow,
        nodes=(failed, recovery, skipped),
        connections=(
            Connection(
                '00000000-0000-4000-8000-000000000101', failed.id, failed_failure.id,
                recovery.id, recovery_trigger.id, ConnectionKind.CONTROL,
            ),
            Connection(
                '00000000-0000-4000-8000-000000000102', failed.id, failed_success.id,
                skipped.id, skipped_trigger.id, ConnectionKind.CONTROL,
            ),
        ),
        execution_order=(skipped.id, recovery.id, failed.id),
    )

    result = execute_workflow(workflow, source_image=np.zeros((8, 8, 3), dtype=np.uint8))

    assert [(record.node_instance_id, record.status) for record in result.records] == [
        (failed.id, 'faulted'),
        (recovery.id, 'faulted'),
    ]
    assert all(record.node_instance_id != skipped.id for record in result.records)


def test_v2_scheduler_finds_control_roots_without_execution_order_semantics() -> None:
    workflow = create_default_workflow()
    first, second = workflow.nodes[:2]
    workflow = replace(
        workflow,
        nodes=(first, second),
        connections=tuple(
            connection for connection in workflow.connections
            if connection.source_node_id in {first.id, second.id}
            and connection.target_node_id in {first.id, second.id}
        ),
        execution_order=(second.id, first.id),
    )

    result = execute_workflow(workflow, source_image=np.zeros((8, 8, 3), dtype=np.uint8))

    assert result.records[0].node_instance_id == first.id


def test_merge_all_waits_for_every_incoming_control_edge() -> None:
    from datetime import datetime, timezone
    from core.algorithms import DataType, PortDirection, get_algorithm_definition
    from core.pipeline import Point, PortChannel, PortInstance, PortOrigin, Workflow, WorkflowNode

    def node(node_id: str, algorithm_id: str, parameters: dict[str, object] | None = None) -> WorkflowNode:
        definition = get_algorithm_definition(algorithm_id)
        assert definition is not None
        ports = [
            PortInstance(
                id=f'{node_id}-{port.key}', template_key=port.key, direction=port.direction,
                data_type=port.data_type, display_label=port.label, required=port.required,
                variadic=port.variadic, variadic_instance_index=0 if port.variadic else None,
            ) for port in (*definition.inputs, *definition.outputs)
        ] + [
            PortInstance(
                id=f'{node_id}-{key}', template_key=key, direction=direction,
                data_type=DataType.GENERIC, display_label=key, required=False,
                channel=PortChannel.CONTROL, origin=PortOrigin.SYSTEM,
            ) for key, direction in (
                ('trigger', PortDirection.INPUT), ('success', PortDirection.OUTPUT),
                ('failure', PortDirection.OUTPUT),
            )
        ] + [
            PortInstance(
                id=f'{node_id}-{port.key}', template_key=port.key, direction=port.direction,
                data_type=DataType.GENERIC, display_label=port.label, required=port.required,
                variadic=port.variadic, variadic_instance_index=0 if port.variadic else None,
                channel=PortChannel.CONTROL, origin=PortOrigin.DEFAULT,
            ) for port in definition.control_ports
        ]
        return WorkflowNode(
            node_id, algorithm_id, definition.name, Point(0, 0),
            parameters or {parameter.key: parameter.default_value for parameter in definition.parameters},
            tuple(ports),
        )

    def data(index: int, source, source_key: str, target, target_key: str) -> Connection:
        return Connection(
            f'data-{index}', source.id, _port(source, source_key).id,
            target.id, _port(target, target_key).id,
        )

    def control(index: int, source, source_key: str, target) -> Connection:
        return Connection(
            f'control-{index}', source.id, _port(source, source_key).id,
            target.id, _port(target, 'trigger').id, ConnectionKind.CONTROL,
        )

    first = node('first', 'image-input')
    second = node('second', 'image-input')
    merge = node('merge', 'merge', {'policy': 'all'})
    output = node('output', 'image-output')
    workflow = Workflow(
        'merge-all', 'Merge all', 2, 0, datetime.now(timezone.utc),
        (first, second, merge, output),
        (
            data(1, first, 'image', output, 'image'),
            control(1, first, 'success', merge),
            control(2, second, 'success', merge),
            control(3, merge, 'merged', output),
        ),
        (first.id, second.id, merge.id, output.id),
    )

    result = execute_workflow(workflow, source_image=np.zeros((4, 4, 3), dtype=np.uint8))

    assert [record.algorithm_id for record in result.records] == [
        'image-input', 'image-input', 'merge', 'image-output',
    ]