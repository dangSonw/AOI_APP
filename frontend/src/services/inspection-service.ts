import { apiRequest } from './api-client';
import type {
  InspectionDetail,
  InspectionFilters,
  InspectionListResponse,
  InspectionMetrics,
  RecipeItem,
} from '../types/inspection';

export async function readInspectionMetrics(accessToken: string): Promise<InspectionMetrics> {
  return apiRequest<InspectionMetrics>('/api/inspections/metrics', {}, accessToken);
}

export async function readInspections(
  accessToken: string,
  filters: InspectionFilters,
): Promise<InspectionListResponse> {
  const params = new URLSearchParams();
  params.set('page', String(filters.page));
  params.set('page_size', String(filters.pageSize));
  if (filters.result) params.set('result', filters.result);
  if (filters.recipeSlug) params.set('recipe_slug', filters.recipeSlug);
  if (filters.lot) params.set('lot', filters.lot);
  if (filters.search) params.set('search', filters.search);
  return apiRequest<InspectionListResponse>(`/api/inspections?${params.toString()}`, {}, accessToken);
}

export async function readInspectionDetail(
  accessToken: string,
  resultId: number,
): Promise<InspectionDetail> {
  return apiRequest<InspectionDetail>(`/api/inspections/${resultId}`, {}, accessToken);
}

export async function submitReview(
  accessToken: string,
  resultId: number,
  decision: 'PASS' | 'FAIL',
): Promise<void> {
  await apiRequest(`/api/inspections/${resultId}/review`, {
    method: 'PATCH',
    body: JSON.stringify({ decision }),
  }, accessToken);
}

export async function readRecipes(accessToken: string): Promise<RecipeItem[]> {
  return apiRequest<RecipeItem[]>('/api/recipes', {}, accessToken);
}
