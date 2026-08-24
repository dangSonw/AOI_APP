import type { NodeResultPluginProps } from '../types';

export function SvmImageClassifierResultView({ result, context }: NodeResultPluginProps) {
  const metrics = (result.metrics ?? {}) as Record<string, number>;
  const report = (result.report ?? {}) as { rows?: Array<Record<string, unknown>> };
  const confusion = (result.confusionMatrix ?? result['confusion-matrix'] ?? {}) as { labels?: string[]; matrix?: number[][] };
  const runId = typeof result.runId === 'string' ? result.runId : '';
  return (
    <section className="svm-result" aria-label="SVM classification results">
      <h3>Classification results</h3>
      <p><strong>Accuracy</strong> {Number.isFinite(metrics.accuracy) ? `${(metrics.accuracy * 100).toFixed(1)}%` : 'Not available'}</p>
      {report.rows && <table><caption>Classification report</caption><thead><tr><th>Label</th><th>Precision</th><th>Recall</th></tr></thead><tbody>{report.rows.map((row, index) => <tr key={`${String(row.label)}-${index}`}><th>{String(row.label)}</th><td>{String(row.precision ?? '—')}</td><td>{String(row.recall ?? '—')}</td></tr>)}</tbody></table>}
      {confusion.labels && confusion.matrix && <table><caption>Confusion matrix</caption><thead><tr><th>Actual / predicted</th>{confusion.labels.map((label) => <th key={label}>{label}</th>)}</tr></thead><tbody>{confusion.labels.map((label, row) => <tr key={label}><th>{label}</th>{confusion.matrix?.[row]?.map((value, column) => <td key={`${row}-${column}`}>{value}</td>)}</tr>)}</tbody></table>}
      {runId && <button type="button" className="secondary-button" onClick={() => context?.training.openRun(runId)}>Open run</button>}
    </section>
  );
}