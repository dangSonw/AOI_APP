from core.nodes.classical_ml_runtime import logistic_classify
from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse

NODE_ID = 'logistic-object-classifier'
USE = NodeUse.DEBUG
INPUT_KEYS = ('image', 'detections')
OUTPUT_KEYS = ('classified-detections',)


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    return logistic_classify(inputs, parameters)