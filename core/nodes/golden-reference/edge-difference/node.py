from core.nodes.golden_runtime import execute_golden_with_context, require_execution_context
from core.nodes.models import NodeExecutionContext, NodeInputs, NodeOutputs, NodeParameters, NodeUse


NODE_ID = 'edge-difference'
USE = NodeUse.DEBUG
INPUT_KEYS = ('image',)
OUTPUT_KEYS = ('anomaly-map', 'score')


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    return require_execution_context(NODE_ID)


def execute_with_context(inputs: NodeInputs, parameters: NodeParameters, context: NodeExecutionContext) -> NodeOutputs:
    return execute_golden_with_context(NODE_ID, inputs, parameters, context)
