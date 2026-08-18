from core.nodes.classical_ml_runtime import nearest_centroid_classify
from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse

NODE_ID = 'nearest-centroid-object-classifier'
USE = NodeUse.DEBUG
INPUT_KEYS = ('image', 'detections')
OUTPUT_KEYS = ('classified-detections',)


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    return nearest_centroid_classify(inputs, parameters)