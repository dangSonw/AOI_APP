from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse
from core.nodes.opencv_runtime import execute_opencv_node


NODE_ID = 'feature-detection-and-matching'
USE = NodeUse.DEBUG
INPUT_KEYS = ('image', 'reference')
OUTPUT_KEYS = ('keypoints', 'transform')


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    return execute_opencv_node(NODE_ID, inputs, parameters)
