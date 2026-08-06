from core.nodes.errors import NodeNotImplementedError
from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse


NODE_ID = 'scharr-gradient'
USE = NodeUse.TEST
INPUT_KEYS = ('image',)
OUTPUT_KEYS = ('processed-image',)


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    raise NodeNotImplementedError(NODE_ID)
