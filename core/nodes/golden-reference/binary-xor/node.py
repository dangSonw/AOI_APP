from core.nodes.golden_runtime import execute_binary_xor
from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse


NODE_ID = 'binary-xor'
USE = NodeUse.DEBUG
INPUT_KEYS = ('mask', 'reference')
OUTPUT_KEYS = ('difference-mask', 'score')


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    return execute_binary_xor(inputs)
