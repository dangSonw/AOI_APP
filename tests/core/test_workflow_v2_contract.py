from dataclasses import replace

from core.algorithms import DataType, PortDirection, get_algorithm_definition
from core.pipeline import (
    Connection,
    ConnectionKind,
    Point,
    PortChannel,
    PortInstance,
    PortOrigin,
    RuntimeBindingMode,
    Workflow,
    WorkflowNode,
    create_default_workflow,
    validate_workflow,
)


def test_default_nodes_have_locked_system_control_ports() -> None:
    workflow = create_default_workflow()

    assert workflow.version == 2
    for node in workflow.nodes:
        controls = {
            (port.template_key, port.direction): port
            for port in node.ports
            if port.channel is PortChannel.CONTROL
        }
        assert set(controls) >= {
            ('trigger', PortDirection.INPUT),
            ('success', PortDirection.OUTPUT),
            ('failure', PortDirection.OUTPUT),
        }
        assert all(port.origin is PortOrigin.SYSTEM for port in controls.values())
        assert all(port.runtime_binding is RuntimeBindingMode.NONE for port in controls.values())


def test_node_instance_accepts_custom_typed_ports_with_runtime_bindings() -> None:
    definition = get_algorithm_definition('gaussian-blur')
    assert definition is not None
    node = WorkflowNode(
        id='00000000-0000-4000-8000-000000000001',
        algorithm_id=definition.id,
        display_name=definition.name,
        position=Point(0, 0),
        parameters={parameter.key: parameter.default_value for parameter in definition.parameters},
        ports=(
            PortInstance(
                id='00000000-0000-4000-8000-000000000002',
                template_key='camera-frame',
                direction=PortDirection.INPUT,
                data_type=DataType.IMAGE,
                display_label='Camera frame',
                required=True,
                channel=PortChannel.DATA,
                origin=PortOrigin.CUSTOM,
                runtime_binding=RuntimeBindingMode.SLOT,
                runtime_key='image',
            ),
            PortInstance(
                id='00000000-0000-4000-8000-000000000003',
                template_key='blurred-frame',
                direction=PortDirection.OUTPUT,
                data_type=DataType.IMAGE,
                display_label='Blurred frame',
                required=True,
                channel=PortChannel.DATA,
                origin=PortOrigin.CUSTOM,
                runtime_binding=RuntimeBindingMode.SLOT,
                runtime_key='processed-image',
            ),
        ),
    )

    workflow = Workflow('dynamic-ports', 'Dynamic ports', 2, 0, create_default_workflow().updated_at, (node,), (), (node.id,))

    assert not {'unknown-port', 'type-mismatch'} & {issue.code for issue in validate_workflow(workflow)}


def test_control_feedback_requires_a_bounded_edge() -> None:
    workflow = create_default_workflow()
    first, second = workflow.nodes[:2]
    first_success = next(port for port in first.ports if port.template_key == 'success')
    first_trigger = next(port for port in first.ports if port.template_key == 'trigger')
    second_success = next(port for port in second.ports if port.template_key == 'success')
    second_trigger = next(port for port in second.ports if port.template_key == 'trigger')
    forward = Connection(
        '00000000-0000-4000-8000-000000000010', first.id, first_success.id,
        second.id, second_trigger.id, ConnectionKind.CONTROL,
    )
    feedback = Connection(
        '00000000-0000-4000-8000-000000000011', second.id, second_success.id,
        first.id, first_trigger.id, ConnectionKind.CONTROL,
    )
    cyclic = replace(workflow, nodes=(first, second), connections=(forward, feedback), execution_order=(first.id, second.id))
    bounded = replace(cyclic, connections=(forward, replace(feedback, max_traversals=3)))

    assert 'unbounded-control-cycle' in {issue.code for issue in validate_workflow(cyclic)}
    assert 'unbounded-control-cycle' not in {issue.code for issue in validate_workflow(bounded)}
