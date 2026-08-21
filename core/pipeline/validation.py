import math
from collections import Counter, defaultdict
from uuid import UUID

from core.algorithms import DataType, ParameterKind, PortDirection, get_algorithm_definition, is_json_parameter_value

from .models import (
    ConnectionKind, PortChannel, PortInstance, PortOrigin, RuntimeBindingMode,
    ValidationIssue, Workflow,
)
from .ordering import CycleError, stable_topological_order
from .virtual_pins import resolve_virtual_pin_groups, virtual_pin_dependencies


def _is_uuid(value: str) -> bool:
    try:
        UUID(value)
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def _parameter_is_valid(kind: ParameterKind, value: object) -> bool:
    if kind is ParameterKind.BOOLEAN:
        return isinstance(value, bool)
    if kind is ParameterKind.INTEGER:
        return isinstance(value, int) and not isinstance(value, bool)
    if kind is ParameterKind.NUMBER:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    if kind is ParameterKind.JSON:
        return is_json_parameter_value(value)
    if kind is ParameterKind.REFERENCE:
        return is_json_parameter_value(value)
    return isinstance(value, str)


def validate_workflow(workflow: Workflow) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    node_counts = Counter(node.id for node in workflow.nodes)
    connection_counts = Counter(connection.id for connection in workflow.connections)
    all_ids = [node.id for node in workflow.nodes] + [port.id for node in workflow.nodes for port in node.ports] + [connection.id for connection in workflow.connections]
    duplicate_ids = {item_id for item_id, count in Counter(all_ids).items() if count > 1}
    nodes = {node.id: node for node in workflow.nodes}
    ports: dict[tuple[str, str], PortInstance] = {
        (node.id, port.id): port for node in workflow.nodes for port in node.ports
    }

    for node in workflow.nodes:
        if node_counts[node.id] > 1 or node.id in duplicate_ids or not _is_uuid(node.id):
            issues.append(ValidationIssue('duplicate-id', 'Node and port IDs must be unique UUIDs.', node_id=node.id))
        if not node.display_name.strip() or not math.isfinite(node.position.x) or not math.isfinite(node.position.y):
            issues.append(ValidationIssue('invalid-parameter', 'Node presentation values are invalid.', node_id=node.id))
        definition = get_algorithm_definition(node.algorithm_id)
        if definition is None:
            issues.append(ValidationIssue('unknown-algorithm', f'Algorithm {node.algorithm_id} is not in the catalog.', node_id=node.id))
            continue

        templates = {port.key: port for port in (*definition.inputs, *definition.outputs)}
        port_keys = Counter(port.template_key for port in node.ports)
        for port in node.ports:
            if port.id in duplicate_ids or not _is_uuid(port.id):
                issues.append(ValidationIssue('duplicate-id', 'Node and port IDs must be unique UUIDs.', node_id=node.id, port_id=port.id))
            if not port.template_key.strip() or port_keys[port.template_key] > 1:
                issues.append(ValidationIssue('duplicate-port-key', 'Port keys must be non-empty and unique within a node.', node_id=node.id, port_id=port.id))
            if port.channel is PortChannel.CONTROL:
                if port.origin is PortOrigin.SYSTEM and (port.template_key, port.direction) not in {
                    ('trigger', PortDirection.INPUT), ('success', PortDirection.OUTPUT), ('failure', PortDirection.OUTPUT),
                }:
                    issues.append(ValidationIssue('invalid-system-port', 'System control ports cannot be changed.', node_id=node.id, port_id=port.id))
                continue
            if port.runtime_binding is RuntimeBindingMode.SLOT:
                template = templates.get(port.runtime_key or '')
                if template is None or template.direction is not port.direction:
                    issues.append(ValidationIssue('unknown-runtime-slot', 'The data port runtime slot is not available for this direction.', node_id=node.id, port_id=port.id))
                elif template.data_type is not DataType.GENERIC and port.data_type is not template.data_type:
                    issues.append(ValidationIssue('type-mismatch', 'The data port type is incompatible with its runtime slot.', node_id=node.id, port_id=port.id))
            elif port.runtime_binding is RuntimeBindingMode.PASSTHROUGH:
                source = next((candidate for candidate in node.ports if candidate.id == port.passthrough_input_port_id), None)
                if port.direction is not PortDirection.OUTPUT or source is None or source.direction is not PortDirection.INPUT or source.channel is not PortChannel.DATA:
                    issues.append(ValidationIssue('invalid-passthrough', 'Passthrough outputs require one data input on the same node.', node_id=node.id, port_id=port.id))
                elif source.data_type is not port.data_type:
                    issues.append(ValidationIssue('type-mismatch', 'Passthrough input and output types must match.', node_id=node.id, port_id=port.id))

        system_ports = {(port.template_key, port.direction) for port in node.ports if port.origin is PortOrigin.SYSTEM and port.channel is PortChannel.CONTROL}
        if workflow.version >= 2 and system_ports != {
            ('trigger', PortDirection.INPUT), ('success', PortDirection.OUTPUT), ('failure', PortDirection.OUTPUT),
        }:
            issues.append(ValidationIssue('missing-system-port', 'Every node requires trigger, success, and failure system control ports.', node_id=node.id))

        bound_slots = {
            (port.runtime_key, port.direction) for port in node.ports
            if port.channel is PortChannel.DATA and port.runtime_binding is RuntimeBindingMode.SLOT
        }
        for template in (*definition.inputs, *definition.outputs):
            if template.required and (template.key, template.direction) not in bound_slots:
                issues.append(ValidationIssue('missing-runtime-slot', f'Required runtime slot {template.label} is not bound.', node_id=node.id))

        parameter_definitions = {parameter.key: parameter for parameter in definition.parameters}
        for key in sorted(set(node.parameters) | set(parameter_definitions)):
            parameter = parameter_definitions.get(key)
            value = node.parameters.get(key)
            valid = parameter is not None and (key in node.parameters or not parameter.required)
            if valid and key in node.parameters:
                valid = _parameter_is_valid(parameter.kind, value)
            if valid and parameter.kind in (ParameterKind.INTEGER, ParameterKind.NUMBER):
                numeric_value = float(value)
                valid = (parameter.minimum is None or numeric_value >= parameter.minimum) and (parameter.maximum is None or numeric_value <= parameter.maximum)
            if valid and parameter.kind is ParameterKind.SELECT:
                valid = value in parameter.options
            if not valid:
                issues.append(ValidationIssue('invalid-parameter', f'Parameter {key} is invalid.', node_id=node.id))

    for group in resolve_virtual_pin_groups(workflow):
        if not group.name:
            for node in (*group.input_nodes, *group.output_nodes):
                issues.append(ValidationIssue(
                    'invalid-parameter', 'Virtual pin display name cannot be empty.', node_id=node.id,
                ))
            continue
        if len(group.input_nodes) != 1:
            for node in (*group.input_nodes, *group.output_nodes):
                issues.append(ValidationIssue(
                    'invalid-parameter',
                    f'Virtual pin channel {group.name} requires exactly one Input Pin.',
                    node_id=node.id,
                ))
        if not group.output_nodes:
            for node in group.input_nodes:
                issues.append(ValidationIssue(
                    'invalid-parameter',
                    f'Input Pin {group.name} requires at least one matching Output Pin.',
                    node_id=node.id,
                ))
        if not group.input_nodes:
            for node in group.output_nodes:
                issues.append(ValidationIssue(
                    'invalid-parameter',
                    f'Output Pin {group.name} requires a matching Input Pin.',
                    node_id=node.id,
                ))
        if len(group.concrete_types) > 1:
            issues.append(ValidationIssue(
                'generic-type-conflict',
                f'Virtual pin channel {group.name} resolves to conflicting data types: '
                f'{", ".join(sorted(item.value for item in group.concrete_types))}.',
                node_id=(group.input_nodes or group.output_nodes)[0].id,
            ))

    endpoint_counts: Counter[tuple[str, str, str, str]] = Counter()
    target_counts: Counter[tuple[str, str]] = Counter()
    incoming: dict[tuple[str, str], int] = defaultdict(int)
    generic_types: dict[str, set[DataType]] = defaultdict(set)
    for connection in workflow.connections:
        if any(not math.isfinite(point.x) or not math.isfinite(point.y) for point in connection.waypoints):
            issues.append(ValidationIssue(
                'invalid-parameter', 'Connection waypoints require finite coordinates.',
                connection_id=connection.id,
            ))
        endpoint = (connection.source_node_id, connection.source_port_id, connection.target_node_id, connection.target_port_id)
        endpoint_counts[endpoint] += 1
        target_counts[(connection.target_node_id, connection.target_port_id)] += 1
        if connection_counts[connection.id] > 1 or connection.id in duplicate_ids or not _is_uuid(connection.id):
            issues.append(ValidationIssue('duplicate-id', 'Connection IDs must be unique UUIDs.', connection_id=connection.id))
        if endpoint_counts[endpoint] > 1:
            issues.append(ValidationIssue('duplicate-connection', 'The same ports are already connected.', connection_id=connection.id))
        if connection.source_node_id == connection.target_node_id and connection.kind is ConnectionKind.DATA:
            issues.append(ValidationIssue('self-loop', 'A node cannot connect to itself.', connection_id=connection.id))
        source_node = nodes.get(connection.source_node_id)
        target_node = nodes.get(connection.target_node_id)
        if source_node is None or target_node is None:
            issues.append(ValidationIssue('unknown-node', 'A connection endpoint node does not exist.', connection_id=connection.id))
            continue
        source_port = ports.get((source_node.id, connection.source_port_id))
        target_port = ports.get((target_node.id, connection.target_port_id))
        if source_port is None or target_port is None:
            missing_port = connection.source_port_id if source_port is None else connection.target_port_id
            issues.append(ValidationIssue('unknown-port', 'A connection endpoint port does not exist.', port_id=missing_port, connection_id=connection.id))
            continue
        if connection.kind is ConnectionKind.CONTROL:
            if (
                source_port.channel is not PortChannel.CONTROL or target_port.channel is not PortChannel.CONTROL
                or source_port.direction is not PortDirection.OUTPUT or target_port.direction is not PortDirection.INPUT
            ):
                issues.append(ValidationIssue('unknown-port', 'Control connections require control output and input ports.', connection_id=connection.id))
            continue
        if source_port.channel is not PortChannel.DATA or target_port.channel is not PortChannel.DATA:
            issues.append(ValidationIssue('unknown-port', 'Data connections require data output and input ports.', connection_id=connection.id))
            continue
        incoming[(target_node.id, target_port.id)] += 1
        if source_port.direction is not PortDirection.OUTPUT or target_port.direction is not PortDirection.INPUT:
            issues.append(ValidationIssue('unknown-port', 'Connections must run from an output to an input.', connection_id=connection.id))
        if source_port.data_type is DataType.GENERIC and target_port.data_type is not DataType.GENERIC:
            generic_types[source_node.id].add(target_port.data_type)
        elif target_port.data_type is DataType.GENERIC and source_port.data_type is not DataType.GENERIC:
            generic_types[target_node.id].add(source_port.data_type)
        elif source_port.data_type is not target_port.data_type:
            issues.append(ValidationIssue('type-mismatch', 'Connected ports require exactly the same data type.', connection_id=connection.id))
        if target_counts[(target_node.id, target_port.id)] > 1 and not target_port.variadic:
            issues.append(ValidationIssue('input-already-connected', 'The target input already has a connection.', port_id=target_port.id, connection_id=connection.id))

    for node in workflow.nodes:
        for port in node.ports:
            if port.channel is PortChannel.DATA and port.direction is PortDirection.INPUT and port.required and incoming[(node.id, port.id)] == 0:
                issues.append(ValidationIssue('missing-required-input', f'Input {port.display_label} requires a connection.', node_id=node.id, port_id=port.id))
        if len(generic_types[node.id]) > 1:
            issues.append(ValidationIssue(
                'generic-type-conflict', 'Generic ports on one node must resolve to one data type.',
                node_id=node.id,
            ))

    control_connections = tuple(
        connection for connection in workflow.connections
        if connection.kind is ConnectionKind.CONTROL
        and connection.source_node_id in nodes and connection.target_node_id in nodes
    )
    unbounded_graph: dict[str, list[str]] = defaultdict(list)
    for connection in control_connections:
        if connection.max_traversals is None:
            unbounded_graph[connection.source_node_id].append(connection.target_node_id)

    def has_unbounded_cycle() -> bool:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str) -> bool:
            if node_id in visiting:
                return True
            if node_id in visited:
                return False
            visiting.add(node_id)
            if any(visit(target_id) for target_id in unbounded_graph[node_id]):
                return True
            visiting.remove(node_id)
            visited.add(node_id)
            return False

        return any(visit(node_id) for node_id in nodes if node_id not in visited)

    if has_unbounded_cycle():
        issues.append(ValidationIssue(
            'unbounded-control-cycle', 'Every control cycle requires a bounded traversal edge.',
        ))

    try:
        stable_topological_order(workflow)
    except CycleError:
        issues.append(ValidationIssue('cycle', 'The workflow must be a directed acyclic graph.'))

    expected_ids = [node.id for node in workflow.nodes]
    if len(workflow.execution_order) != len(expected_ids) or Counter(workflow.execution_order) != Counter(expected_ids):
        issues.append(ValidationIssue('execution-order-mismatch', 'Execution order must contain every node exactly once.'))
    else:
        order_index = {node_id: index for index, node_id in enumerate(workflow.execution_order)}
        for connection in workflow.connections:
            if (
                connection.kind is ConnectionKind.DATA
                and connection.source_node_id in order_index and connection.target_node_id in order_index
                and order_index[connection.source_node_id] >= order_index[connection.target_node_id]
            ):
                issues.append(ValidationIssue('dependency-order', 'Dependencies must execute before consumers.', connection_id=connection.id))
        for source_node_id, target_node_id in virtual_pin_dependencies(workflow):
            if order_index[source_node_id] >= order_index[target_node_id]:
                issues.append(ValidationIssue(
                    'dependency-order',
                    'Input Pin dependencies must execute before matching Output Pins.',
                    node_id=target_node_id,
                ))

    return tuple(issues)