from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse
from core.visualization.contracts import ConfusionMatrixPayload, PlotSeriesPayload

NODE_ID = 'plot-2d-output'
USE = NodeUse.RELEASE
INPUT_KEYS = ('payload',)
OUTPUT_KEYS = ('validated-payload',)

def execute(inputs: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    del parameters
    value = inputs.get('payload')
    if not isinstance(value, dict):
        raise ValueError('Plot 2D payload must be an object.')
    schema = value.get('schema')
    if schema == 'aoi.confusion-matrix.v1':
        normalized = ConfusionMatrixPayload.from_mapping(value).to_mapping()
    elif schema == 'aoi.plot-series.v1':
        normalized = PlotSeriesPayload.from_mapping(value).to_mapping()
    else:
        raise ValueError('Plot 2D payload schema is unsupported.')
    return {'validated-payload': normalized}