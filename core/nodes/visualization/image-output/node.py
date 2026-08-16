from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse


NODE_ID = 'image-output'
USE = NodeUse.DEBUG
INPUT_KEYS = ('image',)
OUTPUT_KEYS = ('preview-image',)


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    if 'image' not in inputs:
        raise ValueError('Image output requires an image input.')
    return {'preview-image': inputs['image']}