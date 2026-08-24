import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { StructuredVisualization, StructuredViewerState } from './StructuredVisualization';

describe('structured visualization renderers', () => {
  it('renders a confusion matrix as an accessible HTML table fallback', () => {
    const markup = renderToStaticMarkup(<StructuredVisualization payload={{
      schema: 'aoi.confusion-matrix.v1', labels: ['good', 'bad'], matrix: [[8, 1], [2, 7]],
    }} title="Confusion matrix" />);

    expect(markup).toContain('<table');
    expect(markup).toContain('<caption>Confusion matrix</caption>');
    expect(markup).toContain('scope="col"');
    expect(markup).toContain('scope="row"');
    expect(markup).toContain('Predicted good');
  });

  it('renders typed tables with semantic headers and cells', () => {
    const markup = renderToStaticMarkup(<StructuredVisualization payload={{
      schema: 'aoi.table.v1',
      columns: [{ key: 'label', label: 'Label', type: 'string' }, { key: 'score', label: 'Score', type: 'number' }],
      rows: [{ label: 'good', score: 0.98 }],
    }} title="Classification report" />);

    expect(markup).toContain('<table');
    expect(markup).toContain('<caption>Classification report</caption>');
    expect(markup).toContain('<th scope="col">Score</th>');
    expect(markup).toContain('<td>0.98</td>');
  });

  it('renders plot series in a bounded accessible SVG', () => {
    const markup = renderToStaticMarkup(<StructuredVisualization payload={{
      schema: 'aoi.plot-series.v1', xLabel: 'Epoch', yLabel: 'Accuracy',
      series: [{ key: 'accuracy', label: 'Accuracy', kind: 'line', x: [0, 1, 2], y: [0.5, 0.75, 1] }],
    }} title="Training accuracy" />);

    expect(markup).toContain('<svg');
    expect(markup).toContain('viewBox="0 0 640 360"');
    expect(markup).toContain('<title>Training accuracy</title>');
    expect(markup).toContain('aria-label="Training accuracy"');
    expect(markup).toContain('<polyline');
  });

  it('shows loading, safe errors, and static media fallback states', () => {
    expect(renderToStaticMarkup(<StructuredViewerState state={{ status: 'loading' }} title="Report" />)).toContain('Loading Report');
    expect(renderToStaticMarkup(<StructuredViewerState state={{ status: 'error', message: 'Artifact is malformed.' }} title="Report" />)).toContain('role="alert"');
    expect(renderToStaticMarkup(<StructuredViewerState state={{ status: 'error', message: 'Artifact exceeds the 2 MB limit.', fallbackUrl: 'blob:fallback' }} title="Report" />)).toContain('src="blob:fallback"');
  });

  it('always renders a semantic heightmap summary and keyboard alternative', () => {
    const markup = renderToStaticMarkup(<StructuredVisualization payload={{
      schema: 'aoi.heightmap.v1', rows: 2, columns: 3,
      values: [[0, 1.5, null], [2, 3, 4]], xSpacing: 0.5, ySpacing: 1, unit: 'μm',
    }} title="Board surface" />);

    expect(markup).toContain('Board surface summary');
    expect(markup).toContain('<dt>Grid</dt><dd>2 × 3</dd>');
    expect(markup).toContain('<dt>Valid samples</dt><dd>5</dd>');
    expect(markup).toContain('<dt>Missing samples</dt><dd>1</dd>');
    expect(markup).toContain('<dt>Range</dt><dd>0–4 μm</dd>');
    expect(markup).toContain('Arrow keys rotate');
    expect(markup).toContain('<dt>X spacing</dt><dd>0.5 μm</dd>');
  });
});