import pytest

from core.nodes import get_node_runtime


@pytest.mark.parametrize(
    ('node_id', 'values', 'expected'),
    [
        ('logic-and', [True, True], True),
        ('logic-and', [True, False], False),
        ('logic-or', [False, True], True),
        ('logic-or', [False, False], False),
        ('logic-xor', [True, False, True], False),
        ('logic-xor', [True, False, False], True),
    ],
)
def test_variadic_logic_nodes_return_boolean_and_matching_control_branch(
    node_id: str,
    values: list[bool],
    expected: bool,
) -> None:
    runtime = get_node_runtime(node_id)

    assert runtime is not None
    outputs = runtime.execute({'values': values}, {})

    assert outputs == {'result': expected, '__control__': 'true' if expected else 'false'}


def test_logic_not_inverts_boolean_and_rejects_non_boolean_input() -> None:
    runtime = get_node_runtime('logic-not')

    assert runtime is not None
    assert runtime.execute({'value': True}, {}) == {'result': False, '__control__': 'false'}
    with pytest.raises(ValueError, match='boolean'):
        runtime.execute({'value': 1}, {})


def test_switch_case_uses_first_matching_case_then_default() -> None:
    runtime = get_node_runtime('switch-case')
    parameters = {
        'cases': [
            {'branch': 'pass', 'value': 'PASS'},
            {'branch': 'reject', 'value': 'FAIL'},
        ],
    }

    assert runtime is not None
    assert runtime.execute({'value': 'PASS'}, parameters) == {'__control__': 'pass'}
    assert runtime.execute({'value': 'UNKNOWN'}, parameters) == {'__control__': 'default'}


def test_merge_declares_scheduler_policy_without_process_global_state() -> None:
    runtime = get_node_runtime('merge')

    assert runtime is not None
    assert runtime.execute({}, {'policy': 'any'}) == {'__control__': 'merged'}
    assert runtime.execute({}, {'policy': 'all'}) == {'__control__': 'merged'}
    with pytest.raises(ValueError, match='policy'):
        runtime.execute({}, {'policy': 'invalid'})


def test_counter_limit_routes_using_run_scoped_visit_index() -> None:
    runtime = get_node_runtime('counter-limit')

    assert runtime is not None
    assert runtime.execute({'__visit_index__': 1}, {'limit': 2}) == {
        'count': 1, '__control__': 'under-limit',
    }
    assert runtime.execute({'__visit_index__': 2}, {'limit': 2}) == {
        'count': 2, '__control__': 'limit-reached',
    }