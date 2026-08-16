from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse
from core.nodes.opencv_extended_runtime import execute_opencv_extended_node

NODE_ID = 'estimate-perspective-transform'
USE = NodeUse.DEBUG
INPUT_KEYS = ('source-points', 'destination-points')
OUTPUT_KEYS = ('transform',)

def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    return execute_opencv_extended_node(NODE_ID, inputs, parameters)