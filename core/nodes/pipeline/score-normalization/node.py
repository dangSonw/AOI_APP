from core.nodes.errors import NodeNotImplementedError
from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse


NODE_ID = 'score-normalization'
USE = NodeUse.TEST
INPUT_KEYS = ('score',)
OUTPUT_KEYS = ('normalized-score',)


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    raise NodeNotImplementedError(NODE_ID)
