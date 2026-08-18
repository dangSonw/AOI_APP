from core.nodes.knn_runtime import segment_image
from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse


NODE_ID = 'knn-image-segmentation'
USE = NodeUse.DEBUG
INPUT_KEYS = ('image',)
OUTPUT_KEYS = ('mask', 'contours')


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    return segment_image(inputs, parameters)