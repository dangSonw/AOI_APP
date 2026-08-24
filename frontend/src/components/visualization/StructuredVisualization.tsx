import { Component, lazy, Suspense, useEffect, useState, type ReactNode } from 'react';
import type { ConfusionMatrixPayload, HeightmapPayload, PlotSeriesPayload, TablePayload, ViewerDescriptor, VisualizationPayload } from '../../types/visualization';
import { readVisualizationArtifact } from '../../services/visualization-service';
import { summarizeHeightmap } from './heightmap-model';

const HeightmapCanvas = lazy(() => import('./HeightmapCanvas'));

class HeightmapCanvasBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    return this.state.failed
      ? <div className="structured-viewer__status structured-viewer__status--error" role="alert">Interactive 3D failed to load. Use the heightmap summary below.</div>
      : this.props.children;
  }
}

export type StructuredViewerLoadState =
  | { status: 'loading' }
  | { status: 'ready'; payload: VisualizationPayload }
  | { status: 'media'; url: string; mediaType: 'image/png' | 'image/svg+xml' }
  | { status: 'error'; message: string; fallbackUrl?: string };

export function StructuredVisualization({ payload, title }: { payload: VisualizationPayload; title: string }) {
  if (payload.schema === 'aoi.confusion-matrix.v1') return <ConfusionMatrixTable payload={payload} title={title} />;
  if (payload.schema === 'aoi.table.v1') return <DataTable payload={payload} title={title} />;
  if (payload.schema === 'aoi.plot-series.v1') return <PlotSeriesSvg payload={payload} title={title} />;
  return <HeightmapVisualization payload={payload} title={title} />;
}

function HeightmapVisualization({ payload, title }: { payload: HeightmapPayload; title: string }) {
  const summary = summarizeHeightmap(payload);
  return <section className="heightmap-viewer" aria-label={`${title} heightmap`}>
    <HeightmapCanvasBoundary><Suspense fallback={<div className="structured-viewer__status" role="status">Loading interactive view…</div>}>
      <HeightmapCanvas payload={payload} title={title} />
    </Suspense></HeightmapCanvasBoundary>
    <p className="heightmap-viewer__instructions">Arrow keys rotate; +/− zoom; 0 resets; Escape leaves the viewer. Drag to rotate and use the wheel to zoom.</p>
    <dl aria-label={`${title} summary`}>
      <div><dt>Grid</dt><dd>{summary.rows} × {summary.columns}</dd></div>
      <div><dt>Valid samples</dt><dd>{summary.validCount}</dd></div>
      <div><dt>Missing samples</dt><dd>{summary.missingCount}</dd></div>
      <div><dt>Range</dt><dd>{summary.minimum}–{summary.maximum} {summary.unit}</dd></div>
      <div><dt>X spacing</dt><dd>{payload.xSpacing} {payload.unit}</dd></div>
      <div><dt>Y spacing</dt><dd>{payload.ySpacing} {payload.unit}</dd></div>
    </dl>
  </section>;
}

export function StructuredViewerState({ state, title }: { state: StructuredViewerLoadState; title: string }) {
  if (state.status === 'loading') return <div className="structured-viewer__status" role="status">Loading {title}…</div>;
  if (state.status === 'ready') return <StructuredVisualization payload={state.payload} title={title} />;
  if (state.status === 'media') return <img className="structured-viewer__fallback" src={state.url} alt={`Static fallback for ${title}`} />;
  return <div className="structured-viewer__status structured-viewer__status--error" role="alert">
    {state.fallbackUrl && <img className="structured-viewer__fallback" src={state.fallbackUrl} alt={`Static fallback for ${title}`} />}
    <span>{state.message}</span>
  </div>;
}

export function StructuredArtifactViewer({ accessToken, descriptor, title }: { accessToken: string; descriptor?: ViewerDescriptor; title: string }) {
  const [state, setState] = useState<StructuredViewerLoadState>({ status: 'loading' });
  useEffect(() => {
    let cancelled = false;
    let objectUrl = '';
    setState({ status: 'loading' });
    if (!descriptor) return () => undefined;
    void readVisualizationArtifact(accessToken, descriptor.artifactEndpoint).then((artifact) => {
      if (cancelled) return;
      if (artifact.kind === 'structured') setState({ status: 'ready', payload: artifact.payload });
      else {
        objectUrl = URL.createObjectURL(artifact.blob);
        setState({ status: 'media', url: objectUrl, mediaType: artifact.mediaType });
      }
    }).catch((error) => {
      if (!cancelled) setState({ status: 'error', message: error instanceof Error ? error.message : 'Artifact is unavailable.' });
    });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [accessToken, descriptor]);
  if (!descriptor) return <div className="structured-viewer__status" role="status">Run workflow to generate {title}</div>;
  return <StructuredViewerState state={state} title={title} />;
}

function ConfusionMatrixTable({ payload, title }: { payload: ConfusionMatrixPayload; title: string }) {
  return <div className="structured-viewer__scroll"><table className="structured-table structured-table--matrix">
    <caption>{title}</caption>
    <thead><tr><th scope="col">Actual / predicted</th>{payload.labels.map((label) => <th scope="col" key={label}>Predicted {label}</th>)}</tr></thead>
    <tbody>{payload.labels.map((label, row) => <tr key={label}><th scope="row">Actual {label}</th>{payload.matrix[row].map((value, column) => <td key={payload.labels[column]}>{value}</td>)}</tr>)}</tbody>
  </table></div>;
}

function DataTable({ payload, title }: { payload: TablePayload; title: string }) {
  return <div className="structured-viewer__scroll"><table className="structured-table">
    <caption>{title}</caption>
    <thead><tr>{payload.columns.map((column) => <th scope="col" key={column.key}>{column.label}</th>)}</tr></thead>
    <tbody>{payload.rows.map((row, index) => <tr key={index}>{payload.columns.map((column) => <td key={column.key}>{String(row[column.key])}</td>)}</tr>)}</tbody>
  </table></div>;
}

function PlotSeriesSvg({ payload, title }: { payload: PlotSeriesPayload; title: string }) {
  const points = payload.series.flatMap((series) => series.x.map((x, index) => ({ x, y: series.y[index] })));
  const xs = points.map((point) => point.x), ys = points.map((point) => point.y);
  const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
  const scaleX = (value: number) => 48 + ((value - minX) / (maxX - minX || 1)) * 568;
  const scaleY = (value: number) => 320 - ((value - minY) / (maxY - minY || 1)) * 280;
  return <svg className="structured-plot" viewBox="0 0 640 360" role="img" aria-label={title}>
    <title>{title}</title>
    <line x1="48" y1="320" x2="616" y2="320" /><line x1="48" y1="40" x2="48" y2="320" />
    {payload.series.map((series) => series.kind === 'line'
      ? <polyline key={series.key} points={series.x.map((x, index) => `${scaleX(x)},${scaleY(series.y[index])}`).join(' ')} fill="none" />
      : series.x.map((x, index) => <circle key={`${series.key}-${index}`} cx={scaleX(x)} cy={scaleY(series.y[index])} r={series.kind === 'bar' ? 5 : 3} />))}
    <text x="332" y="350" textAnchor="middle">{payload.xLabel ?? 'X'}</text>
    <text x="14" y="180" textAnchor="middle" transform="rotate(-90 14 180)">{payload.yLabel ?? 'Y'}</text>
  </svg>;
}