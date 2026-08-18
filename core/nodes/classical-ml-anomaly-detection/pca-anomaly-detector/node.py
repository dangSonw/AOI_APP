from core.nodes.classical_ml_runtime import pca_anomaly
from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse

NODE_ID = 'pca-anomaly-detector'
USE = NodeUse.DEBUG
INPUT_KEYS = ('image',)
OUTPUT_KEYS = ('anomaly-map', 'score')


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    return pca_anomaly(inputs, parameters)