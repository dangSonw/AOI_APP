from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse


NODE_ID = 'camera-capture'
USE = NodeUse.DEBUG
INPUT_KEYS = ()
OUTPUT_KEYS = ('image',)


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    if 'source-image' not in inputs:
        raise ValueError('Camera capture requires an image captured by the adapter boundary.')
    return {'image': inputs['source-image']}
