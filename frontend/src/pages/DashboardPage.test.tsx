import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { createDefaultPreferences } from '../utils/workstation-preferences';
import type { InspectionRun } from '../types/inspection';
import type { Workflow } from '../types/workflow';
import { DashboardPage } from './DashboardPage';

const workflow: Workflow = {
  recipeSlug: 'project-flow', recipeName: 'Project flow', version: 2, revision: 1,
  updatedAt: new Date(0).toISOString(), connections: [], migrationNotices: [],
  nodes: [
    { id: 'node-1', algorithmId: 'image-input', displayName: 'Image input', position: { x: 0, y: 0 }, parameters: {}, ports: [] },
    { id: 'node-2', algorithmId: 'logs', displayName: 'Logs', position: { x: 1, y: 0 }, parameters: {}, ports: [] },
    { id: 'node-3', algorithmId: 'image-output', displayName: 'Image output', position: { x: 2, y: 0 }, parameters: {}, ports: [] },
  ],
  executionOrder: ['node-1', 'node-2', 'node-3'],
};

function run(status: InspectionRun['status']): InspectionRun {
  return {
    id: 'run-1', boardSerial: 'PCB-1', lot: '', recipeId: 1, stationId: 'station-01', workOrderId: null,
    commissioningSnapshot: {}, resultId: null, status, currentStep: 'workflow-execution', progressPercent: 70,
    cancelRequested: false, workflowSha256: 'a'.repeat(64), effectiveVersions: {}, parameters: {}, inputArtifact: null,
    decision: null, evidenceSha256: null, errorCode: null, errorMessage: null,
    createdAt: new Date(0).toISOString(), startedAt: new Date(0).toISOString(), completedAt: null,
    nodeRuns: [
      { sequence: 1, nodeId: 'node-1', algorithmId: 'image-input', visitIndex: 1, nodeVersion: '1', executionTarget: 'local-cpu', status: 'completed', parameters: {}, inputs: {}, outputs: {}, resources: {}, evidenceSha256: null, errorCode: null, errorMessage: null, startedAt: '', completedAt: '', durationMs: 12, logEvent: null },
      { sequence: 2, nodeId: 'node-2', algorithmId: 'logs', visitIndex: 1, nodeVersion: '1', executionTarget: 'local-cpu', status: 'completed', parameters: {}, inputs: {}, outputs: {}, resources: {}, evidenceSha256: null, errorCode: null, errorMessage: null, startedAt: '', completedAt: '', durationMs: 3, logEvent: { destination: 'popup', level: 'warning', message: 'Alignment requires review.' } },
      { sequence: 3, nodeId: 'node-3', algorithmId: 'image-output', visitIndex: 1, nodeVersion: '1', executionTarget: 'local-cpu', status: 'running', parameters: {}, inputs: {}, outputs: {}, resources: {}, evidenceSha256: null, errorCode: null, errorMessage: null, startedAt: '', completedAt: null, durationMs: null, logEvent: null },
    ],
  };
}

function render(runState: InspectionRun) {
  const preferences = createDefaultPreferences(1, 'station-01').dashboard;
  return renderToStaticMarkup(<DashboardPage
    accessToken="token" inputs={null} outputs={null} isLoading={false} error="" isRunning={runState.status === 'executing'}
    inspectionRun={runState} runError="" onOutputToggle={vi.fn()} workflow={workflow} workflowError=""
    onConfigureWorkflow={vi.fn()} preferences={preferences} onPreferencesChange={vi.fn()}
  />);
}

describe('Project inspection flow runtime state', () => {
  it('shows completed, running, duration, and popup state only while the flow is active', () => {
    const markup = render(run('executing'));

    expect(markup).toContain('pipeline-step--completed');
    expect(markup).toContain('Completed · 12 ms');
    expect(markup).toContain('pipeline-step--running');
    expect(markup).toContain('Running');
    expect(markup).toContain('Alignment requires review.');
  });

  it('resets runtime status to white but keeps each node last-run duration when the flow ends', () => {
    const markup = render(run('completed'));

    expect(markup).not.toContain('pipeline-step--completed');
    expect(markup).not.toContain('pipeline-step--running');
    expect(markup).toContain('Not started · 12 ms');
    expect(markup).toContain('Not started · 3 ms');
    expect(markup).toContain('Image output, Not started');
    expect(markup).not.toContain('Image output, Not started ·');
  });

  it('keeps popup visible after the flow ends and stacks at most three newest toasts', () => {
    const withPopups: InspectionRun = {
      ...run('completed'),
      nodeRuns: [1, 2, 3, 4].map((sequence) => ({
        sequence, nodeId: 'node-2', algorithmId: 'logs', visitIndex: 1, nodeVersion: '1',
        executionTarget: 'local-cpu', status: 'completed', parameters: {}, inputs: {}, outputs: {},
        resources: {}, evidenceSha256: null, errorCode: null, errorMessage: null,
        startedAt: '', completedAt: '', durationMs: sequence,
        logEvent: { destination: 'popup', level: 'warning', message: `Popup message ${sequence}` },
      })),
    };

    const markup = render(withPopups);

    expect(markup).toContain('workflow-log-popups');
    expect(markup).toContain('WARNING');
    expect(markup).toContain('Popup message 2');
    expect(markup).toContain('Popup message 3');
    expect(markup).toContain('Popup message 4');
    expect(markup).not.toContain('Popup message 1');
  });
});