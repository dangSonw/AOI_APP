from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse


NODE_ID = 'input-pin'
USE = NodeUse.DEBUG
INPUT_KEYS = ('value',)
OUTPUT_KEYS: tuple[str, ...] = ()


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    return {}