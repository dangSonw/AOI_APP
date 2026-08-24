import { describe, expect, it } from 'vitest';
import { parseViewerDescriptor, parseVisualizationPayload, type ViewerDescriptor } from './visualization';

describe('visualization contracts', () => {
  it('parses confusion, table, and plot payloads with a typed descriptor', () => {
    expect(parseVisualizationPayload({ schema: 'aoi.confusion-matrix.v1', labels: ['cat', 'dog'], matrix: [[1, 0], [0, 1]] }).schema).toBe('aoi.confusion-matrix.v1');
    expect(parseVisualizationPayload({ schema: 'aoi.table.v1', columns: [{ key: 'label', label: 'Label', type: 'string' }], rows: [{ label: 'cat' }] }).schema).toBe('aoi.table.v1');
    expect(parseVisualizationPayload({ schema: 'aoi.plot-series.v1', series: [{ key: 'score', label: 'Score', kind: 'line', x: [0], y: [1] }] }).schema).toBe('aoi.plot-series.v1');
    const descriptor: ViewerDescriptor = { nodeInstanceId: 'node-1', title: 'Result', kind: 'plot-2d', schema: 'aoi.plot-series.v1', artifactEndpoint: '/api/v1/research/artifacts/1', width: 640, height: 360, xLabel: '', yLabel: '', xUnit: '', yUnit: '', interactions: ['focus'], fallbackMediaType: 'image/png' };
    expect(descriptor.kind).toBe('plot-2d');
  });

  it('rejects malformed dimensions and non-finite values', () => {
    expect(() => parseVisualizationPayload({ schema: 'aoi.confusion-matrix.v1', labels: ['cat'], matrix: [[1, 0]] })).toThrow('dimensions');
    expect(() => parseVisualizationPayload({ schema: 'aoi.plot-series.v1', series: [{ key: 'x', label: 'X', kind: 'line', x: [0], y: [Infinity] }] })).toThrow('finite');
    expect(() => parseVisualizationPayload({ schema: 'aoi.table.v1', columns: [], rows: [] })).toThrow('columns');
  });

  it('parses a bounded versioned heightmap and rejects invalid grids', () => {
    const payload = parseVisualizationPayload({
      schema: 'aoi.heightmap.v1', rows: 2, columns: 3,
      values: [[0, 1.5, null], [2, 3, 4]], xSpacing: 0.5, ySpacing: 1, unit: 'μm',
    });
    expect(payload.schema).toBe('aoi.heightmap.v1');
    expect(() => parseVisualizationPayload({ schema: 'aoi.heightmap.v1', rows: 1, columns: 513, values: [[]], xSpacing: 1, ySpacing: 1, unit: 'mm' })).toThrow('dimensions');
    expect(() => parseVisualizationPayload({ schema: 'aoi.heightmap.v1', rows: 2, columns: 2, values: [[Infinity, 0], [1, 2]], xSpacing: 1, ySpacing: 1, unit: 'mm' })).toThrow('finite');
    expect(() => parseVisualizationPayload({ schema: 'aoi.heightmap.v1', rows: 2, columns: 2, values: [[null, null], [null, null]], xSpacing: 1, ySpacing: 1, unit: 'mm' })).toThrow('sample');
  });

  it('accepts only matching heightmap descriptors', () => {
    const descriptor = parseViewerDescriptor({
      nodeInstanceId: 'heightmap-1', title: 'Surface', kind: 'heightmap', schema: 'aoi.heightmap.v1',
      artifactEndpoint: '/api/v1/research/artifacts/9', width: 640, height: 360,
      xLabel: 'X', yLabel: 'Y', xUnit: 'mm', yUnit: 'mm', interactions: ['focus', 'pan', 'zoom'], fallbackMediaType: 'image/png',
    });
    expect(descriptor.schema).toBe('aoi.heightmap.v1');
    expect(() => parseViewerDescriptor({ ...descriptor, schema: 'aoi.table.v1' })).toThrow('kind and schema');
  });
});