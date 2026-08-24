from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping


MAX_LABELS = 256
MAX_TABLE_COLUMNS = 128
MAX_TABLE_ROWS = 10_000
MAX_PLOT_SERIES = 64
MAX_PLOT_POINTS = 10_000
MAX_HEIGHTMAP_DIMENSION = 512
SCHEMAS = frozenset({'aoi.confusion-matrix.v1', 'aoi.table.v1', 'aoi.plot-series.v1', 'aoi.heightmap.v1'})
CONFUSION_MATRIX_SCHEMA = 'aoi.confusion-matrix.v1'
TABLE_SCHEMA = 'aoi.table.v1'
PLOT_SERIES_SCHEMA = 'aoi.plot-series.v1'
HEIGHTMAP_SCHEMA = 'aoi.heightmap.v1'


def _mapping(value: object, message: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(message)
    return value


def _finite_number(value: object, message: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(message)
    return float(value)


@dataclass(frozen=True, slots=True)
class ConfusionMatrixPayload:
    labels: tuple[str, ...]
    matrix: tuple[tuple[int, ...], ...]
    schema: str = CONFUSION_MATRIX_SCHEMA

    @classmethod
    def from_mapping(cls, value: object) -> 'ConfusionMatrixPayload':
        payload = _mapping(value, 'Confusion matrix payload must be an object.')
        if set(payload) != {'schema', 'labels', 'matrix'} or payload.get('schema') != CONFUSION_MATRIX_SCHEMA:
            raise ValueError('Confusion matrix schema is invalid.')
        raw_labels, raw_matrix = payload['labels'], payload['matrix']
        if not isinstance(raw_labels, list) or not 1 <= len(raw_labels) <= MAX_LABELS:
            raise ValueError('Confusion matrix labels are invalid.')
        labels = tuple(str(label) for label in raw_labels)
        if any(not label or len(label) > 200 for label in labels) or len(set(labels)) != len(labels):
            raise ValueError('Confusion matrix labels must be unique and non-empty.')
        if not isinstance(raw_matrix, list) or len(raw_matrix) != len(labels):
            raise ValueError('Confusion matrix dimensions must match labels.')
        rows: list[tuple[int, ...]] = []
        for row in raw_matrix:
            if not isinstance(row, list) or len(row) != len(labels):
                raise ValueError('Confusion matrix dimensions must be square.')
            if any(isinstance(item, bool) or not isinstance(item, int) or item < 0 for item in row):
                raise ValueError('Confusion matrix values must be non-negative integers.')
            rows.append(tuple(row))
        return cls(labels=labels, matrix=tuple(rows))

    def to_mapping(self) -> dict[str, Any]:
        return {'schema': self.schema, 'labels': list(self.labels), 'matrix': [list(row) for row in self.matrix]}


@dataclass(frozen=True, slots=True)
class TableColumn:
    key: str
    label: str
    type: str


@dataclass(frozen=True, slots=True)
class TablePayload:
    columns: tuple[TableColumn, ...]
    rows: tuple[dict[str, Any], ...]
    schema: str = TABLE_SCHEMA

    @classmethod
    def from_mapping(cls, value: object) -> 'TablePayload':
        payload = _mapping(value, 'Table payload must be an object.')
        if set(payload) != {'schema', 'columns', 'rows'} or payload.get('schema') != TABLE_SCHEMA:
            raise ValueError('Table schema is invalid.')
        raw_columns, raw_rows = payload['columns'], payload['rows']
        if not isinstance(raw_columns, list) or not 1 <= len(raw_columns) <= MAX_TABLE_COLUMNS:
            raise ValueError('Table columns are invalid.')
        columns: list[TableColumn] = []
        for raw in raw_columns:
            column = _mapping(raw, 'Table column must be an object.')
            if set(column) != {'key', 'label', 'type'} or column['type'] not in {'string', 'number', 'integer', 'boolean'}:
                raise ValueError('Table column contract is invalid.')
            columns.append(TableColumn(str(column['key']), str(column['label']), str(column['type'])))
        keys = [column.key for column in columns]
        if any(not key for key in keys) or len(set(keys)) != len(keys):
            raise ValueError('Table column keys must be unique and non-empty.')
        if not isinstance(raw_rows, list) or len(raw_rows) > MAX_TABLE_ROWS:
            raise ValueError('Table row count exceeds its limit.')
        rows: list[dict[str, Any]] = []
        for raw in raw_rows:
            row = dict(_mapping(raw, 'Table row must be an object.'))
            if set(row) != set(keys):
                raise ValueError('Table row keys must match columns.')
            for column in columns:
                item = row[column.key]
                if column.type == 'string' and not isinstance(item, str):
                    raise ValueError('Table row value does not match its string column.')
                if column.type == 'boolean' and not isinstance(item, bool):
                    raise ValueError('Table row value does not match its boolean column.')
                if column.type == 'integer' and (isinstance(item, bool) or not isinstance(item, int)):
                    raise ValueError('Table row value does not match its integer column.')
                if column.type == 'number':
                    _finite_number(item, 'Table row number must be finite.')
            rows.append(row)
        return cls(columns=tuple(columns), rows=tuple(rows))

    def to_mapping(self) -> dict[str, Any]:
        return {'schema': self.schema, 'columns': [{'key': column.key, 'label': column.label, 'type': column.type} for column in self.columns], 'rows': [dict(row) for row in self.rows]}


@dataclass(frozen=True, slots=True)
class PlotSeries:
    key: str
    label: str
    kind: str
    x: tuple[float, ...]
    y: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class PlotSeriesPayload:
    series: tuple[PlotSeries, ...]
    x_label: str = ''
    y_label: str = ''
    schema: str = PLOT_SERIES_SCHEMA

    @classmethod
    def from_mapping(cls, value: object) -> 'PlotSeriesPayload':
        payload = _mapping(value, 'Plot payload must be an object.')
        if set(payload) - {'schema', 'series', 'xLabel', 'yLabel'} or payload.get('schema') != PLOT_SERIES_SCHEMA:
            raise ValueError('Plot schema is invalid.')
        raw_series = payload.get('series')
        if not isinstance(raw_series, list) or not 1 <= len(raw_series) <= MAX_PLOT_SERIES:
            raise ValueError('Plot series are invalid.')
        result: list[PlotSeries] = []
        for raw in raw_series:
            item = _mapping(raw, 'Plot series must be an object.')
            if set(item) != {'key', 'label', 'kind', 'x', 'y'} or item['kind'] not in {'line', 'scatter', 'bar'}:
                raise ValueError('Plot series contract is invalid.')
            if not isinstance(item['x'], list) or not isinstance(item['y'], list) or len(item['x']) != len(item['y']):
                raise ValueError('Plot series x/y dimensions must match.')
            if not 1 <= len(item['x']) <= MAX_PLOT_POINTS:
                raise ValueError('Plot series points exceed their limit.')
            x = tuple(_finite_number(point, 'Plot values must be finite.') for point in item['x'])
            y = tuple(_finite_number(point, 'Plot values must be finite.') for point in item['y'])
            result.append(PlotSeries(str(item['key']), str(item['label']), str(item['kind']), x, y))
        return cls(series=tuple(result), x_label=str(payload.get('xLabel', '')), y_label=str(payload.get('yLabel', '')))

    def to_mapping(self) -> dict[str, Any]:
        return {'schema': self.schema, 'xLabel': self.x_label, 'yLabel': self.y_label, 'series': [{'key': item.key, 'label': item.label, 'kind': item.kind, 'x': list(item.x), 'y': list(item.y)} for item in self.series]}


@dataclass(frozen=True, slots=True)
class HeightmapPayload:
    rows: int
    columns: int
    values: tuple[tuple[float | None, ...], ...]
    x_spacing: float
    y_spacing: float
    unit: str
    schema: str = HEIGHTMAP_SCHEMA

    @classmethod
    def from_mapping(cls, value: object) -> 'HeightmapPayload':
        payload = _mapping(value, 'Heightmap payload must be an object.')
        if set(payload) != {'schema', 'rows', 'columns', 'values', 'xSpacing', 'ySpacing', 'unit'} or payload.get('schema') != HEIGHTMAP_SCHEMA:
            raise ValueError('Heightmap schema is invalid.')
        rows, columns = payload['rows'], payload['columns']
        if any(isinstance(item, bool) or not isinstance(item, int) or not 2 <= item <= MAX_HEIGHTMAP_DIMENSION for item in (rows, columns)):
            raise ValueError('Heightmap dimensions are invalid.')
        raw_values = payload['values']
        if not isinstance(raw_values, list) or len(raw_values) != rows:
            raise ValueError('Heightmap dimensions must match values.')
        values: list[tuple[float | None, ...]] = []
        valid_count = 0
        for raw_row in raw_values:
            if not isinstance(raw_row, list) or len(raw_row) != columns:
                raise ValueError('Heightmap dimensions must match values.')
            row: list[float | None] = []
            for item in raw_row:
                if item is None:
                    row.append(None)
                else:
                    row.append(_finite_number(item, 'Heightmap values must be finite or null.'))
                    valid_count += 1
            values.append(tuple(row))
        if not valid_count:
            raise ValueError('Heightmap must contain at least one valid sample.')
        x_spacing = _finite_number(payload['xSpacing'], 'Heightmap spacing must be finite.')
        y_spacing = _finite_number(payload['ySpacing'], 'Heightmap spacing must be finite.')
        if x_spacing <= 0 or y_spacing <= 0:
            raise ValueError('Heightmap spacing must be positive.')
        unit = payload['unit']
        if not isinstance(unit, str) or not unit or len(unit) > 32:
            raise ValueError('Heightmap unit is invalid.')
        return cls(rows, columns, tuple(values), x_spacing, y_spacing, unit)

    @property
    def valid_count(self) -> int:
        return sum(item is not None for row in self.values for item in row)

    @property
    def minimum(self) -> float:
        return min(item for row in self.values for item in row if item is not None)

    @property
    def maximum(self) -> float:
        return max(item for row in self.values for item in row if item is not None)

    def to_mapping(self) -> dict[str, Any]:
        return {'schema': self.schema, 'rows': self.rows, 'columns': self.columns, 'values': [list(row) for row in self.values], 'xSpacing': self.x_spacing, 'ySpacing': self.y_spacing, 'unit': self.unit}


@dataclass(frozen=True, slots=True)
class ViewerDescriptor:
    node_instance_id: str
    title: str
    kind: str
    schema: str
    artifact_endpoint: str
    width: int | None
    height: int | None
    x_label: str
    y_label: str
    x_unit: str
    y_unit: str
    interactions: tuple[str, ...]
    fallback_media_type: str | None

    @classmethod
    def from_mapping(cls, value: object) -> 'ViewerDescriptor':
        payload = _mapping(value, 'Viewer descriptor must be an object.')
        required = {'nodeInstanceId', 'title', 'kind', 'schema', 'artifactEndpoint', 'interactions', 'fallbackMediaType'}
        if not required <= set(payload) or payload['kind'] not in {'image', 'plot-2d', 'table', 'heightmap'} or payload['schema'] not in SCHEMAS:
            raise ValueError('Viewer descriptor contract is invalid.')
        if payload['kind'] == 'heightmap' and payload['schema'] != HEIGHTMAP_SCHEMA:
            raise ValueError('Viewer kind and schema do not match.')
        endpoint = str(payload['artifactEndpoint'])
        if not endpoint.startswith('/api/v1/research/artifacts/'):
            raise ValueError('Viewer artifact endpoint must use the authenticated research API.')
        width, height = payload.get('width'), payload.get('height')
        if width is not None and (isinstance(width, bool) or not isinstance(width, int) or not 1 <= width <= 8192):
            raise ValueError('Viewer width is invalid.')
        if height is not None and (isinstance(height, bool) or not isinstance(height, int) or not 1 <= height <= 8192):
            raise ValueError('Viewer height is invalid.')
        interactions = payload['interactions']
        if not isinstance(interactions, list) or any(item not in {'focus', 'download', 'pan', 'zoom'} for item in interactions):
            raise ValueError('Viewer interactions are invalid.')
        fallback = payload['fallbackMediaType']
        if fallback not in {None, 'image/png', 'image/svg+xml'}:
            raise ValueError('Viewer fallback media type is invalid.')
        return cls(str(payload['nodeInstanceId']), str(payload['title']), str(payload['kind']), str(payload['schema']), endpoint, width, height, str(payload.get('xLabel', '')), str(payload.get('yLabel', '')), str(payload.get('xUnit', '')), str(payload.get('yUnit', '')), tuple(interactions), fallback)

    def to_mapping(self) -> dict[str, Any]:
        return {'nodeInstanceId': self.node_instance_id, 'title': self.title, 'kind': self.kind, 'schema': self.schema, 'artifactEndpoint': self.artifact_endpoint, 'width': self.width, 'height': self.height, 'xLabel': self.x_label, 'yLabel': self.y_label, 'xUnit': self.x_unit, 'yUnit': self.y_unit, 'interactions': list(self.interactions), 'fallbackMediaType': self.fallback_media_type}