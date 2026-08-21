from __future__ import annotations

import time
from dataclasses import dataclass
from collections.abc import Callable
from typing import Any

import numpy as np

from core.algorithms import DataType
from core.nodes import (
    NodeExecutionCancelled, NodeExecutionContext, NodeNotImplementedError,
    get_node_manifest_registry, get_node_runtime,
)

from .models import (
    ConnectionKind, PortChannel, RuntimeBindingMode, Workflow, WorkflowNode,
)
from .virtual_pins import INPUT_PIN_ID, OUTPUT_PIN_ID, normalize_virtual_pin_name


@dataclass(frozen=True, slots=True)
class WorkflowExecutionRecord:
    node_instance_id: str
    algorithm_id: str
    status: str
    parameters: dict[str, Any]
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    duration_ms: int | None
    error_code: str | None = None
    error_message: str | None = None
    activation_id: str | None = None
    activation_sequence: int | None = None
    visit_index: int = 1
    log_event: dict[str, str] | None = None


WorkflowExecutionObserver = Callable[[WorkflowExecutionRecord], None]


@dataclass(frozen=True, slots=True)
class WorkflowExecutionResult:
    records: tuple[WorkflowExecutionRecord, ...]
    final_image: np.ndarray | None
    decision: str | None
    score: float | None
    preview_images: dict[str, np.ndarray]


def _summary(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return {
            'kind': 'image', 'shape': list(value.shape), 'dtype': str(value.dtype),
            'minimum': float(value.min()) if value.size else None,
            'maximum': float(value.max()) if value.size else None,
        }
    if isinstance(value, list):
        return {'kind': 'list', 'count': len(value)}
    if isinstance(value, dict):
        return {str(key): _summary(item) for key, item in value.items()}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return {'kind': type(value).__name__}


def _token_node_inputs(
    workflow: Workflow,
    node: WorkflowNode,
    values: dict[tuple[str, str], Any],
    source_image: np.ndarray,
    virtual_pin_values: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], tuple[str, ...], dict[str, Any]]:
    node_inputs: dict[str, Any] = {}
    values_by_input_port: dict[str, Any] = {}
    missing: list[str] = []
    for port in node.ports:
        if port.channel is not PortChannel.DATA or port.direction.value != 'input':
            continue
        incoming = [
            connection for connection in workflow.connections
            if connection.kind is ConnectionKind.DATA
            and connection.target_node_id == node.id and connection.target_port_id == port.id
        ]
        received = [
            values[(connection.source_node_id, connection.source_port_id)]
            for connection in incoming
            if (connection.source_node_id, connection.source_port_id) in values
        ]
        runtime_key = port.runtime_key or port.template_key
        if port.variadic:
            if received:
                node_inputs.setdefault(runtime_key, []).extend(received)
                values_by_input_port[port.id] = tuple(received)
            elif port.required:
                missing.append(port.id)
        elif received:
            node_inputs[runtime_key] = received[0]
            values_by_input_port[port.id] = received[0]
        elif node.algorithm_id == OUTPUT_PIN_ID and virtual_pin_values is not None:
            name = normalize_virtual_pin_name(node)
            if name in virtual_pin_values:
                node_inputs[runtime_key] = virtual_pin_values[name]
                values_by_input_port[port.id] = virtual_pin_values[name]
            elif port.required:
                missing.append(port.id)
        elif port.required:
            missing.append(port.id)
    if node.algorithm_id == OUTPUT_PIN_ID:
        name = normalize_virtual_pin_name(node)
        if virtual_pin_values is not None and name in virtual_pin_values:
            node_inputs['value'] = virtual_pin_values[name]
        else:
            missing.append(node.id)
    if node.algorithm_id in {'image-input', 'camera-capture'}:
        node_inputs['source-image'] = source_image
    return node_inputs, tuple(missing), values_by_input_port


def _execute_token_workflow(
    workflow: Workflow,
    *,
    source_image: np.ndarray,
    context: NodeExecutionContext | None,
    observer: WorkflowExecutionObserver | None,
) -> WorkflowExecutionResult:
    nodes = {node.id: node for node in workflow.nodes}
    manifests = get_node_manifest_registry()
    values: dict[tuple[str, str], Any] = {}
    virtual_pin_values: dict[str, Any] = {}
    records: list[WorkflowExecutionRecord] = []
    visits: dict[str, int] = {}
    traversals: dict[str, int] = {}
    final_image: np.ndarray | None = source_image
    has_explicit_preview = False
    decision: str | None = None
    score: float | None = None
    preview_images: dict[str, np.ndarray] = {}
    next_activation = 0
    executed_steps = 0

    def publish(record: WorkflowExecutionRecord) -> None:
        if observer is not None:
            observer(record)

    incoming_control = {
        connection.target_node_id
        for connection in workflow.connections if connection.kind is ConnectionKind.CONTROL
    }
    queue: list[tuple[str, str]] = []
    merge_arrivals: dict[str, set[str]] = {}

    def enqueue(node_id: str, incoming_connection_id: str | None = None) -> None:
        nonlocal next_activation
        target = nodes[node_id]
        if target.algorithm_id == 'merge' and target.parameters.get('policy') == 'all' and incoming_connection_id:
            arrivals = merge_arrivals.setdefault(node_id, set())
            arrivals.add(incoming_connection_id)
            required = {
                connection.id for connection in workflow.connections
                if connection.kind is ConnectionKind.CONTROL and connection.target_node_id == node_id
            }
            if not required <= arrivals:
                return
            arrivals.clear()
        next_activation += 1
        queue.append((node_id, f'activation-{next_activation:08d}'))

    def emit_control(node: WorkflowNode, emitted_keys: set[str]) -> tuple[set[str], set[str]]:
        matched: set[str] = set()
        traversed: set[str] = set()
        for connection in workflow.connections:
            source_port = next((port for port in node.ports if port.id == connection.source_port_id), None)
            if (
                connection.kind is not ConnectionKind.CONTROL
                or connection.source_node_id != node.id
                or source_port is None
                or source_port.template_key not in emitted_keys
            ):
                continue
            matched.add(source_port.template_key)
            count = traversals.get(connection.id, 0)
            if connection.max_traversals is not None and count >= connection.max_traversals:
                continue
            traversals[connection.id] = count + 1
            traversed.add(source_port.template_key)
            enqueue(connection.target_node_id, connection.id)
        return matched, traversed

    for node in workflow.nodes:
        if node.id not in incoming_control:
            enqueue(node.id)

    while queue:
        runnable_index: int | None = None
        blocked: list[tuple[str, tuple[str, ...]]] = []
        for index, (node_id, _) in enumerate(queue):
            _, missing_ports, _ = _token_node_inputs(
                workflow, nodes[node_id], values, source_image, virtual_pin_values,
            )
            if not missing_ports:
                runnable_index = index
                break
            blocked.append((node_id, missing_ports))
        if runnable_index is None:
            blocked_message = '; '.join(
                f'{node_id}: {", ".join(port_ids)}' for node_id, port_ids in blocked
            )
            node_id, activation_id = queue[0]
            node = nodes[node_id]
            record = WorkflowExecutionRecord(
                node_instance_id=node.id, algorithm_id=node.algorithm_id, status='faulted',
                parameters=dict(node.parameters), inputs={}, outputs={}, duration_ms=0,
                error_code='control-data-deadlock',
                error_message=f'Control activations cannot resolve required data ports: {blocked_message}'[:500],
                activation_id=activation_id, activation_sequence=len(records) + 1,
                visit_index=visits.get(node.id, 0) + 1,
            )
            records.append(record)
            publish(record)
            queue.pop(0)
            continue

        node_id, activation_id = queue.pop(runnable_index)
        node = nodes[node_id]
        runtime = get_node_runtime(node.algorithm_id)
        manifest = manifests.get(node.algorithm_id)
        node_inputs, _, input_port_values = _token_node_inputs(
            workflow, node, values, source_image, virtual_pin_values,
        )
        if node.algorithm_id == 'counter-limit':
            node_inputs['__visit_index__'] = visits.get(node.id, 0) + 1
        started = time.monotonic()
        executed_steps += 1
        visit_index = visits.get(node.id, 0) + 1
        visits[node.id] = visit_index
        publish(WorkflowExecutionRecord(
            node_instance_id=node.id, algorithm_id=node.algorithm_id, status='running',
            parameters=dict(node.parameters), inputs=_summary(node_inputs), outputs={}, duration_ms=None,
            activation_id=activation_id, activation_sequence=len(records) + 1, visit_index=visit_index,
        ))
        try:
            if executed_steps > 10_000:
                raise ValueError('Workflow exceeded the bounded execution limit of 10000 node steps.')
            if runtime is None or manifest is None:
                raise ValueError(f'Node runtime {node.algorithm_id} is not registered.')
            outputs = dict(runtime.invoke(node_inputs, node.parameters, context=context))
            control_branch = str(outputs.pop('__control__', 'success'))
            log_event = outputs.pop('__log__', None)
            if node.algorithm_id == INPUT_PIN_ID:
                virtual_pin_values[normalize_virtual_pin_name(node)] = node_inputs['value']
            output_ports = [
                port for port in node.ports
                if port.channel is PortChannel.DATA and port.direction.value == 'output'
            ]
            missing_outputs = set(runtime.output_keys) - set(outputs)
            if missing_outputs:
                raise ValueError(f'Node {node.algorithm_id} omitted outputs: {sorted(missing_outputs)}.')
            for key, value in outputs.items():
                bound_ports = [
                    port for port in output_ports
                    if port.runtime_binding is RuntimeBindingMode.SLOT
                    and (port.runtime_key or port.template_key) == key
                ]
                for output_port in bound_ports:
                    values[(node.id, output_port.id)] = value
                output_port = bound_ports[0] if bound_ports else None
                is_viewable_output = (
                    output_port is not None
                    and output_port.data_type in {DataType.IMAGE, DataType.MASK, DataType.ANOMALY_MAP, DataType.GENERIC}
                    and isinstance(value, np.ndarray) and value.ndim in {2, 3}
                )
                if node.algorithm_id == 'image-output' and key == 'preview-image' and is_viewable_output:
                    final_image = value
                    has_explicit_preview = True
                    preview_images[node.id] = value
                elif any(capability in manifest.capabilities for capability in ('image-preview', '3d-preview')) and is_viewable_output:
                    preview_images[node.id] = value
                elif is_viewable_output and not has_explicit_preview:
                    final_image = value
                if key in {'decision', 'result-decision'}:
                    decision = str(value)
                if key in {'score', 'normalized-score'}:
                    score = float(value)
            for output_port in output_ports:
                if output_port.runtime_binding is RuntimeBindingMode.PASSTHROUGH:
                    passthrough = input_port_values.get(output_port.passthrough_input_port_id or '')
                    if passthrough is not None:
                        values[(node.id, output_port.id)] = passthrough
            record = WorkflowExecutionRecord(
                node_instance_id=node.id, algorithm_id=node.algorithm_id,
                status='faulted' if control_branch == 'failure' else 'completed',
                parameters=dict(node.parameters), inputs=_summary(node_inputs), outputs=_summary(outputs),
                duration_ms=max(0, int((time.monotonic() - started) * 1000)),
                activation_id=activation_id, activation_sequence=len(records) + 1,
                visit_index=visit_index, log_event=log_event,
                error_code='node-reported-failure' if control_branch == 'failure' else None,
                error_message='Node emitted its failure control output.' if control_branch == 'failure' else None,
            )
            records.append(record)
            publish(record)

            if control_branch == 'failure':
                emit_control(node, {'failure'})
            else:
                emit_control(node, {'success'})
            if control_branch not in {'success', 'failure'}:
                matched, traversed = emit_control(node, {control_branch})
                if control_branch in matched and control_branch not in traversed:
                    emit_control(node, {'completed'})
        except NodeExecutionCancelled as error:
            record = WorkflowExecutionRecord(
                node_instance_id=node.id, algorithm_id=node.algorithm_id, status='cancelled',
                parameters=dict(node.parameters), inputs=_summary(node_inputs), outputs={},
                duration_ms=max(0, int((time.monotonic() - started) * 1000)),
                error_code='node-execution-cancelled', error_message=str(error),
                activation_id=activation_id, activation_sequence=len(records) + 1,
                visit_index=visit_index,
            )
            records.append(record)
            publish(record)
            break
        except NodeNotImplementedError as error:
            record = WorkflowExecutionRecord(
                node_instance_id=node.id, algorithm_id=node.algorithm_id, status='faulted',
                parameters=dict(node.parameters), inputs=_summary(node_inputs), outputs={},
                duration_ms=max(0, int((time.monotonic() - started) * 1000)),
                error_code='node-not-implemented', error_message=str(error),
                activation_id=activation_id, activation_sequence=len(records) + 1,
                visit_index=visit_index,
            )
            records.append(record)
            publish(record)
            emit_control(node, {'failure'})
            continue
        except Exception as error:
            record = WorkflowExecutionRecord(
                node_instance_id=node.id, algorithm_id=node.algorithm_id, status='faulted',
                parameters=dict(node.parameters), inputs=_summary(node_inputs), outputs={},
                duration_ms=max(0, int((time.monotonic() - started) * 1000)),
                error_code='node-execution-error', error_message=str(error)[:500],
                activation_id=activation_id, activation_sequence=len(records) + 1,
                visit_index=visit_index,
            )
            records.append(record)
            publish(record)
            if executed_steps > 10_000:
                break
            emit_control(node, {'failure'})
            continue
    return WorkflowExecutionResult(tuple(records), final_image, decision, score, dict(preview_images))


def execute_workflow(
    workflow: Workflow,
    *,
    source_image: np.ndarray,
    context: NodeExecutionContext | None = None,
    observer: WorkflowExecutionObserver | None = None,
) -> WorkflowExecutionResult:
    return _execute_token_workflow(
        workflow, source_image=source_image, context=context, observer=observer,
    )