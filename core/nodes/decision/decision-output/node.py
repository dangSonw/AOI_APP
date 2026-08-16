from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse


NODE_ID = 'decision-output'
USE = NodeUse.DEBUG
INPUT_KEYS = ('decision',)
OUTPUT_KEYS = ('result-decision',)


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    decision = str(inputs['decision'])
    if decision not in {'PASS', 'FAIL', 'REVIEW'}:
        raise ValueError('Decision output received an unsupported decision.')
    return {'result-decision': decision}
