import time

from core.nodes.models import NodeExecutionContext, NodeInputs, NodeOutputs, NodeParameters, NodeUse


NODE_ID = 'delay'
USE = NodeUse.DEBUG
INPUT_KEYS = ('image',)
OUTPUT_KEYS = ('delayed-image',)


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    milliseconds = int(parameters['milliseconds'])
    if milliseconds < 0 or milliseconds > 10_000:
        raise ValueError('Delay must be between 0 and 10000 milliseconds.')
    time.sleep(milliseconds / 1000)
    return {'delayed-image': inputs['image']}


def execute_with_context(
    inputs: NodeInputs,
    parameters: NodeParameters,
    context: NodeExecutionContext,
) -> NodeOutputs:
    milliseconds = int(parameters['milliseconds'])
    if milliseconds < 0 or milliseconds > 10_000:
        raise ValueError('Delay must be between 0 and 10000 milliseconds.')
    remaining_seconds = milliseconds / 1000
    while remaining_seconds > 0:
        context.checkpoint()
        interval = min(remaining_seconds, 0.05)
        time.sleep(interval)
        remaining_seconds -= interval
    context.checkpoint()
    return {'delayed-image': inputs['image']}