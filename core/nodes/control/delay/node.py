import time

from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse


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