from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse
from core.nodes.opencv_extended_runtime import execute_opencv_extended_node

NODE_ID = 'convex-hull'
USE = NodeUse.DEBUG
INPUT_KEYS = ('contours',)
OUTPUT_KEYS = ('hulls',)

def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    return execute_opencv_extended_node(NODE_ID, inputs, parameters)