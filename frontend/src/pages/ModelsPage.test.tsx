import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import type { RegisteredModel } from '../types/research';
import { ModelsPage } from './ModelsPage';

const models: RegisteredModel[] = [{
  name: 'pcb-classifier',
  description: 'Board classifier',
  aliases: { champion: 2 },
  versions: [{
    version: 2,
    runId: 'run-01',
    artifactSha256: 'a'.repeat(64),
    artifactVerified: true,
    validationEvidence: { passed: true, accuracy: 0.99 },
    compatibility: { task: 'classification', inputSchema: 'features', outputSchema: 'labels', framework: 'scikit-learn', status: 'validated' },
    createdAt: '2026-08-24T00:00:00Z',
  }],
}];

describe('ModelsPage', () => {
  it('renders model versions, lineage, integrity, compatibility, and aliases', () => {
    const markup = renderToStaticMarkup(<ModelsPage accessToken="token" initialModels={models} onOpenResearchRun={() => undefined} />);

    expect(markup).not.toContain('Model registry</span>');
    expect(markup).toContain('pcb-classifier');
    expect(markup).toContain('champion → v2');
    expect(markup).toContain('run-01');
    expect(markup).toContain('artifact verified');
    expect(markup).toContain('classification');
    expect(markup).toContain('scikit-learn');
    expect(markup).toContain('Promote to candidate');
    expect(markup).toContain('Promote to champion');
    expect(markup).toContain('Rollback champion');
    expect(markup).not.toContain('alias: rollback');
    expect(markup).toContain('Input schema');
    expect(markup).toContain('Output schema');
    expect(markup).toContain('Validation evidence');
    expect(markup).toContain('Accuracy');
    expect(markup).toContain('Advanced raw evidence');
    expect(markup).toContain('Open source run');
  });

  it('explains model governance and guides registration in three stages', () => {
    const markup = renderToStaticMarkup(<ModelsPage accessToken="token" initialModels={models} />);

    expect(markup).not.toContain('Register and govern deployable model versions from verified research artifacts.');
    expect(markup).toContain('Register an artifact');
    expect(markup).toContain('Promote a candidate');
    expect(markup).toContain('Choose a champion');
    expect(markup).toContain('Candidate is a version under review');
    expect(markup).toContain('1 model');
    expect(markup).toContain('Choose destination');
    expect(markup).toContain('Choose source run');
    expect(markup).toContain('Register artifact');
  });

  it('renders an actionable empty state', () => {
    const markup = renderToStaticMarkup(<ModelsPage accessToken="token" initialModels={[]} />);

    expect(markup).toContain('No registered models');
    expect(markup).toContain('completed research run');
  });

  it('renders model creation and validated artifact registration states', () => {
    const markup = renderToStaticMarkup(
      <ModelsPage
        accessToken="token"
        initialModels={models}
        initialRuns={[{
          id: 'run-01', experimentId: 'experiment-01', status: 'completed',
          executionTarget: 'local-cpu', codeRevision: 'abc123', nodeVersions: {},
          environment: {}, randomSeeds: {}, resources: {}, datasetVersions: {},
          parameters: {}, metrics: { accuracy: 0.99 }, outputArtifacts: {}, error: null,
        }, {
          id: 'run-failed', experimentId: 'experiment-01', status: 'failed',
          executionTarget: 'local-cpu', codeRevision: 'abc123', nodeVersions: {},
          environment: {}, randomSeeds: {}, resources: {}, datasetVersions: {},
          parameters: {}, metrics: {}, outputArtifacts: {}, error: 'Training failed.',
        }]}
      />,
    );

    expect(markup).toContain('Register model version');
    expect(markup).toContain('Create a new model');
    expect(markup).toContain('Use an existing model');
    expect(markup).toContain('run-01');
    expect(markup).not.toContain('run-failed');
    expect(markup).toContain('Select a completed source run');
    expect(markup).toContain('Select a verified artifact');
  });

  it('bounds the initial registry list when many models exist', () => {
    const manyModels = Array.from({ length: 23 }, (_, index) => ({
      ...models[0],
      name: `model-${index + 1}`,
    }));
    const markup = renderToStaticMarkup(<ModelsPage accessToken="token" initialModels={manyModels} />);

    expect(markup.match(/View lifecycle history/g)).toHaveLength(20);
    expect(markup).toContain('Showing 20 of 23 models');
    expect(markup).toContain('Show 3 more');
  });
});
