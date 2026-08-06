from core.nodes.errors import NodeNotImplementedError
from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse


NODE_ID = 'edge-difference'
USE = NodeUse.TEST
INPUT_KEYS = ('image',)
OUTPUT_KEYS = ('anomaly-map', 'score')


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    raise NodeNotImplementedError(NODE_ID)
