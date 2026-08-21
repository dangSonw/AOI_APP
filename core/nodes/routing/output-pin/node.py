from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse


NODE_ID = 'output-pin'
USE = NodeUse.DEBUG
INPUT_KEYS: tuple[str, ...] = ()
OUTPUT_KEYS = ('value',)


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    return {'value': inputs['value']}