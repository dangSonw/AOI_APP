from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse
from core.nodes.opencv_runtime import draw_detections


NODE_ID = 'draw-detections'
USE = NodeUse.DEBUG
INPUT_KEYS = ('image', 'detections')
OUTPUT_KEYS = ('annotated-image',)


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    return draw_detections(inputs, parameters)