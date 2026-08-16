from core.nodes.logic_runtime import execute_logic_node
from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse

NODE_ID = 'merge'
USE = NodeUse.DEBUG
INPUT_KEYS: tuple[str, ...] = ()
OUTPUT_KEYS: tuple[str, ...] = ()

def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    return execute_logic_node(NODE_ID, inputs, parameters)