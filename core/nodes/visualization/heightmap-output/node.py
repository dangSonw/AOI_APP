from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse


NODE_ID = 'heightmap-output'
USE = NodeUse.DEBUG
INPUT_KEYS = ('heightmap',)
OUTPUT_KEYS = ('measurement-heightmap',)


def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    if 'heightmap' not in inputs:
        raise ValueError('3D measurement output requires a heightmap input.')
    return {'measurement-heightmap': inputs['heightmap']}