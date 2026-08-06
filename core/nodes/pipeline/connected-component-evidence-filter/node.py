from core.nodes.errors import NodeNotImplementedError
from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse


NODE_ID = 'connected-component-evidence-filter'
USE = NodeUse.TEST
INPUT_KEYS = ('anomaly-map',)
OUTPUT_KEYS = ('detections', 'score')


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    raise NodeNotImplementedError(NODE_ID)
