from core.nodes.logic_runtime import execute_logic_node
from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse

NODE_ID = 'logic-not'
USE = NodeUse.DEBUG
INPUT_KEYS = ('value',)
OUTPUT_KEYS = ('result',)

def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    return execute_logic_node(NODE_ID, inputs, parameters)