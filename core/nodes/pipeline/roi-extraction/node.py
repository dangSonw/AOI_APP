from core.nodes.errors import NodeNotImplementedError
from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse


NODE_ID = 'roi-extraction'
USE = NodeUse.TEST
INPUT_KEYS = ('image', 'regions')
OUTPUT_KEYS = ('images',)


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    raise NodeNotImplementedError(NODE_ID)
