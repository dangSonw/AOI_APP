from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse
from core.nodes.opencv_extended_runtime import execute_opencv_extended_node

NODE_ID = 'image-arithmetic'
USE = NodeUse.DEBUG
INPUT_KEYS = ('image', 'operand')
OUTPUT_KEYS = ('processed-image',)

def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    return execute_opencv_extended_node(NODE_ID, inputs, parameters)