from __future__ import annotations

from collections.abc import Mapping
from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse

NODE_ID = 'logic-xor'
USE = NodeUse.DEBUG
INPUT_KEYS = ('values',)
OUTPUT_KEYS = ('result',)

def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    if NODE_ID == 'logic-not':
        result = not _boolean(inputs.get('value'), name='Logic input')
        return {'result': result, '__control__': 'true' if result else 'false'}
    if NODE_ID in {'logic-and', 'logic-or', 'logic-xor'}:
        values = _values(inputs)
        if NODE_ID == 'logic-and':
            result = all(values)
        elif NODE_ID == 'logic-or':
            result = any(values)
        else:
            result = sum(values) % 2 == 1
        return {'result': result, '__control__': 'true' if result else 'false'}
    if NODE_ID == 'switch-case':
        cases = parameters.get('cases')
        if not isinstance(cases, list):
            raise ValueError('Switch cases must be a JSON list.')
        value = inputs.get('value')
        for case in cases:
            if not isinstance(case, Mapping) or not isinstance(case.get('branch'), str) or (not case['branch'].strip()):
                raise ValueError('Each switch case requires a non-empty branch and a value.')
            if value == case.get('value'):
                return {'__control__': case['branch']}
        return {'__control__': 'default'}
    if NODE_ID == 'merge':
        if parameters.get('policy') not in {'any', 'all'}:
            raise ValueError('Merge policy must be any or all.')
        return {'__control__': 'merged'}
    if NODE_ID == 'counter-limit':
        limit = int(parameters.get('limit', 0))
        count = int(inputs.get('__visit_index__', 1))
        if limit < 1:
            raise ValueError('Counter limit must be at least one.')
        return {'count': count, '__control__': 'under-limit' if count < limit else 'limit-reached'}
    raise ValueError(f'Logic node {NODE_ID} is not implemented.')

def _boolean(value: object, *, name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f'{name} must be a boolean value.')
    return value

def _values(inputs: NodeInputs) -> list[bool]:
    values = inputs.get('values')
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError('Logic values must contain at least one boolean value.')
    return [_boolean(value, name='Each logic input') for value in values]
