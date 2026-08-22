import { useEffect, useState } from 'react';
import { readRegisteredModels, searchResearchRuns } from '../services/research-service';
import type { RegisteredModel, ResearchRun } from '../types/research';

interface ResearchPageProps {
  accessToken: string;
  initialRuns?: ResearchRun[];
  initialModels?: RegisteredModel[];
}

export function ResearchPage({ accessToken, initialRuns = [], initialModels = [] }: ResearchPageProps) {
  const [runs, setRuns] = useState(initialRuns);
  const [models, setModels] = useState(initialModels);
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState<string[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    if (initialRuns.length > 0) return;
    searchResearchRuns(accessToken).then(setRuns).catch((loadError: unknown) => {
      setError(loadError instanceof Error ? loadError.message : 'Research runs could not be loaded.');
    });
  }, [accessToken, initialRuns.length]);

  useEffect(() => {
    if (initialModels.length > 0) return;
    readRegisteredModels(accessToken).then(setModels).catch((loadError: unknown) => {
      setError(loadError instanceof Error ? loadError.message : 'Registered models could not be loaded.');
    });
  }, [accessToken, initialModels.length]);

  const search = async () => {
    setError('');
    try { setRuns(await searchResearchRuns(accessToken, query)); }
    catch (searchError) { setError(searchError instanceof Error ? searchError.message : 'Research search failed.'); }
  };
  const selectedRuns = runs.filter((run) => selected.includes(run.id));

  return (
    <section className="research-page" aria-label="Research workspace">
      <header className="research-page__header">
        <div><span className="overline">Reproducible experiments</span><h1>Research runs</h1><p>Compare metrics, inspect lineage, browse immutable artifacts, and diagnose failures.</p></div>
        <div className="research-search"><input aria-label="Search research runs" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Run, experiment, code revision" /><button type="button" onClick={() => void search()}>Search</button></div>
      </header>
      {error && <div className="studio-message studio-message--error" role="alert">{error}</div>}
      <div className="research-summary"><span><small>Runs</small><strong>{runs.length}</strong></span><span><small>Completed</small><strong>{runs.filter((run) => run.status === 'completed').length}</strong></span><span><small>Failed</small><strong>{runs.filter((run) => run.status === 'failed').length}</strong></span><button type="button" disabled={selected.length < 2}>Compare selected</button></div>
      {selectedRuns.length >= 2 && <section className="research-comparison"><h2>Metric comparison</h2>{selectedRuns.map((run) => <article key={run.id}><strong>{run.id}</strong>{Object.entries(run.metrics).map(([key, value]) => <span key={key}>{key.toLocaleUpperCase()} {value}</span>)}</article>)}</section>}
      <div className="research-run-list">{runs.map((run) => (
        <article className={`research-run research-run--${run.status}`} key={run.id}>
          <header><label><input type="checkbox" checked={selected.includes(run.id)} onChange={(event) => setSelected((current) => event.target.checked ? [...current, run.id] : current.filter((id) => id !== run.id))} />Compare</label><strong>{run.id}</strong><span>{run.status}</span></header>
          <div className="research-run__lineage"><span>Code <code>{run.codeRevision}</code></span><span>Target {run.executionTarget}</span><span>Seed {Object.values(run.randomSeeds)[0] ?? '—'}</span></div>
          <div className="research-run__metrics">{Object.entries(run.metrics).map(([key, value]) => <span key={key}><small>{key.toLocaleUpperCase()}</small><strong>{value}</strong></span>)}</div>
          <details><summary>Parameters and environment</summary><pre>{JSON.stringify({ nodeVersions: run.nodeVersions, environment: run.environment, resources: run.resources, parameters: run.parameters, datasets: run.datasetVersions }, null, 2)}</pre></details>
          <details><summary>Artifacts</summary>{Object.keys(run.outputArtifacts).length === 0 ? <p>No output artifacts.</p> : <ul>{Object.entries(run.outputArtifacts).map(([name, hash]) => <li key={name}><strong>{name}</strong><code>{hash}</code></li>)}</ul>}</details>
          {run.error && <div className="research-run__error" role="alert"><strong>Failure diagnostics</strong><p>{run.error}</p></div>}
        </article>
      ))}</div>
      {runs.length === 0 && !error && <div className="workflow-empty"><strong>No research runs</strong><p>Create a node-context run from a trainable inspector.</p></div>}
      <section className="research-models" aria-label="Registered models">
        <header><span className="overline">Registry</span><h2>Model versions</h2><p>Only validated aliases with verified artifacts can be bound to a workflow node.</p></header>
        {models.map((model) => (
          <article className="research-run" key={model.name}>
            <header><strong>{model.name}</strong><span>{Object.entries(model.aliases).map(([alias, version]) => `${alias} → v${version}`).join(' · ') || 'No promoted alias'}</span></header>
            <p>{model.description || 'No model description.'}</p>
            {model.versions.map((version) => (
              <details key={version.version}>
                <summary>v{version.version} · {version.artifactVerified ? 'artifact verified' : 'artifact unavailable'} · run {version.runId}</summary>
                <p><code>{version.artifactSha256}</code></p>
                <pre>{JSON.stringify({ metrics: version.validationEvidence, compatibility: version.compatibility }, null, 2)}</pre>
                {version.deepLearningContract && <div><strong>External deep-learning artifact</strong><p>{version.deepLearningContract.format} · {version.deepLearningContract.runtime} {version.deepLearningContract.runtimeVersion}</p><p>{version.deepLearningContract.inputSchema.length} input tensor(s) → {version.deepLearningContract.outputSchema.length} output tensor(s)</p></div>}
              </details>
            ))}
          </article>
        ))}
        {models.length === 0 && <div className="workflow-empty"><strong>No registered models</strong><p>Create a version from a completed research run and promote a validated candidate.</p></div>}
      </section>
    </section>
  );
}
