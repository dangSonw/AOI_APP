from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse


NODE_ID = 'image-input'
USE = NodeUse.DEBUG
INPUT_KEYS = ()
OUTPUT_KEYS = ('image',)


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    if 'source-image' not in inputs:
        raise ValueError('Image input requires a source-image runtime resource.')
    return {'image': inputs['source-image']}
