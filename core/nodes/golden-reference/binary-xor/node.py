from core.nodes.errors import NodeNotImplementedError
from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse


NODE_ID = 'binary-xor'
USE = NodeUse.TEST
INPUT_KEYS = ('mask', 'reference')
OUTPUT_KEYS = ('difference-mask', 'score')


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    raise NodeNotImplementedError(NODE_ID)
