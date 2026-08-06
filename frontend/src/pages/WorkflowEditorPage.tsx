import { useCallback, useEffect, useMemo, useState } from 'react';
import { AlgorithmCatalog } from '../components/workflow/AlgorithmCatalog';
import { ExecutionOrderRail } from '../components/workflow/ExecutionOrderRail';
import { NodeInspector } from '../components/workflow/NodeInspector';
import { WorkflowCanvas } from '../components/workflow/WorkflowCanvas';
import { ApiError } from '../services/api-client';
import { readAlgorithmCatalog, readWorkflow, saveWorkflow } from '../services/workflow-service';
import type {
  AlgorithmDefinition,
  ConnectionDraft,
  Workflow,
  WorkflowNode,
} from '../types/workflow';
import {
  addConnection,
  createNodeFromDefinition,
  isWorkflowDirty,
  stableTopologicalOrder,
  validateDraft,
} from '../utils/workflow-graph';


interface WorkflowEditorPageProps {
  accessToken: string;
  recipeSlug: string;
  onBack: () => void;
  onDirtyChange: (isDirty: boolean) => void;
  onWorkflowSaved: (workflow: Workflow) => void;
}

export function WorkflowEditorPage({
  accessToken,
  recipeSlug,
  onBack,
  onDirtyChange,
  onWorkflowSaved,
}: WorkflowEditorPageProps) {
  const [catalog, setCatalog] = useState<AlgorithmDefinition[]>([]);
  const [savedWorkflow, setSavedWorkflow] = useState<Workflow | null>(null);
  const [draftWorkflow, setDraftWorkflow] = useState<Workflow | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [hasConflict, setHasConflict] = useState(false);

  const loadEditor = useCallback(async () => {
    setIsLoading(true);
    setError('');
    setNotice('');
    setHasConflict(false);
    try {
      const [nextCatalog, nextWorkflow] = await Promise.all([
        readAlgorithmCatalog(accessToken),
        readWorkflow(accessToken, recipeSlug),
      ]);
      setCatalog(nextCatalog);
      setSavedWorkflow(nextWorkflow);
      setDraftWorkflow(structuredClone(nextWorkflow));
      setSelectedNodeId(nextWorkflow.nodes[0]?.id ?? null);
      onWorkflowSaved(nextWorkflow);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'The workflow editor could not be loaded.');
    } finally {
      setIsLoading(false);
    }
  }, [accessToken, recipeSlug, onWorkflowSaved]);

  useEffect(() => {
    void loadEditor();
  }, [loadEditor]);

  const isDirty = isWorkflowDirty(savedWorkflow, draftWorkflow);
  useEffect(() => {
    onDirtyChange(isDirty);
    return () => onDirtyChange(false);
  }, [isDirty, onDirtyChange]);

  useEffect(() => {
    const warnBeforeUnload = (event: BeforeUnloadEvent) => {
      if (!isDirty) return;
      event.preventDefault();
      event.returnValue = '';
    };
    window.addEventListener('beforeunload', warnBeforeUnload);
    return () => window.removeEventListener('beforeunload', warnBeforeUnload);
  }, [isDirty]);

  const issues = useMemo(
    () => draftWorkflow ? validateDraft(draftWorkflow, catalog) : [],
    [catalog, draftWorkflow],
  );
  const selectedNode = draftWorkflow?.nodes.find((node) => node.id === selectedNodeId) ?? null;
  const selectedDefinition = catalog.find((definition) => definition.id === selectedNode?.algorithmId) ?? null;
  const canSave = Boolean(draftWorkflow && isDirty && !isLoading && !isSaving && issues.length === 0);

  const updateDraft = (updater: (workflow: Workflow) => Workflow) => {
    setDraftWorkflow((current) => current ? updater(current) : current);
    setNotice('');
    setError('');
    setHasConflict(false);
  };

  const addAlgorithm = (definition: AlgorithmDefinition, position = { x: 80, y: 80 }) => {
    const node = createNodeFromDefinition(definition, position);
    updateDraft((workflow) => ({
      ...workflow,
      nodes: [...workflow.nodes, node],
      executionOrder: [...workflow.executionOrder, node.id],
    }));
    setSelectedNodeId(node.id);
  };

  const removeNode = (nodeId: string) => {
    if (!draftWorkflow) return;
    const affected = draftWorkflow.connections.filter((connection) => connection.sourceNodeId === nodeId || connection.targetNodeId === nodeId);
    if (affected.length > 0 && !window.confirm(`Remove this node and ${affected.length} dependent connection${affected.length === 1 ? '' : 's'}?`)) {
      return;
    }
    updateDraft((workflow) => ({
      ...workflow,
      nodes: workflow.nodes.filter((node) => node.id !== nodeId),
      connections: workflow.connections.filter((connection) => connection.sourceNodeId !== nodeId && connection.targetNodeId !== nodeId),
      executionOrder: workflow.executionOrder.filter((id) => id !== nodeId),
    }));
    setSelectedNodeId((current) => current === nodeId ? null : current);
  };

  const handleSave = async () => {
    if (!draftWorkflow || !canSave) return;
    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      const saved = await saveWorkflow(accessToken, draftWorkflow);
      setSavedWorkflow(saved);
      setDraftWorkflow(structuredClone(saved));
      onWorkflowSaved(saved);
      setNotice(`Workflow saved as revision ${saved.revision}.`);
    } catch (saveError) {
      if (saveError instanceof ApiError && saveError.status === 409) {
        setHasConflict(true);
        setError('A newer workflow revision is available. Your unsaved draft is preserved.');
      } else {
        setError(saveError instanceof Error ? saveError.message : 'The workflow could not be saved.');
      }
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading && !draftWorkflow) {
    return <section className="workflow-editor workflow-editor--loading" aria-busy="true"><strong>Loading workflow editor…</strong></section>;
  }
  if (!draftWorkflow) {
    return (
      <section className="workflow-editor workflow-editor--loading">
        <p className="studio-message studio-message--error" role="alert">{error || 'The workflow editor is unavailable.'}</p>
        <button type="button" className="primary-button" onClick={() => void loadEditor()}>Retry editor</button>
      </section>
    );
  }

  return (
    <section className="workflow-editor" aria-busy={isLoading || isSaving}>
      <header className="workflow-editor__header">
        <div className="workflow-editor__identity">
          <button type="button" className="text-action" onClick={onBack}>← Back to workspace</button>
          <span className="overline">Recipe workflow</span>
          <h1>{draftWorkflow.recipeName}</h1>
          <p>Configuration graph · Revision {savedWorkflow?.revision ?? draftWorkflow.revision} · Schema v{draftWorkflow.version}</p>
        </div>
        <div className="workflow-editor__status">
          <span className={`workflow-state ${issues.length > 0 ? 'workflow-state--warning' : isDirty ? 'workflow-state--dirty' : 'workflow-state--valid'}`}>
            {issues.length > 0 ? `${issues.length} issue${issues.length === 1 ? '' : 's'}` : isDirty ? 'Unsaved changes' : 'Saved and valid'}
          </span>
          <button type="button" className="secondary-button" onClick={() => updateDraft((workflow) => ({ ...workflow, executionOrder: stableTopologicalOrder(workflow) }))}>Auto order</button>
          <button type="button" className="primary-button" disabled={!canSave} onClick={() => void handleSave()}>{isSaving ? 'Saving…' : 'Save changes'}</button>
        </div>
      </header>

      <div className="workflow-editor__messages" aria-live="polite">
        {error && <div className="studio-message studio-message--error" role="alert"><span>{error}</span>{hasConflict && <button type="button" onClick={() => void loadEditor()}>Reload server version</button>}</div>}
        {notice && <p className="studio-message studio-message--success">{notice}</p>}
        {issues.length > 0 && (
          <details className="workflow-issues">
            <summary>Review {issues.length} workflow issue{issues.length === 1 ? '' : 's'}</summary>
            <ul>{issues.map((issue, index) => <li key={`${issue.code}-${issue.nodeId ?? issue.connectionId ?? index}`}><code>{issue.code}</code> {issue.message}</li>)}</ul>
          </details>
        )}
      </div>

      <div className="workflow-editor__grid">
        <AlgorithmCatalog catalog={catalog} onAdd={(definition) => addAlgorithm(definition)} onRetry={() => void loadEditor()} />
        <main className="workflow-graph-region">
          <header className="workflow-region-heading"><div><span className="overline">Typed DAG</span><strong>Inspection graph</strong></div><span>{draftWorkflow.nodes.length} nodes · {draftWorkflow.connections.length} edges</span></header>
          <WorkflowCanvas
            workflow={draftWorkflow}
            catalog={catalog}
            selectedNodeId={selectedNodeId}
            onSelectNode={setSelectedNodeId}
            onAddAlgorithm={addAlgorithm}
            onMoveNode={(nodeId, position) => updateDraft((workflow) => ({ ...workflow, nodes: workflow.nodes.map((node) => node.id === nodeId ? { ...node, position } : node) }))}
            onConnect={(connection: ConnectionDraft) => updateDraft((workflow) => addConnection(workflow, connection))}
            onRemoveNode={removeNode}
            onRemoveConnection={(connectionId) => updateDraft((workflow) => ({ ...workflow, connections: workflow.connections.filter((connection) => connection.id !== connectionId) }))}
            onConnectionRejected={setError}
          />
        </main>
        <NodeInspector
          node={selectedNode}
          definition={selectedDefinition}
          onChange={(nextNode: WorkflowNode) => updateDraft((workflow) => ({ ...workflow, nodes: workflow.nodes.map((node) => node.id === nextNode.id ? nextNode : node) }))}
        />
      </div>
      <ExecutionOrderRail
        workflow={draftWorkflow}
        catalog={catalog}
        issues={issues}
        onChange={(executionOrder) => updateDraft((workflow) => ({ ...workflow, executionOrder }))}
        onAutoOrder={() => updateDraft((workflow) => ({ ...workflow, executionOrder: stableTopologicalOrder(workflow) }))}
        onSelectNode={setSelectedNodeId}
      />
    </section>
  );
}