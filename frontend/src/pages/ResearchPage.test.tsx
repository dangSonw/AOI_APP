import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import type { ResearchRun } from '../types/research';
import { ResearchPage, transitionResearchComparison } from './ResearchPage';

const runs: ResearchRun[] = [
  { id: 'run-01', experimentId: 'experiment-01', status: 'completed', executionTarget: 'local-gpu', codeRevision: '9ae70df', nodeVersions: { patchcore: '1.0.0' }, environment: { python: '3.12' }, randomSeeds: { python: 42 }, resources: { gpu: 'orin' }, datasetVersions: { pcb: 'sha256:abc' }, parameters: { memoryBankSize: 10000 }, metrics: { auroc: 0.98 }, outputArtifacts: { weights: 'sha256:def' }, error: null, createdAt: '2026-08-08T00:00:00Z' },
  { id: 'run-02', experimentId: 'experiment-01', status: 'failed', executionTarget: 'local-cpu', codeRevision: '9ae70df', nodeVersions: {}, environment: {}, randomSeeds: { python: 7 }, resources: {}, datasetVersions: {}, parameters: {}, metrics: {}, outputArtifacts: {}, error: 'Out of memory', createdAt: '2026-08-08T01:00:00Z' },
];

describe('ResearchPage', () => {
  it('renders search, comparison metrics, lineage, artifacts, and failure diagnostics', () => {
    const markup = renderToStaticMarkup(<ResearchPage accessToken="token" initialRuns={runs} />);

    expect(markup).not.toContain('Experiment tracking');
    expect(markup).not.toContain('<h1>Research runs</h1>');
    expect(markup).toContain('Run ID, experiment ID or name, code revision, execution target');
    expect(markup).toContain('Compare selected');
    expect(markup).toContain('AUROC');
    expect(markup).toContain('sha256:def');
    expect(markup).toContain('Out of memory');
    expect(markup).toContain('9ae70df');
    expect(markup).toContain('Seed 42');
    expect(markup.match(/View reproducibility manifest/g)).toHaveLength(2);
  });

  it('explains the research workflow and presents readable run status', () => {
    const markup = renderToStaticMarkup(<ResearchPage accessToken="token" initialRuns={runs} />);

    expect(markup).not.toContain('Find, evaluate, and compare training runs before registering a model artifact.');
    expect(markup).toContain('Find the right run');
    expect(markup).toContain('Review the evidence');
    expect(markup).toContain('Compare outcomes');
    expect(markup).toContain('0 selected');
    expect(markup).toContain('Status: Completed');
    expect(markup).toContain('Status: Failed');
  });

  it('keeps model registry and lifecycle content out of Research', () => {
    const markup = renderToStaticMarkup(<ResearchPage accessToken="token" initialRuns={runs} />);

    expect(markup).not.toContain('Experiment tracking');
    expect(markup).not.toContain('Model versions');
    expect(markup).not.toContain('Registered models');
    expect(markup).not.toContain('No registered models');
    expect(markup).not.toContain('Promote to candidate');
  });

  it('opens comparison explicitly and closes it when selection becomes insufficient', () => {
    const initial = { selectedRunIds: [] as string[], isComparisonOpen: false };
    const oneSelected = transitionResearchComparison(initial, { type: 'select', runId: 'run-01', isSelected: true });
    const prematureOpen = transitionResearchComparison(oneSelected, { type: 'open' });
    const twoSelected = transitionResearchComparison(prematureOpen, { type: 'select', runId: 'run-02', isSelected: true });
    const opened = transitionResearchComparison(twoSelected, { type: 'open' });
    const insufficient = transitionResearchComparison(opened, { type: 'select', runId: 'run-02', isSelected: false });

    expect(prematureOpen.isComparisonOpen).toBe(false);
    expect(opened).toEqual({ selectedRunIds: ['run-01', 'run-02'], isComparisonOpen: true });
    expect(insufficient).toEqual({ selectedRunIds: ['run-01'], isComparisonOpen: false });
    expect(transitionResearchComparison(opened, { type: 'close' }).isComparisonOpen).toBe(false);
  });

  it('renders a source-run query supplied by Models', () => {
    const markup = renderToStaticMarkup(
      <ResearchPage accessToken="token" initialRuns={runs} initialQuery="run-01" />,
    );

    expect(markup).toContain('value="run-01"');
  });

  it('bounds the initial run list for large research histories', () => {
    const manyRuns = Array.from({ length: 25 }, (_, index) => ({
      ...runs[0],
      id: `run-${index + 1}`,
    }));
    const markup = renderToStaticMarkup(<ResearchPage accessToken="token" initialRuns={manyRuns} />);

    expect(markup.match(/View reproducibility manifest/g)).toHaveLength(20);
    expect(markup).toContain('Showing 20 of 25 runs');
    expect(markup).toContain('Show 5 more');
  });
});
