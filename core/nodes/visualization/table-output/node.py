from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse
from core.visualization.contracts import TablePayload

NODE_ID = 'table-output'
USE = NodeUse.RELEASE
INPUT_KEYS = ('payload',)
OUTPUT_KEYS = ('validated-payload',)

def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    del parameters
    return {'validated-payload': TablePayload.from_mapping(inputs.get('payload')).to_mapping()}