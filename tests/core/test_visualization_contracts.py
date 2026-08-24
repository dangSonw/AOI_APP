import math

import pytest

from core.visualization.contracts import (
    ConfusionMatrixPayload, HeightmapPayload, PlotSeriesPayload, TablePayload, ViewerDescriptor,
)


def test_structured_viewer_payloads_round_trip() -> None:
    confusion = ConfusionMatrixPayload.from_mapping({
        'schema': 'aoi.confusion-matrix.v1', 'labels': ['cat', 'dog'], 'matrix': [[3, 1], [0, 4]],
    })
    table = TablePayload.from_mapping({
        'schema': 'aoi.table.v1',
        'columns': [{'key': 'label', 'label': 'Label', 'type': 'string'}, {'key': 'score', 'label': 'Score', 'type': 'number'}],
        'rows': [{'label': 'cat', 'score': 0.9}],
    })
    plot = PlotSeriesPayload.from_mapping({
        'schema': 'aoi.plot-series.v1', 'xLabel': 'Threshold', 'yLabel': 'Accuracy',
        'series': [{'key': 'accuracy', 'label': 'Accuracy', 'kind': 'line', 'x': [0, 1], 'y': [0.5, 1]}],
    })
    descriptor = ViewerDescriptor.from_mapping({
        'nodeInstanceId': 'plot-01', 'title': 'Accuracy', 'kind': 'plot-2d',
        'schema': plot.schema, 'artifactEndpoint': '/api/v1/research/artifacts/7',
        'width': 640, 'height': 360, 'xLabel': 'Threshold', 'yLabel': 'Accuracy',
        'xUnit': '', 'yUnit': '%', 'interactions': ['focus'], 'fallbackMediaType': 'image/png',
    })
    assert confusion.to_mapping()['matrix'] == [[3, 1], [0, 4]]
    assert table.to_mapping()['rows'][0]['score'] == 0.9
    assert plot.to_mapping()['series'][0]['kind'] == 'line'
    assert descriptor.to_mapping()['artifactEndpoint'].endswith('/7')


@pytest.mark.parametrize('payload', [
    {'schema': 'aoi.confusion-matrix.v1', 'labels': ['a'], 'matrix': [[1, 2]]},
    {'schema': 'aoi.confusion-matrix.v1', 'labels': ['a', 'a'], 'matrix': [[1, 0], [0, 1]]},
    {'schema': 'aoi.confusion-matrix.v1', 'labels': ['a'], 'matrix': [[-1]]},
])
def test_confusion_matrix_rejects_invalid_dimensions_labels_and_values(payload) -> None:
    with pytest.raises(ValueError): ConfusionMatrixPayload.from_mapping(payload)


def test_table_plot_and_descriptor_reject_malformed_oversized_or_non_finite_values() -> None:
    with pytest.raises(ValueError, match='row'):
        TablePayload.from_mapping({'schema': 'aoi.table.v1', 'columns': [{'key': 'value', 'label': 'Value', 'type': 'number'}], 'rows': [{'value': 'bad'}]})
    with pytest.raises(ValueError, match='finite'):
        PlotSeriesPayload.from_mapping({'schema': 'aoi.plot-series.v1', 'series': [{'key': 'x', 'label': 'X', 'kind': 'scatter', 'x': [0], 'y': [math.inf]}]})
    with pytest.raises(ValueError, match='points'):
        PlotSeriesPayload.from_mapping({'schema': 'aoi.plot-series.v1', 'series': [{'key': 'x', 'label': 'X', 'kind': 'line', 'x': list(range(10001)), 'y': list(range(10001))}]})
    with pytest.raises(ValueError, match='endpoint'):
        ViewerDescriptor.from_mapping({'nodeInstanceId': 'x', 'title': 'X', 'kind': 'table', 'schema': 'aoi.table.v1', 'artifactEndpoint': 'file:///secret', 'interactions': [], 'fallbackMediaType': None})


def test_bounded_heightmap_round_trips_with_missing_samples() -> None:
    payload = HeightmapPayload.from_mapping({
        'schema': 'aoi.heightmap.v1', 'rows': 2, 'columns': 3,
        'values': [[0, 1.5, None], [2, 3, 4]],
        'xSpacing': 0.5, 'ySpacing': 1, 'unit': 'μm',
    })

    assert payload.to_mapping()['values'][0] == [0.0, 1.5, None]
    assert payload.valid_count == 5
    assert payload.minimum == 0
    assert payload.maximum == 4


@pytest.mark.parametrize('payload, message', [
    ({'schema': 'aoi.heightmap.v1', 'rows': 1, 'columns': 513, 'values': [[0] * 513], 'xSpacing': 1, 'ySpacing': 1, 'unit': 'mm'}, 'dimensions'),
    ({'schema': 'aoi.heightmap.v1', 'rows': 2, 'columns': 2, 'values': [[0, 1]], 'xSpacing': 1, 'ySpacing': 1, 'unit': 'mm'}, 'dimensions'),
    ({'schema': 'aoi.heightmap.v1', 'rows': 2, 'columns': 2, 'values': [[0, math.inf], [1, 2]], 'xSpacing': 1, 'ySpacing': 1, 'unit': 'mm'}, 'finite'),
    ({'schema': 'aoi.heightmap.v1', 'rows': 2, 'columns': 2, 'values': [[None, None], [None, None]], 'xSpacing': 1, 'ySpacing': 1, 'unit': 'mm'}, 'sample'),
    ({'schema': 'aoi.heightmap.v1', 'rows': 2, 'columns': 2, 'values': [[0, 1], [2, 3]], 'xSpacing': 0, 'ySpacing': 1, 'unit': 'mm'}, 'spacing'),
])
def test_heightmap_rejects_malformed_oversized_and_non_finite_data(payload, message) -> None:
    with pytest.raises(ValueError, match=message):
        HeightmapPayload.from_mapping(payload)