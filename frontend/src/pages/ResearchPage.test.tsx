import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import type { ResearchRun } from '../types/research';
import { ResearchPage } from './ResearchPage';

const runs: ResearchRun[] = [
  { id: 'run-01', experimentId: 'experiment-01', status: 'completed', executionTarget: 'local-gpu', codeRevision: '9ae70df', nodeVersions: { patchcore: '1.0.0' }, environment: { python: '3.12' }, randomSeeds: { python: 42 }, resources: { gpu: 'orin' }, datasetVersions: { pcb: 'sha256:abc' }, parameters: { memoryBankSize: 10000 }, metrics: { auroc: 0.98 }, outputArtifacts: { weights: 'sha256:def' }, error: null, createdAt: '2026-08-08T00:00:00Z' },
  { id: 'run-02', experimentId: 'experiment-01', status: 'failed', executionTarget: 'local-cpu', codeRevision: '9ae70df', nodeVersions: {}, environment: {}, randomSeeds: { python: 7 }, resources: {}, datasetVersions: {}, parameters: {}, metrics: {}, outputArtifacts: {}, error: 'Out of memory', createdAt: '2026-08-08T01:00:00Z' },
];

describe('ResearchPage', () => {
  it('renders search, comparison metrics, lineage, artifacts, and failure diagnostics', () => {
    const markup = renderToStaticMarkup(<ResearchPage accessToken="token" initialRuns={runs} />);

    expect(markup).toContain('Research runs');
    expect(markup).toContain('Compare selected');
    expect(markup).toContain('AUROC');
    expect(markup).toContain('sha256:def');
    expect(markup).toContain('Out of memory');
    expect(markup).toContain('9ae70df');
    expect(markup).toContain('Seed 42');
  });
});
