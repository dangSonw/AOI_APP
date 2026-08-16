from collections.abc import Mapping

from .models import NodeInputs, NodeOutputs, NodeParameters


def _boolean(value: object, *, name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f'{name} must be a boolean value.')
    return value


def _values(inputs: NodeInputs) -> list[bool]:
    values = inputs.get('values')
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError('Logic values must contain at least one boolean value.')
    return [_boolean(value, name='Each logic input') for value in values]


def execute_logic_node(node_id: str, inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    if node_id == 'logic-not':
        result = not _boolean(inputs.get('value'), name='Logic input')
        return {'result': result, '__control__': 'true' if result else 'false'}
    if node_id in {'logic-and', 'logic-or', 'logic-xor'}:
        values = _values(inputs)
        if node_id == 'logic-and':
            result = all(values)
        elif node_id == 'logic-or':
            result = any(values)
        else:
            result = sum(values) % 2 == 1
        return {'result': result, '__control__': 'true' if result else 'false'}
    if node_id == 'switch-case':
        cases = parameters.get('cases')
        if not isinstance(cases, list):
            raise ValueError('Switch cases must be a JSON list.')
        value = inputs.get('value')
        for case in cases:
            if not isinstance(case, Mapping) or not isinstance(case.get('branch'), str) or not case['branch'].strip():
                raise ValueError('Each switch case requires a non-empty branch and a value.')
            if value == case.get('value'):
                return {'__control__': case['branch']}
        return {'__control__': 'default'}
    if node_id == 'merge':
        if parameters.get('policy') not in {'any', 'all'}:
            raise ValueError('Merge policy must be any or all.')
        return {'__control__': 'merged'}
    if node_id == 'counter-limit':
        limit = int(parameters.get('limit', 0))
        count = int(inputs.get('__visit_index__', 1))
        if limit < 1:
            raise ValueError('Counter limit must be at least one.')
        return {
            'count': count,
            '__control__': 'under-limit' if count < limit else 'limit-reached',
        }
    raise ValueError(f'Logic node {node_id} is not implemented.')