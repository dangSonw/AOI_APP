from core.nodes.knn_runtime import classify_objects
from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse


NODE_ID = 'knn-object-classifier'
USE = NodeUse.DEBUG
INPUT_KEYS = ('image', 'detections')
OUTPUT_KEYS = ('classified-detections',)


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    return classify_objects(inputs, parameters)