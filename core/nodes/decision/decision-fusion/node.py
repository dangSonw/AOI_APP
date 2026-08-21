from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse


NODE_ID = 'decision-fusion'
USE = NodeUse.DEBUG
INPUT_KEYS = ('scores',)
OUTPUT_KEYS = ('decision',)


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    scores = inputs.get('scores', [])
    if not isinstance(scores, list) or not scores:
        raise ValueError('Decision fusion requires at least one score.')
    maximum_score = max(float(score) for score in scores)
    threshold = float(parameters['reviewThreshold'])
    return {'decision': 'FAIL' if maximum_score >= threshold else 'PASS'}
