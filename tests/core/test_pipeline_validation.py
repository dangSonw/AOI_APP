from dataclasses import replace

from core.algorithms import DataType
from core.pipeline import validate_workflow

from workflow_fixtures import branched_workflow, connection


def issue_codes(workflow) -> set[str]:
    return {issue.code for issue in validate_workflow(workflow)}


def test_valid_branched_graph_passes() -> None:
    assert validate_workflow(branched_workflow()) == ()


def test_type_mismatch_and_unknown_ports_have_stable_codes() -> None:
    workflow = branched_workflow()
    first = workflow.connections[0]
    source = workflow.nodes[0]
    bad_source_port = replace(source.ports[0], data_type=DataType.SCORE)
    bad_source = replace(source, ports=(bad_source_port, *source.ports[1:]))
    type_mismatch = replace(workflow, nodes=(bad_source, *workflow.nodes[1:]))
    unknown_port = replace(
        workflow,
        connections=(replace(first, target_port_id='20000000-0000-4000-8000-000000000099'), *workflow.connections[1:]),
    )

    assert 'type-mismatch' in issue_codes(type_mismatch)
    assert 'unknown-port' in issue_codes(unknown_port)


def test_duplicate_self_loop_and_occupied_input_are_rejected() -> None:
    workflow = branched_workflow()
    source, left, right, _ = workflow.nodes
    duplicate = replace(workflow, connections=(*workflow.connections, workflow.connections[0]))
    self_loop = replace(
        workflow,
        connections=(*workflow.connections, connection(6, left, 'score', left, 'score')),
    )
    occupied = replace(
        workflow,
        connections=(*workflow.connections, connection(7, source, 'image', right, 'image')),
    )

    assert {'duplicate-id', 'duplicate-connection'} & issue_codes(duplicate)
    assert 'self-loop' in issue_codes(self_loop)
    assert 'input-already-connected' in issue_codes(occupied)


def test_missing_required_input_and_cycle_are_rejected() -> None:
    workflow = branched_workflow()
    _, left, _, merge = workflow.nodes
    missing = replace(workflow, connections=workflow.connections[1:])
    cyclic = replace(
        workflow,
        connections=(*workflow.connections, connection(8, merge, 'decision', left, 'score')),
    )

    assert 'missing-required-input' in issue_codes(missing)
    assert 'cycle' in issue_codes(cyclic)


def test_invalid_parameters_and_execution_order_are_rejected() -> None:
    workflow = branched_workflow()
    left = replace(workflow.nodes[1], parameters={'memoryBankSize': 'not-a-number'})
    bad_parameter = replace(workflow, nodes=(workflow.nodes[0], left, *workflow.nodes[2:]))
    missing_node = replace(workflow, execution_order=workflow.execution_order[:-1])
    dependency_after_consumer = replace(
        workflow,
        execution_order=(workflow.nodes[1].id, workflow.nodes[0].id, workflow.nodes[2].id, workflow.nodes[3].id),
    )

    assert 'invalid-parameter' in issue_codes(bad_parameter)
    assert 'execution-order-mismatch' in issue_codes(missing_node)
    assert 'dependency-order' in issue_codes(dependency_after_consumer)


def test_reference_parameters_accept_bounded_json_values() -> None:
    from core.algorithms import ParameterKind
    from core.pipeline.validation import _parameter_is_valid

    assert _parameter_is_valid(ParameterKind.REFERENCE, [{'label': 'object', 'color': [255, 255, 255]}])
    assert not _parameter_is_valid(ParameterKind.REFERENCE, object())


def test_model_references_require_portable_alias_or_immutable_version_shape() -> None:
    from core.algorithms import ParameterKind
    from core.pipeline.validation import _parameter_is_valid

    assert _parameter_is_valid(ParameterKind.MODEL_REFERENCE, {'modelName': 'pcb-defect', 'alias': 'champion'})
    assert _parameter_is_valid(ParameterKind.MODEL_REFERENCE, {
        'modelName': 'pcb-defect', 'modelVersion': 2, 'artifactSha256': 'a' * 64,
    })
    assert not _parameter_is_valid(ParameterKind.MODEL_REFERENCE, {'modelName': 'pcb-defect', 'alias': 'draft'})
    assert not _parameter_is_valid(ParameterKind.MODEL_REFERENCE, {'modelName': 'pcb-defect', 'artifactSha256': 'a' * 64})