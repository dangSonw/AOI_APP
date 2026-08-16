from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse


NODE_ID = 'bounded-repeat'
USE = NodeUse.DEBUG
INPUT_KEYS = ('image',)
OUTPUT_KEYS = ('images',)


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    iterations = int(parameters['iterations'])
    if iterations < 1 or iterations > 100:
        raise ValueError('Bounded repeat iterations must be between 1 and 100.')
    return {'images': [inputs['image']] * iterations}