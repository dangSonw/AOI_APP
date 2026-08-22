import type {
  ModelAlias,
  ModelPromotionEvent,
  RegisteredModel,
  ResearchRun,
} from '../types/research';
import { apiRequest } from './api-client';

export function searchResearchRuns(accessToken: string, query = ''): Promise<ResearchRun[]> {
  return apiRequest(`/api/research/runs?query=${encodeURIComponent(query)}`, {}, accessToken);
}

export function readReproducibilityManifest(accessToken: string, runId: string): Promise<Record<string, unknown>> {
  return apiRequest(`/api/research/runs/${encodeURIComponent(runId)}/reproducibility-manifest`, {}, accessToken);
}

export function readRegisteredModels(accessToken: string): Promise<RegisteredModel[]> {
  return apiRequest('/api/models', {}, accessToken);
}

export function promoteModel(
  accessToken: string,
  modelName: string,
  alias: ModelAlias,
  version: number,
  reason: string,
): Promise<ModelPromotionEvent> {
  return apiRequest(`/api/models/${encodeURIComponent(modelName)}/aliases/${alias}/promotions`, {
    method: 'POST',
    body: JSON.stringify({ version, reason }),
  }, accessToken);
}

export function rollbackModel(
  accessToken: string,
  modelName: string,
  alias: ModelAlias,
  reason: string,
): Promise<ModelPromotionEvent> {
  return apiRequest(`/api/models/${encodeURIComponent(modelName)}/aliases/${alias}/rollback`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  }, accessToken);
}

export interface ImmutableModelBinding {
  modelName: string;
  modelVersion: number;
  artifactSha256: string;
}

export function resolveProductionBindings<T>(accessToken: string, payload: T): Promise<T> {
  return apiRequest<T>('/api/models/resolve-production-bindings', {
    method: 'POST',
    body: JSON.stringify(payload),
  }, accessToken);
}
