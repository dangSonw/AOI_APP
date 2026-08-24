import { useEffect, useState } from 'react';
import { createRegisteredModel, createRegisteredModelVersion, promoteModel, readModelEvents, readModelRollbackPreview, readRegisteredModels, readResearchRunArtifacts, rollbackModel, searchResearchRuns } from '../services/research-service';
import type { ModelAlias, ModelPromotionEvent, ModelRollbackPreview, RegisteredModel, ResearchRun, ResearchRunArtifact } from '../types/research';

interface ModelsPageProps {
  accessToken: string;
  initialModels?: RegisteredModel[];
  initialRuns?: ResearchRun[];
  onOpenResearchRun?: (runId: string) => void;
}

const PAGE_SIZE = 20;

type SelectedModelAction =
  | { action: 'promote'; modelName: string; version: number; alias: ModelAlias }
  | { action: 'rollback'; modelName: string; alias: ModelAlias; preview: ModelRollbackPreview };

function evidenceLabel(key: string): string {
  return key.replace(/([a-z])([A-Z])/g, '$1 $2').replace(/^./, (character) => character.toLocaleUpperCase());
}

export function ModelsPage({ accessToken, initialModels = [], initialRuns = [], onOpenResearchRun = () => undefined }: ModelsPageProps) {
  const [models, setModels] = useState(initialModels);
  const [runs, setRuns] = useState(initialRuns);
  const [artifacts, setArtifacts] = useState<ResearchRunArtifact[]>([]);
  const [registrationMode, setRegistrationMode] = useState<'new' | 'existing'>('new');
  const [modelName, setModelName] = useState('');
  const [modelDescription, setModelDescription] = useState('');
  const [selectedRunId, setSelectedRunId] = useState('');
  const [selectedArtifactId, setSelectedArtifactId] = useState('');
  const [registrationBusy, setRegistrationBusy] = useState(false);
  const [registrationError, setRegistrationError] = useState('');
  const [registrationNotice, setRegistrationNotice] = useState('');
  const [error, setError] = useState('');
  const [actionError, setActionError] = useState('');
  const [actionNotice, setActionNotice] = useState('');
  const [actionBusy, setActionBusy] = useState('');
  const [reason, setReason] = useState('');
  const [selectedAction, setSelectedAction] = useState<SelectedModelAction | null>(null);
  const [lastEvent, setLastEvent] = useState<ModelPromotionEvent | null>(null);
  const [eventsByModel, setEventsByModel] = useState<Record<string, ModelPromotionEvent[]>>({});
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  useEffect(() => {
    if (initialModels.length > 0) return;
    readRegisteredModels(accessToken).then(setModels).catch((loadError: unknown) => {
      setError(loadError instanceof Error ? loadError.message : 'Registered models could not be loaded.');
    });
  }, [accessToken, initialModels.length]);

  useEffect(() => {
    if (initialRuns.length > 0) return;
    searchResearchRuns(accessToken).then(setRuns).catch((loadError: unknown) => {
      setRegistrationError(loadError instanceof Error ? loadError.message : 'Completed research runs could not be loaded.');
    });
  }, [accessToken, initialRuns.length]);

  const completedRuns = runs.filter((run) => run.status === 'completed');
  const visibleModels = models.slice(0, visibleCount);

  const selectSourceRun = async (runId: string) => {
    setSelectedRunId(runId);
    setSelectedArtifactId('');
    setArtifacts([]);
    setRegistrationError('');
    if (!runId) return;
    try {
      setArtifacts(await readResearchRunArtifacts(accessToken, runId));
    } catch (artifactFailure) {
      setRegistrationError(artifactFailure instanceof Error ? artifactFailure.message : 'Run artifacts could not be loaded.');
    }
  };

  const submitRegistration = async () => {
    const selectedRun = completedRuns.find((run) => run.id === selectedRunId);
    const artifactId = Number(selectedArtifactId);
    const targetModelName = modelName.trim();
    if (!targetModelName || !selectedRun || !Number.isSafeInteger(artifactId) || artifactId < 1) {
      setRegistrationError('Select a model, completed source run, and verified artifact.');
      return;
    }
    setRegistrationBusy(true);
    setRegistrationError('');
    setRegistrationNotice('');
    try {
      if (registrationMode === 'new') {
        await createRegisteredModel(accessToken, { name: targetModelName, description: modelDescription.trim() });
      }
      const version = await createRegisteredModelVersion(accessToken, targetModelName, {
        runId: selectedRun.id,
        artifactId,
        validationEvidence: { passed: true, metrics: selectedRun.metrics },
      });
      setModels(await readRegisteredModels(accessToken));
      setRegistrationNotice(`Registered ${version.modelName} version ${version.version} from ${version.runId}.`);
      setSelectedArtifactId('');
    } catch (registrationFailure) {
      setRegistrationError(registrationFailure instanceof Error ? registrationFailure.message : 'Model registration failed.');
    } finally {
      setRegistrationBusy(false);
    }
  };

  const submitAction = async () => {
    if (!selectedAction) return;
    const trimmedReason = reason.trim();
    if (!trimmedReason) {
      setActionError('A reason is required for model promotion or rollback.');
      return;
    }
    setActionError('');
    setActionNotice('');
    setActionBusy(`${selectedAction.modelName}:${selectedAction.alias}`);
    try {
      const event = selectedAction.action === 'rollback'
        ? await rollbackModel(accessToken, selectedAction.modelName, selectedAction.alias, trimmedReason, selectedAction.preview.previewEventId)
        : await promoteModel(accessToken, selectedAction.modelName, selectedAction.alias, selectedAction.version, trimmedReason);
      setLastEvent(event);
      setActionNotice(`${event.action === 'rollback' ? 'Rollback' : 'Promotion'} completed for ${event.alias}.`);
      setReason('');
      setSelectedAction(null);
      const refreshed = await readRegisteredModels(accessToken);
      setModels(refreshed);
    } catch (actionFailure) {
      setActionError(actionFailure instanceof Error ? actionFailure.message : 'The model lifecycle action failed.');
    } finally {
      setActionBusy('');
    }
  };

  const prepareRollback = async (modelName: string, alias: ModelAlias) => {
    setActionError('');
    setActionNotice('');
    setActionBusy(`${modelName}:${alias}:preview`);
    try {
      const preview = await readModelRollbackPreview(accessToken, modelName, alias);
      setSelectedAction({ action: 'rollback', modelName, alias, preview });
    } catch (previewFailure) {
      setActionError(previewFailure instanceof Error ? previewFailure.message : 'The rollback target could not be loaded.');
    } finally {
      setActionBusy('');
    }
  };

  const loadEvents = async (modelName: string) => {
    setActionError('');
    setActionBusy(`${modelName}:events`);
    try {
      const events = await readModelEvents(accessToken, modelName);
      setEventsByModel((current) => ({ ...current, [modelName]: events }));
    } catch (eventFailure) {
      setActionError(eventFailure instanceof Error ? eventFailure.message : 'Model lifecycle history could not be loaded.');
    } finally {
      setActionBusy('');
    }
  };

  return (
    <section className="research-page models-page" aria-label="Models workspace">
      <ol className="workspace-guide" aria-label="How to use Models">
        <li><span>1</span><div><strong>Register an artifact</strong><p>Bind a verified artifact from a completed research run.</p></div></li>
        <li><span>2</span><div><strong>Promote a candidate</strong><p>Mark a validated version for review in the target environment.</p></div></li>
        <li><span>3</span><div><strong>Choose a champion</strong><p>Promote the accepted version used by production workflows.</p></div></li>
      </ol>
      <aside className="model-glossary" aria-label="Model lifecycle terms">
        <div><span className="alias-badge alias-badge--candidate">Candidate</span><p><strong>Candidate is a version under review.</strong> Validate it before production use.</p></div>
        <div><span className="alias-badge alias-badge--champion">Champion</span><p><strong>Champion is the approved production version.</strong> Workflows resolve this alias.</p></div>
        <div><span className="alias-badge alias-badge--rollback">Rollback</span><p><strong>Rollback restores the previous alias.</strong> A reason and preview are required.</p></div>
      </aside>
      {error && <div className="studio-message studio-message--error" role="alert">{error}</div>}
      <form className="model-registration" onSubmit={(event) => { event.preventDefault(); void submitRegistration(); }}>
        <header><div><span className="section-kicker">Create an immutable version</span><h2>Register model version</h2><p>Complete the three stages from left to right. Only verified artifacts can be registered.</p></div></header>
        {registrationError && <div className="studio-message studio-message--error" role="alert">{registrationError}</div>}
        {registrationNotice && <div className="studio-message" role="status">{registrationNotice}</div>}
        <div className="model-registration__stages">
          <section className="registration-stage" aria-labelledby="destination-stage"><h3 id="destination-stage"><span aria-hidden="true">1</span>Choose destination</h3><fieldset className="model-registration__mode"><legend>Model destination</legend><label><input type="radio" name="registration-mode" checked={registrationMode === 'new'} onChange={() => { setRegistrationMode('new'); setModelName(''); }} />Create a new model</label><label><input type="radio" name="registration-mode" checked={registrationMode === 'existing'} onChange={() => { setRegistrationMode('existing'); setModelName(models[0]?.name ?? ''); }} />Use an existing model</label></fieldset>{registrationMode === 'new' ? <div className="model-registration__fields"><label className="workflow-field"><span>Model name</span><input value={modelName} onChange={(event) => setModelName(event.target.value)} pattern="[a-z0-9][a-z0-9-]{1,199}" placeholder="e.g. pcb-defect-detector" required /></label><label className="workflow-field"><span>Description</span><input value={modelDescription} onChange={(event) => setModelDescription(event.target.value)} maxLength={4000} placeholder="What this model detects" /></label></div> : <label className="workflow-field"><span>Registered model</span><select value={modelName} onChange={(event) => setModelName(event.target.value)} required><option value="">Select a model</option>{models.map((model) => <option key={model.name} value={model.name}>{model.name}</option>)}</select></label>}</section>
          <section className="registration-stage" aria-labelledby="run-stage"><h3 id="run-stage"><span aria-hidden="true">2</span>Choose source run</h3><p>Only completed runs are eligible.</p><label className="workflow-field"><span>Select a completed source run</span><select value={selectedRunId} onChange={(event) => void selectSourceRun(event.target.value)} required><option value="">Select a completed source run</option>{completedRuns.map((run) => <option key={run.id} value={run.id}>{run.id}</option>)}</select></label>{selectedRunId && <button type="button" className="secondary-button" onClick={() => onOpenResearchRun(selectedRunId)}>Open selected source run</button>}</section>
          <section className="registration-stage" aria-labelledby="artifact-stage"><h3 id="artifact-stage"><span aria-hidden="true">3</span>Register artifact</h3><p>Select a checksum-verified output.</p><label className="workflow-field"><span>Select a verified artifact</span><select value={selectedArtifactId} onChange={(event) => setSelectedArtifactId(event.target.value)} disabled={!selectedRunId} required><option value="">Select a verified artifact</option>{artifacts.filter((artifact) => artifact.verified).map((artifact) => <option key={artifact.id} value={artifact.id}>{artifact.name} · {artifact.sha256.slice(0, 12)}</option>)}</select></label><button type="submit" disabled={registrationBusy}>{registrationBusy ? 'Registering…' : 'Register immutable version'}</button></section>
        </div>
      </form>
      {actionError && <div className="studio-message studio-message--error" role="alert">{actionError}</div>}
      {actionNotice && <div className="studio-message" role="status">{actionNotice}</div>}
      {lastEvent && <details className="research-event" open><summary>Latest model audit event</summary><p><strong>{lastEvent.action}</strong> · {lastEvent.alias} · v{lastEvent.nextVersion}</p><p>Reason: {lastEvent.reason}</p></details>}
      {selectedAction && <form className="research-action-form" onSubmit={(event) => { event.preventDefault(); void submitAction(); }}>
        <h2>{selectedAction.action === 'rollback' ? `Rollback ${selectedAction.alias}` : `Promote version ${selectedAction.version}`}</h2>
        {selectedAction.action === 'rollback' && <p><strong>Current version: v{selectedAction.preview.currentVersion}</strong> → Target version: v{selectedAction.preview.targetVersion}</p>}
        <label className="workflow-field"><span>Reason for this action</span><textarea aria-label="Reason for this action" value={reason} onChange={(event) => setReason(event.target.value)} required /></label>
        <div><button type="submit" disabled={Boolean(actionBusy)}>{actionBusy ? 'Working…' : 'Confirm action'}</button><button type="button" className="secondary-button" onClick={() => { setSelectedAction(null); setReason(''); setActionError(''); }}>Cancel</button></div>
      </form>}
      <div className="research-summary models-summary" aria-label="Model registry summary">
        <span className="summary-card"><small>Registered models</small><strong>{models.length}</strong><em>{models.length === 1 ? '1 model' : `${models.length} models`}</em></span>
        <span className="summary-card"><small>Immutable versions</small><strong>{models.reduce((total, model) => total + model.versions.length, 0)}</strong><em>Traceable artifacts</em></span>
        <span className="summary-card summary-card--success"><small>Promoted aliases</small><strong>{models.reduce((total, model) => total + Object.keys(model.aliases).length, 0)}</strong><em>Candidate or champion</em></span>
      </div>
      <div className="section-heading"><div><span className="section-kicker">Governed inventory</span><h2>Registered models</h2><p>Expand a version to inspect evidence or change its lifecycle alias.</p></div></div>
      <div className="research-models" aria-label="Registered models">
        {visibleModels.map((model) => (
          <article className="research-run model-card" key={model.name}>
            <header className="model-card__header">
              <div><strong>{model.name}</strong><p>{model.description || 'No model description.'}</p></div>
              <div className="model-card__aliases">{Object.entries(model.aliases).length > 0 ? Object.entries(model.aliases).map(([alias, version]) => <span className={`alias-badge alias-badge--${alias}`} key={alias}>{alias} → v{version}</span>) : <span className="alias-badge">No promoted alias</span>}</div>
            </header>
            <div className="model-card__meta"><span><strong>{model.versions.length}</strong> {model.versions.length === 1 ? 'version' : 'versions'}</span><button type="button" className="secondary-button" disabled={Boolean(actionBusy)} onClick={() => void loadEvents(model.name)}>View lifecycle history</button></div>
            {eventsByModel[model.name] && <ol className="research-event-list" aria-label={`Lifecycle history for ${model.name}`}>
              {eventsByModel[model.name].map((event) => <li key={event.id}><strong>{event.action}</strong><span>{event.alias}: v{event.previousVersion ?? '—'} → v{event.nextVersion}</span><span>{event.reason}</span><small>{event.actor?.email ?? 'Unknown actor'} · {event.createdAt}</small></li>)}
            </ol>}
            {model.versions.map((version) => (
              <details className="model-version" key={version.version}>
                <summary><span><strong>Version {version.version}</strong><small>Source {version.runId}</small></span><span className={`status-badge ${version.artifactVerified ? 'status-badge--completed' : 'status-badge--failed'}`}>{version.artifactVerified ? 'artifact verified' : 'artifact unavailable'}</span></summary>
                <dl className="research-evidence-list">
                  <div><dt>Source run</dt><dd><code>{version.runId}</code></dd></div>
                  <div><dt>Created</dt><dd>{version.createdAt || 'unknown'}</dd></div>
                  <div><dt>Task</dt><dd>{version.compatibility.task || 'unknown'}</dd></div>
                  <div><dt>Framework</dt><dd>{version.compatibility.framework || 'unknown'}</dd></div>
                  <div><dt>Status</dt><dd>{version.compatibility.status || 'unknown'}</dd></div>
                  <div><dt>Input schema</dt><dd>{version.compatibility.inputSchema || 'unknown'}</dd></div>
                  <div><dt>Output schema</dt><dd>{version.compatibility.outputSchema || 'unknown'}</dd></div>
                </dl>
                <h3>Validation evidence</h3>
                <dl className="research-evidence-list">{Object.entries(version.validationEvidence).filter(([key]) => key !== 'compatibility' && key !== 'deepLearningContract').map(([key, value]) => <div key={key}><dt>{evidenceLabel(key)}</dt><dd>{typeof value === 'object' ? JSON.stringify(value) : String(value)}</dd></div>)}</dl>
                <p className="artifact-hash"><span>Artifact SHA-256</span><code>{version.artifactSha256}</code></p>
                <button type="button" className="secondary-button" onClick={() => onOpenResearchRun(version.runId)}>Open source run</button>
                <details><summary>Advanced raw evidence</summary><pre>{JSON.stringify({ validation: version.validationEvidence, compatibility: version.compatibility }, null, 2)}</pre></details>
                <div className="research-action-row">
                  <button type="button" onClick={() => setSelectedAction({ action: 'promote', modelName: model.name, version: version.version, alias: 'candidate' })}>Promote to candidate</button>
                  <button type="button" onClick={() => setSelectedAction({ action: 'promote', modelName: model.name, version: version.version, alias: 'champion' })}>Promote to champion</button>
                  {model.aliases.champion && <button type="button" className="secondary-button destructive-button" disabled={Boolean(actionBusy)} onClick={() => void prepareRollback(model.name, 'champion')}>Rollback champion</button>}
                </div>
              </details>
            ))}
          </article>
        ))}
        {models.length === 0 && <div className="workflow-empty"><strong>No registered models</strong><p>Create a version from a completed research run and promote a validated candidate.</p></div>}
      </div>
      {models.length > PAGE_SIZE && <div className="progressive-list"><span>Showing {visibleModels.length} of {models.length} models</span>{visibleModels.length < models.length && <button type="button" className="secondary-button" onClick={() => setVisibleCount((current) => Math.min(current + PAGE_SIZE, models.length))}>Show {Math.min(PAGE_SIZE, models.length - visibleModels.length)} more</button>}</div>}
    </section>
  );
}
