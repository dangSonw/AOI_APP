from core.nodes.errors import NodeNotImplementedError
from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse


NODE_ID = 'component-relation-graph'
USE = NodeUse.TEST
INPUT_KEYS = ('detections',)
OUTPUT_KEYS = ('score', 'decision')


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    raise NodeNotImplementedError(NODE_ID)
