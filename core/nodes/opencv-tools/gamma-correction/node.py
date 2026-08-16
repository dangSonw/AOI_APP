from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse
from core.nodes.opencv_runtime import execute_opencv_node


NODE_ID = 'gamma-correction'
USE = NodeUse.DEBUG
INPUT_KEYS = ('image',)
OUTPUT_KEYS = ('processed-image',)


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    return execute_opencv_node(NODE_ID, inputs, parameters)