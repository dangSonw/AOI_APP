import math
from collections import Counter, defaultdict
from uuid import UUID

from core.algorithms import ParameterKind, PortDirection, get_algorithm_definition

from .models import PortInstance, ValidationIssue, Workflow
from .ordering import CycleError, stable_topological_order


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
        instance_templates = Counter(port.template_key for port in node.ports)
        for port in node.ports:
            template = templates.get(port.template_key)
            if port.id in duplicate_ids or not _is_uuid(port.id):
                issues.append(ValidationIssue('duplicate-id', 'Node and port IDs must be unique UUIDs.', node_id=node.id, port_id=port.id))
            if template is None or port.direction is not template.direction:
                issues.append(ValidationIssue('unknown-port', 'The node contains a port not defined by its algorithm.', node_id=node.id, port_id=port.id))
            elif port.data_type is not template.data_type:
                issues.append(ValidationIssue('type-mismatch', 'The port type differs from its catalog definition.', node_id=node.id, port_id=port.id))
            elif instance_templates[port.template_key] > 1 and not template.variadic:
                issues.append(ValidationIssue('duplicate-id', 'A non-variadic port template can have only one instance.', node_id=node.id, port_id=port.id))
        for template in (*definition.inputs, *definition.outputs):
            if instance_templates[template.key] == 0:
                code = 'missing-required-input' if template.direction is PortDirection.INPUT and template.required else 'unknown-port'
                issues.append(ValidationIssue(code, f'Required port {template.label} is missing.', node_id=node.id))

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

    endpoint_counts: Counter[tuple[str, str, str, str]] = Counter()
    target_counts: Counter[tuple[str, str]] = Counter()
    incoming: dict[tuple[str, str], int] = defaultdict(int)
    for connection in workflow.connections:
        endpoint = (connection.source_node_id, connection.source_port_id, connection.target_node_id, connection.target_port_id)
        endpoint_counts[endpoint] += 1
        target_counts[(connection.target_node_id, connection.target_port_id)] += 1
        if connection_counts[connection.id] > 1 or connection.id in duplicate_ids or not _is_uuid(connection.id):
            issues.append(ValidationIssue('duplicate-id', 'Connection IDs must be unique UUIDs.', connection_id=connection.id))
        if endpoint_counts[endpoint] > 1:
            issues.append(ValidationIssue('duplicate-connection', 'The same ports are already connected.', connection_id=connection.id))
        if connection.source_node_id == connection.target_node_id:
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
        incoming[(target_node.id, target_port.id)] += 1
        if source_port.direction is not PortDirection.OUTPUT or target_port.direction is not PortDirection.INPUT:
            issues.append(ValidationIssue('unknown-port', 'Connections must run from an output to an input.', connection_id=connection.id))
        if source_port.data_type is not target_port.data_type:
            issues.append(ValidationIssue('type-mismatch', 'Connected ports require exactly the same data type.', connection_id=connection.id))
        if target_counts[(target_node.id, target_port.id)] > 1 and not target_port.variadic:
            issues.append(ValidationIssue('input-already-connected', 'The target input already has a connection.', port_id=target_port.id, connection_id=connection.id))

    for node in workflow.nodes:
        for port in node.ports:
            if port.direction is PortDirection.INPUT and port.required and incoming[(node.id, port.id)] == 0:
                issues.append(ValidationIssue('missing-required-input', f'Input {port.display_label} requires a connection.', node_id=node.id, port_id=port.id))

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
            if connection.source_node_id in order_index and connection.target_node_id in order_index and order_index[connection.source_node_id] >= order_index[connection.target_node_id]:
                issues.append(ValidationIssue('dependency-order', 'Dependencies must execute before consumers.', connection_id=connection.id))

    return tuple(issues)