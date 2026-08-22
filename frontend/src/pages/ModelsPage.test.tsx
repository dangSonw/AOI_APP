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
  }],
}];

describe('ModelsPage', () => {
  it('renders model versions, lineage, integrity, compatibility, and aliases', () => {
    const markup = renderToStaticMarkup(<ModelsPage accessToken="token" initialModels={models} />);

    expect(markup).toContain('Models');
    expect(markup).toContain('pcb-classifier');
    expect(markup).toContain('champion → v2');
    expect(markup).toContain('run-01');
    expect(markup).toContain('artifact verified');
    expect(markup).toContain('classification');
    expect(markup).toContain('scikit-learn');
    expect(markup).toContain('Promote to candidate');
    expect(markup).toContain('Promote to champion');
  });

  it('renders an actionable empty state', () => {
    const markup = renderToStaticMarkup(<ModelsPage accessToken="token" initialModels={[]} />);

    expect(markup).toContain('No registered models');
    expect(markup).toContain('completed research run');
  });
});
