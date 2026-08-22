import { useEffect, useState } from 'react';
import { promoteModel, readRegisteredModels, rollbackModel } from '../services/research-service';
import type { ModelAlias, ModelPromotionEvent, RegisteredModel } from '../types/research';

interface ModelsPageProps {
  accessToken: string;
  initialModels?: RegisteredModel[];
}

export function ModelsPage({ accessToken, initialModels = [] }: ModelsPageProps) {
  const [models, setModels] = useState(initialModels);
  const [error, setError] = useState('');
  const [actionError, setActionError] = useState('');
  const [actionNotice, setActionNotice] = useState('');
  const [actionBusy, setActionBusy] = useState('');
  const [reason, setReason] = useState('');
  const [selectedAction, setSelectedAction] = useState<{ modelName: string; version: number; alias: ModelAlias } | null>(null);
  const [lastEvent, setLastEvent] = useState<ModelPromotionEvent | null>(null);

  useEffect(() => {
    if (initialModels.length > 0) return;
    readRegisteredModels(accessToken).then(setModels).catch((loadError: unknown) => {
      setError(loadError instanceof Error ? loadError.message : 'Registered models could not be loaded.');
    });
  }, [accessToken, initialModels.length]);

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
      const event = selectedAction.alias === 'rollback'
        ? await rollbackModel(accessToken, selectedAction.modelName, 'champion', trimmedReason)
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

  return (
    <section className="research-page models-page" aria-label="Models workspace">
      <header className="research-page__header">
        <div>
          <span className="overline">Controlled model registry</span>
          <h1>Models</h1>
          <p>Browse immutable versions, lineage, compatibility, verified artifacts, and promoted aliases.</p>
        </div>
      </header>
      {error && <div className="studio-message studio-message--error" role="alert">{error}</div>}
      {actionError && <div className="studio-message studio-message--error" role="alert">{actionError}</div>}
      {actionNotice && <div className="studio-message" role="status">{actionNotice}</div>}
      {lastEvent && <details className="research-event" open><summary>Latest model audit event</summary><p><strong>{lastEvent.action}</strong> · {lastEvent.alias} · v{lastEvent.nextVersion}</p><p>Reason: {lastEvent.reason}</p></details>}
      {selectedAction && <form className="research-action-form" onSubmit={(event) => { event.preventDefault(); void submitAction(); }}>
        <h2>{selectedAction.alias === 'rollback' ? 'Rollback model alias' : `Promote version ${selectedAction.version}`}</h2>
        <label className="workflow-field"><span>Reason for this action</span><textarea aria-label="Reason for this action" value={reason} onChange={(event) => setReason(event.target.value)} required /></label>
        <div><button type="submit" disabled={Boolean(actionBusy)}>{actionBusy ? 'Working…' : 'Confirm action'}</button><button type="button" className="secondary-button" onClick={() => { setSelectedAction(null); setReason(''); setActionError(''); }}>Cancel</button></div>
      </form>}
      <div className="research-summary">
        <span><small>Models</small><strong>{models.length}</strong></span>
        <span><small>Versions</small><strong>{models.reduce((total, model) => total + model.versions.length, 0)}</strong></span>
        <span><small>Promoted aliases</small><strong>{models.reduce((total, model) => total + Object.keys(model.aliases).length, 0)}</strong></span>
      </div>
      <div className="research-models" aria-label="Registered models">
        {models.map((model) => (
          <article className="research-run" key={model.name}>
            <header>
              <strong>{model.name}</strong>
              <span>{Object.entries(model.aliases).map(([alias, version]) => `${alias} → v${version}`).join(' · ') || 'No promoted alias'}</span>
            </header>
            <p>{model.description || 'No model description.'}</p>
            {model.versions.map((version) => (
              <details key={version.version} open>
                <summary>v{version.version} · {version.artifactVerified ? 'artifact verified' : 'artifact unavailable'}</summary>
                <div className="research-run__lineage">
                  <span>Run <code>{version.runId}</code></span>
                  <span>Task {version.compatibility.task || 'unknown'}</span>
                  <span>Framework {version.compatibility.framework || 'unknown'}</span>
                  <span>Status {version.compatibility.status || 'unknown'}</span>
                </div>
                <p>Artifact SHA-256 <code>{version.artifactSha256}</code></p>
                <pre>{JSON.stringify({ validation: version.validationEvidence, compatibility: version.compatibility }, null, 2)}</pre>
                <div className="research-action-row">
                  <button type="button" onClick={() => setSelectedAction({ modelName: model.name, version: version.version, alias: 'candidate' })}>Promote to candidate</button>
                  <button type="button" onClick={() => setSelectedAction({ modelName: model.name, version: version.version, alias: 'champion' })}>Promote to champion</button>
                  {model.aliases.champion && <button type="button" className="secondary-button" onClick={() => setSelectedAction({ modelName: model.name, version: model.aliases.champion ?? version.version, alias: 'rollback' })}>Rollback champion</button>}
                </div>
              </details>
            ))}
          </article>
        ))}
        {models.length === 0 && <div className="workflow-empty"><strong>No registered models</strong><p>Create a version from a completed research run and promote a validated candidate.</p></div>}
      </div>
    </section>
  );
}
