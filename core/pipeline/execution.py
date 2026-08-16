from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import numpy as np

from core.algorithms import DataType
from core.nodes import NodeNotImplementedError, get_node_manifest_registry, get_node_runtime

from .models import Workflow


@dataclass(frozen=True, slots=True)
class WorkflowExecutionRecord:
    node_instance_id: str
    algorithm_id: str
    status: str
    parameters: dict[str, Any]
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    duration_ms: int
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class WorkflowExecutionResult:
    records: tuple[WorkflowExecutionRecord, ...]
    final_image: np.ndarray | None
    decision: str | None
    score: float | None


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


def execute_workflow(workflow: Workflow, *, source_image: np.ndarray) -> WorkflowExecutionResult:
    nodes = {node.id: node for node in workflow.nodes}
    manifests = get_node_manifest_registry()
    values: dict[tuple[str, str], Any] = {}
    records: list[WorkflowExecutionRecord] = []
    final_image: np.ndarray | None = source_image
    has_explicit_preview = False
    decision: str | None = None
    score: float | None = None

    for node_id in workflow.execution_order:
        node = nodes[node_id]
        runtime = get_node_runtime(node.algorithm_id)
        manifest = manifests.get(node.algorithm_id)
        started = time.monotonic()
        node_inputs: dict[str, Any] = {}
        for port in node.ports:
            if port.direction.value != 'input':
                continue
            incoming = [
                connection for connection in workflow.connections
                if connection.target_node_id == node.id and connection.target_port_id == port.id
            ]
            received = [values[(connection.source_node_id, connection.source_port_id)] for connection in incoming]
            if port.variadic:
                node_inputs.setdefault(port.template_key, []).extend(received)
            elif received:
                node_inputs[port.template_key] = received[0]
        if node.algorithm_id in {'image-input', 'camera-capture'}:
            node_inputs['source-image'] = source_image

        try:
            if runtime is None or manifest is None:
                raise ValueError(f'Node runtime {node.algorithm_id} is not registered.')
            outputs = dict(runtime.execute(node_inputs, node.parameters))
            output_ports = {port.template_key: port for port in node.ports if port.direction.value == 'output'}
            missing = set(runtime.output_keys) - set(outputs)
            if missing:
                raise ValueError(f'Node {node.algorithm_id} omitted outputs: {sorted(missing)}.')
            for key, value in outputs.items():
                output_port = output_ports.get(key)
                if output_port is not None:
                    values[(node.id, output_port.id)] = value
                is_viewable_output = (
                    output_port is not None
                    and output_port.data_type in {DataType.IMAGE, DataType.MASK, DataType.ANOMALY_MAP}
                    and isinstance(value, np.ndarray)
                    and value.ndim in {2, 3}
                )
                if node.algorithm_id == 'image-output' and key == 'preview-image' and is_viewable_output:
                    final_image = value
                    has_explicit_preview = True
                elif is_viewable_output and not has_explicit_preview:
                    final_image = value
                if key in {'decision', 'result-decision'}:
                    decision = str(value)
                if key in {'score', 'normalized-score'}:
                    score = float(value)
            records.append(WorkflowExecutionRecord(
                node_instance_id=node.id, algorithm_id=node.algorithm_id, status='completed',
                parameters=dict(node.parameters), inputs=_summary(node_inputs), outputs=_summary(outputs),
                duration_ms=max(0, int((time.monotonic() - started) * 1000)),
            ))
        except NodeNotImplementedError as error:
            records.append(WorkflowExecutionRecord(
                node_instance_id=node.id, algorithm_id=node.algorithm_id, status='faulted',
                parameters=dict(node.parameters), inputs=_summary(node_inputs), outputs={},
                duration_ms=max(0, int((time.monotonic() - started) * 1000)),
                error_code='node-not-implemented', error_message=str(error),
            ))
            break
        except Exception as error:
            records.append(WorkflowExecutionRecord(
                node_instance_id=node.id, algorithm_id=node.algorithm_id, status='faulted',
                parameters=dict(node.parameters), inputs=_summary(node_inputs), outputs={},
                duration_ms=max(0, int((time.monotonic() - started) * 1000)),
                error_code='node-execution-error', error_message=str(error)[:500],
            ))
            break
    return WorkflowExecutionResult(tuple(records), final_image, decision, score)