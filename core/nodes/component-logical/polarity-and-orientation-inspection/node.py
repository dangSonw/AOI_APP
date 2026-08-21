from core.nodes.errors import NodeNotImplementedError
from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse


NODE_ID = 'polarity-and-orientation-inspection'
USE = NodeUse.TEST
INPUT_KEYS = ('image', 'components')
OUTPUT_KEYS = ('detections', 'score')


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    raise NodeNotImplementedError(NODE_ID)
