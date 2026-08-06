from core.nodes.errors import NodeNotImplementedError
from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse


NODE_ID = 'homography-registration'
USE = NodeUse.TEST
INPUT_KEYS = ('image', 'reference')
OUTPUT_KEYS = ('registered-image', 'transform')


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    raise NodeNotImplementedError(NODE_ID)
