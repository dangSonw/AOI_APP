import type { ResearchRun } from '../types/research';
import { apiRequest } from './api-client';

export function searchResearchRuns(accessToken: string, query = ''): Promise<ResearchRun[]> {
  return apiRequest(`/api/research/runs?query=${encodeURIComponent(query)}`, {}, accessToken);
}

export function readReproducibilityManifest(accessToken: string, runId: string): Promise<Record<string, unknown>> {
  return apiRequest(`/api/research/runs/${encodeURIComponent(runId)}/reproducibility-manifest`, {}, accessToken);
}
