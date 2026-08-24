export type VisualizationSchema = 'aoi.confusion-matrix.v1' | 'aoi.table.v1' | 'aoi.plot-series.v1' | 'aoi.heightmap.v1';
export interface ConfusionMatrixPayload { schema: 'aoi.confusion-matrix.v1'; labels: string[]; matrix: number[][] }
export interface TableColumn { key: string; label: string; type: 'string' | 'number' | 'integer' | 'boolean' }
export interface TablePayload { schema: 'aoi.table.v1'; columns: TableColumn[]; rows: Array<Record<string, string | number | boolean>> }
export interface PlotSeries { key: string; label: string; kind: 'line' | 'scatter' | 'bar'; x: number[]; y: number[] }
export interface PlotSeriesPayload { schema: 'aoi.plot-series.v1'; xLabel?: string; yLabel?: string; series: PlotSeries[] }
export interface HeightmapPayload { schema: 'aoi.heightmap.v1'; rows: number; columns: number; values: Array<Array<number | null>>; xSpacing: number; ySpacing: number; unit: string }
export type VisualizationPayload = ConfusionMatrixPayload | TablePayload | PlotSeriesPayload | HeightmapPayload;
export interface ViewerDescriptor { nodeInstanceId: string; title: string; kind: 'image' | 'plot-2d' | 'table' | 'heightmap'; schema: VisualizationSchema; artifactEndpoint: string; width: number | null; height: number | null; xLabel: string; yLabel: string; xUnit: string; yUnit: string; interactions: Array<'focus' | 'download' | 'pan' | 'zoom'>; fallbackMediaType: 'image/png' | 'image/svg+xml' | null }

const schemas: VisualizationSchema[] = ['aoi.confusion-matrix.v1', 'aoi.table.v1', 'aoi.plot-series.v1', 'aoi.heightmap.v1'];
const kinds: ViewerDescriptor['kind'][] = ['image', 'plot-2d', 'table', 'heightmap'];
const interactions: ViewerDescriptor['interactions'][number][] = ['focus', 'download', 'pan', 'zoom'];

export function parseViewerDescriptor(value: unknown): ViewerDescriptor {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Viewer descriptor must be an object.');
  const descriptor = value as Record<string, unknown>;
  if (typeof descriptor.nodeInstanceId !== 'string' || !descriptor.nodeInstanceId) throw new Error('Viewer node instance is invalid.');
  if (typeof descriptor.title !== 'string' || !descriptor.title) throw new Error('Viewer title is invalid.');
  if (!kinds.includes(descriptor.kind as ViewerDescriptor['kind'])) throw new Error('Viewer kind is invalid.');
  if (!schemas.includes(descriptor.schema as VisualizationSchema)) throw new Error('Viewer schema is invalid.');
  if (descriptor.kind === 'heightmap' && descriptor.schema !== 'aoi.heightmap.v1') throw new Error('Viewer kind and schema do not match.');
  if (typeof descriptor.artifactEndpoint !== 'string' || !/^\/api\/v1\/research\/artifacts\/\d+$/.test(descriptor.artifactEndpoint)) throw new Error('Viewer artifact endpoint is invalid.');
  if (!Array.isArray(descriptor.interactions) || descriptor.interactions.some((item) => !interactions.includes(item as ViewerDescriptor['interactions'][number]))) throw new Error('Viewer interactions are invalid.');
  if (![null, 'image/png', 'image/svg+xml'].includes(descriptor.fallbackMediaType as null | string)) throw new Error('Viewer fallback media type is invalid.');
  for (const field of ['xLabel', 'yLabel', 'xUnit', 'yUnit'] as const) {
    if (typeof descriptor[field] !== 'string') throw new Error(`Viewer ${field} is invalid.`);
  }
  for (const field of ['width', 'height'] as const) {
    if (descriptor[field] !== null && (!Number.isInteger(descriptor[field]) || (descriptor[field] as number) < 1 || (descriptor[field] as number) > 4096)) throw new Error(`Viewer ${field} is invalid.`);
  }
  return descriptor as unknown as ViewerDescriptor;
}

const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value);
export function parseVisualizationPayload(value: unknown): VisualizationPayload {
  if (!value || typeof value !== 'object') throw new Error('Visualization payload must be an object.');
  const payload = value as Record<string, unknown>;
  if (payload.schema === 'aoi.confusion-matrix.v1') {
    const labels = payload.labels, matrix = payload.matrix;
    if (!Array.isArray(labels) || labels.length < 1 || labels.length > 256 || labels.some((label) => typeof label !== 'string') || new Set(labels).size !== labels.length) throw new Error('Confusion labels are invalid.');
    if (!Array.isArray(matrix) || matrix.length !== labels.length || matrix.some((row) => !Array.isArray(row) || row.length !== labels.length || row.some((item) => !Number.isInteger(item) || item < 0))) throw new Error('Confusion matrix dimensions or values are invalid.');
    return payload as unknown as ConfusionMatrixPayload;
  }
  if (payload.schema === 'aoi.table.v1') {
    if (!Array.isArray(payload.columns) || payload.columns.length < 1 || payload.columns.length > 128) throw new Error('Table columns are invalid.');
    if (!Array.isArray(payload.rows) || payload.rows.length > 10000) throw new Error('Table rows are invalid.');
    return payload as unknown as TablePayload;
  }
  if (payload.schema === 'aoi.plot-series.v1') {
    if (!Array.isArray(payload.series) || payload.series.length < 1 || payload.series.length > 64) throw new Error('Plot series are invalid.');
    for (const item of payload.series as Array<Record<string, unknown>>) {
      if (!Array.isArray(item.x) || !Array.isArray(item.y) || item.x.length !== item.y.length || item.x.length < 1 || item.x.length > 10000) throw new Error('Plot point dimensions are invalid.');
      if (![...item.x, ...item.y].every(finite)) throw new Error('Plot values must be finite.');
    }
    return payload as unknown as PlotSeriesPayload;
  }
  if (payload.schema === 'aoi.heightmap.v1') {
    const rows = payload.rows, columns = payload.columns, values = payload.values;
    if (!Number.isInteger(rows) || !Number.isInteger(columns) || (rows as number) < 2 || (columns as number) < 2 || (rows as number) > 512 || (columns as number) > 512) throw new Error('Heightmap dimensions are invalid.');
    if (!Array.isArray(values) || values.length !== rows || values.some((row) => !Array.isArray(row) || row.length !== columns)) throw new Error('Heightmap dimensions must match values.');
    const samples = values.flat() as unknown[];
    if (samples.some((sample) => sample !== null && !finite(sample))) throw new Error('Heightmap values must be finite or null.');
    if (!samples.some(finite)) throw new Error('Heightmap must contain at least one valid sample.');
    if (!finite(payload.xSpacing) || !finite(payload.ySpacing) || payload.xSpacing <= 0 || payload.ySpacing <= 0) throw new Error('Heightmap spacing must be positive and finite.');
    if (typeof payload.unit !== 'string' || !payload.unit || payload.unit.length > 32) throw new Error('Heightmap unit is invalid.');
    return payload as unknown as HeightmapPayload;
  }
  throw new Error('Visualization schema is unsupported.');
}