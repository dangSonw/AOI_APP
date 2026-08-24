import type {
  ModelAlias,
  ModelPromotionEvent,
  ModelRollbackPreview,
  ModelCreateRequest,
  ModelVersionCreateRequest,
  RegisteredModel,
  ResearchRun,
  ResearchRunArtifact,
} from '../types/research';
import { apiRequest } from './api-client';

export function searchResearchRuns(accessToken: string, query = ''): Promise<ResearchRun[]> {
  return apiRequest(`/api/research/runs?query=${encodeURIComponent(query)}`, {}, accessToken);
}

export function readReproducibilityManifest(accessToken: string, runId: string): Promise<Record<string, unknown>> {
  return apiRequest(`/api/research/runs/${encodeURIComponent(runId)}/reproducibility-manifest`, {}, accessToken);
}

export function readRegisteredModels(accessToken: string): Promise<RegisteredModel[]> {
  return apiRequest('/api/v1/models', {}, accessToken);
}

export function createRegisteredModel(accessToken: string, request: ModelCreateRequest): Promise<{ id: number; name: string; description: string }> {
  return apiRequest('/api/v1/models', {
    method: 'POST',
    body: JSON.stringify(request),
  }, accessToken);
}

export function createRegisteredModelVersion(
  accessToken: string,
  modelName: string,
  request: ModelVersionCreateRequest,
): Promise<{ id: number; modelName: string; version: number; runId: string; artifactId: number; artifactSha256: string }> {
  return apiRequest(`/api/v1/models/${encodeURIComponent(modelName)}/versions`, {
    method: 'POST',
    body: JSON.stringify(request),
  }, accessToken);
}

export function readResearchRunArtifacts(accessToken: string, runId: string): Promise<ResearchRunArtifact[]> {
  return apiRequest(`/api/v1/research/runs/${encodeURIComponent(runId)}/artifacts`, {}, accessToken);
}

export function promoteModel(
  accessToken: string,
  modelName: string,
  alias: ModelAlias,
  version: number,
  reason: string,
): Promise<ModelPromotionEvent> {
  return apiRequest(`/api/v1/models/${encodeURIComponent(modelName)}/aliases/${alias}/promotions`, {
    method: 'POST',
    body: JSON.stringify({ version, reason }),
  }, accessToken);
}

export function rollbackModel(
  accessToken: string,
  modelName: string,
  alias: ModelAlias,
  reason: string,
  previewEventId: number,
): Promise<ModelPromotionEvent> {
  return apiRequest(`/api/v1/models/${encodeURIComponent(modelName)}/aliases/${alias}/rollback`, {
    method: 'POST',
    body: JSON.stringify({ reason, previewEventId }),
  }, accessToken);
}

export function readModelRollbackPreview(
  accessToken: string,
  modelName: string,
  alias: ModelAlias,
): Promise<ModelRollbackPreview> {
  return apiRequest(`/api/v1/models/${encodeURIComponent(modelName)}/aliases/${alias}/rollback-preview`, {}, accessToken);
}

export function readModelEvents(accessToken: string, modelName: string): Promise<ModelPromotionEvent[]> {
  return apiRequest(`/api/v1/models/${encodeURIComponent(modelName)}/events`, {}, accessToken);
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
