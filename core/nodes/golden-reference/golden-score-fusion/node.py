from core.nodes.golden_runtime import execute_score_fusion
from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse


NODE_ID = 'golden-score-fusion'
USE = NodeUse.DEBUG
INPUT_KEYS = ('scores',)
OUTPUT_KEYS = ('score',)


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    return execute_score_fusion(inputs, parameters)
