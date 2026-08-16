from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse
from core.nodes.opencv_runtime import mask_coverage_score


NODE_ID = 'mask-coverage-score'
USE = NodeUse.DEBUG
INPUT_KEYS = ('mask',)
OUTPUT_KEYS = ('score',)


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    return mask_coverage_score(inputs, parameters)