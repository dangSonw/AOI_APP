import { useEffect, useReducer, useState } from 'react';
import { ReproducibilityManifestDialog } from '../components/research/ReproducibilityManifestDialog';
import { searchResearchRuns } from '../services/research-service';
import type { ResearchRun } from '../types/research';

interface ResearchPageProps {
  accessToken: string;
  initialRuns?: ResearchRun[];
  initialQuery?: string;
}

interface ResearchComparisonState {
  selectedRunIds: string[];
  isComparisonOpen: boolean;
}

type ResearchComparisonAction =
  | { type: 'select'; runId: string; isSelected: boolean }
  | { type: 'open' }
  | { type: 'close' };

const INITIAL_COMPARISON_STATE: ResearchComparisonState = {
  selectedRunIds: [],
  isComparisonOpen: false,
};

const PAGE_SIZE = 20;

export function transitionResearchComparison(
  state: ResearchComparisonState,
  action: ResearchComparisonAction,
): ResearchComparisonState {
  if (action.type === 'open') {
    return state.selectedRunIds.length >= 2 ? { ...state, isComparisonOpen: true } : state;
  }
  if (action.type === 'close') return { ...state, isComparisonOpen: false };

  const selectedRunIds = action.isSelected
    ? [...new Set([...state.selectedRunIds, action.runId])]
    : state.selectedRunIds.filter((runId) => runId !== action.runId);
  return {
    selectedRunIds,
    isComparisonOpen: state.isComparisonOpen && selectedRunIds.length >= 2,
  };
}

export function ResearchPage({ accessToken, initialRuns = [], initialQuery = '' }: ResearchPageProps) {
  const [runs, setRuns] = useState(initialRuns);
  const [query, setQuery] = useState(initialQuery);
  const [comparison, dispatchComparison] = useReducer(transitionResearchComparison, INITIAL_COMPARISON_STATE);
  const [manifestRunId, setManifestRunId] = useState<string | null>(null);
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);
  const [error, setError] = useState('');

  useEffect(() => {
    if (initialRuns.length > 0) return;
    searchResearchRuns(accessToken, initialQuery).then(setRuns).catch((loadError: unknown) => {
      setError(loadError instanceof Error ? loadError.message : 'Research runs could not be loaded.');
    });
  }, [accessToken, initialQuery, initialRuns.length]);

  const search = async () => {
    setError('');
    try { setRuns(await searchResearchRuns(accessToken, query)); setVisibleCount(PAGE_SIZE); }
    catch (searchError) { setError(searchError instanceof Error ? searchError.message : 'Research search failed.'); }
  };
  const selectedRuns = runs.filter((run) => comparison.selectedRunIds.includes(run.id));
  const completedCount = runs.filter((run) => run.status === 'completed').length;
  const failedCount = runs.filter((run) => run.status === 'failed').length;
  const visibleRuns = runs.slice(0, visibleCount);

  return (
    <section className="research-page" aria-label="Research workspace">
      <header className="research-page__header">
        <form className="research-search" onSubmit={(event) => { event.preventDefault(); void search(); }}>
          <label htmlFor="research-run-search">Search runs</label>
          <input id="research-run-search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Run ID, experiment ID or name, code revision, execution target" />
          <button type="submit">Search</button>
        </form>
      </header>
      <ol className="workspace-guide" aria-label="How to use Research">
        <li><span>1</span><div><strong>Find the right run</strong><p>Search by run, experiment, revision, or execution target.</p></div></li>
        <li><span>2</span><div><strong>Review the evidence</strong><p>Check status, metrics, lineage, artifacts, and failure details.</p></div></li>
        <li><span>3</span><div><strong>Compare outcomes</strong><p>Select two or more runs, then compare their recorded metrics.</p></div></li>
      </ol>
      {error && <div className="studio-message studio-message--error" role="alert">{error}</div>}
      <div className="research-summary" aria-label="Research run summary">
        <span className="summary-card"><small>All runs</small><strong>{runs.length}</strong><em>Tracked experiments</em></span>
        <span className="summary-card summary-card--success"><small>Completed</small><strong>{completedCount}</strong><em>Ready to review</em></span>
        <span className="summary-card summary-card--danger"><small>Failed</small><strong>{failedCount}</strong><em>Need attention</em></span>
        <div className="research-summary__action"><span>{comparison.selectedRunIds.length} selected</span><button type="button" disabled={comparison.selectedRunIds.length < 2} onClick={() => dispatchComparison({ type: 'open' })}>Compare selected</button><small>Select at least 2 runs</small></div>
      </div>
      {comparison.isComparisonOpen && <section className="research-comparison" aria-label="Selected run comparison"><header><div><span className="section-kicker">Side-by-side review</span><h2>Metric comparison</h2></div><button type="button" className="secondary-button" onClick={() => dispatchComparison({ type: 'close' })}>Close comparison</button></header>{selectedRuns.map((run) => <article key={run.id}><strong>{run.id}</strong>{Object.entries(run.metrics).map(([key, value]) => <span key={key}>{key.toLocaleUpperCase()} {value}</span>)}</article>)}</section>}
      <div className="section-heading"><div><span className="section-kicker">Run history</span><h2>Training runs</h2><p>Open a run only when you need its technical evidence.</p></div><span>{runs.length} results</span></div>
      <div className="research-run-list">{visibleRuns.map((run) => (
        <article className={`research-run research-run--${run.status}`} key={run.id}>
          <header className="research-run__header"><div className="research-run__identity"><strong>{run.id}</strong><span>{run.experimentId}</span></div><span className={`status-badge status-badge--${run.status}`}>Status: {run.status.charAt(0).toLocaleUpperCase() + run.status.slice(1)}</span></header>
          <div className="research-run__toolbar"><label className="comparison-check"><input type="checkbox" checked={comparison.selectedRunIds.includes(run.id)} onChange={(event) => dispatchComparison({ type: 'select', runId: run.id, isSelected: event.target.checked })} />Select for comparison</label>{run.createdAt && <time dateTime={run.createdAt}>{new Date(run.createdAt).toLocaleString()}</time>}</div>
          <dl className="research-run__lineage"><div><dt>Code revision</dt><dd><code>{run.codeRevision}</code></dd></div><div><dt>Execution target</dt><dd>{run.executionTarget}</dd></div><div><dt>Random seed</dt><dd>Seed {Object.values(run.randomSeeds)[0] ?? '—'}</dd></div></dl>
          {Object.keys(run.metrics).length > 0 ? <div className="research-run__metrics">{Object.entries(run.metrics).map(([key, value]) => <span key={key}><small>{key.toLocaleUpperCase()}</small><strong>{value}</strong></span>)}</div> : <p className="research-run__no-metrics">No metrics were recorded for this run.</p>}
          {run.error && <div className="research-run__error" role="alert"><strong>Failure diagnostics</strong><p>{run.error}</p></div>}
          <div className="research-run__details">
            <details><summary>Parameters and environment</summary><pre>{JSON.stringify({ nodeVersions: run.nodeVersions, environment: run.environment, resources: run.resources, parameters: run.parameters, datasets: run.datasetVersions }, null, 2)}</pre></details>
            <details><summary>Output artifacts</summary>{Object.keys(run.outputArtifacts).length === 0 ? <p>No output artifacts.</p> : <ul>{Object.entries(run.outputArtifacts).map(([name, hash]) => <li key={name}><strong>{name}</strong><code>{hash}</code></li>)}</ul>}</details>
          </div>
          <footer className="research-run__footer"><button type="button" className="secondary-button" onClick={() => setManifestRunId(run.id)}>View reproducibility manifest</button></footer>
        </article>
      ))}</div>
      {runs.length > PAGE_SIZE && <div className="progressive-list"><span>Showing {visibleRuns.length} of {runs.length} runs</span>{visibleRuns.length < runs.length && <button type="button" className="secondary-button" onClick={() => setVisibleCount((current) => Math.min(current + PAGE_SIZE, runs.length))}>Show {Math.min(PAGE_SIZE, runs.length - visibleRuns.length)} more</button>}</div>}
      {runs.length === 0 && !error && <div className="workflow-empty"><strong>No research runs</strong><p>Create a node-context run from a trainable inspector.</p></div>}
      <ReproducibilityManifestDialog accessToken={accessToken} runId={manifestRunId} onClose={() => setManifestRunId(null)} />
    </section>
  );
}
