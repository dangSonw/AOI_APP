import type { AlgorithmDefinition, Workflow } from '../types/workflow';
import { apiRequest } from './api-client';


export function readAlgorithmCatalog(accessToken: string): Promise<AlgorithmDefinition[]> {
  return apiRequest<AlgorithmDefinition[]>('/api/algorithms', {}, accessToken);
}

export function readWorkflow(accessToken: string, recipeSlug: string): Promise<Workflow> {
  return apiRequest<Workflow>(`/api/recipes/${encodeURIComponent(recipeSlug)}/workflow`, {}, accessToken);
}

export function saveWorkflow(accessToken: string, workflow: Workflow): Promise<Workflow> {
  return apiRequest<Workflow>(`/api/recipes/${encodeURIComponent(workflow.recipeSlug)}/workflow`, {
    method: 'PUT',
    body: JSON.stringify(workflow),
  }, accessToken);
}