from core.nodes.classical_ml_runtime import kmeans_segment
from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse

NODE_ID = 'kmeans-image-segmentation'
USE = NodeUse.DEBUG
INPUT_KEYS = ('image',)
OUTPUT_KEYS = ('mask', 'contours')


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    return kmeans_segment(inputs, parameters)