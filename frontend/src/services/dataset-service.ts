import { apiBlobRequest, apiRequest } from './api-client';
import type {
  CaptureListResponse,
  DatasetDetail,
  DatasetListResponse,
  DatasetSummary,
  DatasetValidationReport,
  CsvPreviewResponse,
  CsvPreparationResponse,
  CsvPreparationSnapshotResponse,
  CsvPreprocessingPreviewResponse,
  CsvProcessedArtifactResponse,
  CsvProcessedArtifactVerificationResponse,
  CsvKnnTrainingJobResponse,
  ImageInfo,
  ImageListResponse,
} from '../types/dataset';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, '');

const encode = encodeURIComponent;


export function readDatasets(accessToken: string): Promise<DatasetSummary[]> {
  return apiRequest<DatasetListResponse>('/api/datasets', {}, accessToken).then((response) => response.datasets);
}

export function createDataset(accessToken: string, name: string, description: string): Promise<DatasetDetail> {
  return apiRequest<DatasetDetail>('/api/datasets', {
    method: 'POST',
    body: JSON.stringify({ name, description }),
  }, accessToken);
}

export function readDataset(accessToken: string, name: string): Promise<DatasetDetail> {
  return apiRequest<DatasetDetail>(`/api/datasets/${encode(name)}`, {}, accessToken);
}

export function validateDataset(accessToken: string, name: string): Promise<DatasetValidationReport> {
  return apiRequest<DatasetValidationReport>(`/api/datasets/${encode(name)}/validate`, { method: 'POST' }, accessToken);
}

export async function previewCsv(accessToken: string, datasetName: string, file: File): Promise<CsvPreviewResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const headers = new Headers({ Authorization: `Bearer ${accessToken}` });
  const response = await fetch(`${API_BASE_URL}/api/datasets/${encode(datasetName)}/csv-preview`, {
    method: 'POST', headers, body: formData,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({})) as { detail?: unknown };
    throw new Error(typeof body.detail === 'string' ? body.detail : 'The CSV preview could not be generated.');
  }
  return response.json() as Promise<CsvPreviewResponse>;
}

export async function prepareCsv(
  accessToken: string,
  datasetName: string,
  file: File,
  targetColumn: string,
  featureColumns: string[],
  ratios: { train: number; validation: number; test: number },
): Promise<CsvPreparationResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('targetColumn', targetColumn);
  formData.append('featureColumns', JSON.stringify(featureColumns));
  formData.append('trainRatio', String(ratios.train));
  formData.append('validationRatio', String(ratios.validation));
  formData.append('testRatio', String(ratios.test));
  const response = await fetch(`${API_BASE_URL}/api/datasets/${encode(datasetName)}/csv-prepare`, {
    method: 'POST', headers: new Headers({ Authorization: `Bearer ${accessToken}` }), body: formData,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({})) as { detail?: unknown };
    throw new Error(typeof body.detail === 'string' ? body.detail : 'The CSV preparation could not be generated.');
  }
  return response.json() as Promise<CsvPreparationResponse>;
}

export async function createCsvPreparationSnapshot(
  accessToken: string,
  datasetName: string,
  file: File,
  targetColumn: string,
  featureColumns: string[],
  ratios: { train: number; validation: number; test: number },
  preprocessingPolicy: Record<string, string> = {},
): Promise<CsvPreparationSnapshotResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('targetColumn', targetColumn);
  formData.append('featureColumns', JSON.stringify(featureColumns));
  formData.append('trainRatio', String(ratios.train));
  formData.append('validationRatio', String(ratios.validation));
  formData.append('testRatio', String(ratios.test));
  formData.append('preprocessingPolicy', JSON.stringify(preprocessingPolicy));
  const response = await fetch(`${API_BASE_URL}/api/datasets/${encode(datasetName)}/csv-preparations`, {
    method: 'POST', headers: new Headers({ Authorization: `Bearer ${accessToken}` }), body: formData,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({})) as { detail?: unknown };
    throw new Error(typeof body.detail === 'string' ? body.detail : 'The CSV preparation snapshot could not be created.');
  }
  return response.json() as Promise<CsvPreparationSnapshotResponse>;
}

export function previewCsvPreprocessing(
  accessToken: string,
  datasetName: string,
  preparationId: string,
): Promise<CsvPreprocessingPreviewResponse> {
  return apiRequest<CsvPreprocessingPreviewResponse>(
    `/api/datasets/${encode(datasetName)}/csv-preparations/${encode(preparationId)}/preview`,
    { method: 'POST' },
    accessToken,
  );
}

export function createCsvProcessedArtifact(
  accessToken: string,
  datasetName: string,
  preparationId: string,
): Promise<CsvProcessedArtifactResponse> {
  return apiRequest<CsvProcessedArtifactResponse>(
    `/api/datasets/${encode(datasetName)}/csv-preparations/${encode(preparationId)}/artifacts`,
    { method: 'POST' },
    accessToken,
  );
}

export function readCsvProcessedArtifacts(accessToken: string, datasetName: string, preparationId: string): Promise<CsvProcessedArtifactResponse[]> {
  return apiRequest<{ artifacts: CsvProcessedArtifactResponse[] }>(
    `/api/datasets/${encode(datasetName)}/csv-preparations/${encode(preparationId)}/artifacts`, {}, accessToken,
  ).then((response) => response.artifacts);
}

export function verifyCsvProcessedArtifact(
  accessToken: string, datasetName: string, preparationId: string, artifactId: string,
): Promise<CsvProcessedArtifactVerificationResponse> {
  return apiRequest<CsvProcessedArtifactVerificationResponse>(
    `/api/datasets/${encode(datasetName)}/csv-preparations/${encode(preparationId)}/artifacts/${encode(artifactId)}/verify`,
    { method: 'POST' }, accessToken,
  );
}

export function createCsvKnnTrainingJob(
  accessToken: string, datasetName: string, preparationId: string, artifactId: string, k: number,
): Promise<CsvKnnTrainingJobResponse> {
  return apiRequest<CsvKnnTrainingJobResponse>(
    `/api/datasets/${encode(datasetName)}/csv-preparations/${encode(preparationId)}/artifacts/${encode(artifactId)}/knn-jobs`,
    { method: 'POST', body: JSON.stringify({ k }) }, accessToken,
  );
}

export function readCsvKnnTrainingJobs(
  accessToken: string, datasetName: string, preparationId: string, artifactId: string,
): Promise<CsvKnnTrainingJobResponse[]> {
  return apiRequest<{ jobs: CsvKnnTrainingJobResponse[] }>(
    `/api/datasets/${encode(datasetName)}/csv-preparations/${encode(preparationId)}/artifacts/${encode(artifactId)}/knn-jobs`, {}, accessToken,
  ).then((response) => response.jobs);
}

export function updateDataset(
  accessToken: string,
  name: string,
  body: { newName?: string; description?: string },
): Promise<DatasetDetail> {
  return apiRequest<DatasetDetail>(`/api/datasets/${encode(name)}`, {
    method: 'PUT',
    body: JSON.stringify(body),
  }, accessToken);
}

export function deleteDataset(accessToken: string, name: string): Promise<void> {
  return apiRequest<void>(`/api/datasets/${encode(name)}`, { method: 'DELETE' }, accessToken);
}

export function createCategory(accessToken: string, datasetName: string, categoryName: string): Promise<DatasetDetail> {
  return apiRequest<DatasetDetail>(`/api/datasets/${encode(datasetName)}/categories`, {
    method: 'POST',
    body: JSON.stringify({ name: categoryName }),
  }, accessToken);
}

export function renameCategory(
  accessToken: string,
  datasetName: string,
  oldName: string,
  newName: string,
): Promise<DatasetDetail> {
  return apiRequest<DatasetDetail>(`/api/datasets/${encode(datasetName)}/categories/${encode(oldName)}`, {
    method: 'PUT',
    body: JSON.stringify({ newName }),
  }, accessToken);
}

export function deleteCategory(
  accessToken: string,
  datasetName: string,
  categoryName: string,
): Promise<DatasetDetail> {
  return apiRequest<DatasetDetail>(`/api/datasets/${encode(datasetName)}/categories/${encode(categoryName)}`, {
    method: 'DELETE',
  }, accessToken);
}

export function readImages(accessToken: string, datasetName: string, categoryName: string): Promise<ImageInfo[]> {
  return apiRequest<ImageListResponse>(
    `/api/datasets/${encode(datasetName)}/categories/${encode(categoryName)}/images`,
    {},
    accessToken,
  ).then((response) => response.images);
}

export async function uploadImages(
  accessToken: string,
  datasetName: string,
  categoryName: string,
  files: File[],
): Promise<ImageInfo[]> {
  const formData = new FormData();
  for (const file of files) formData.append('files', file);
  const headers = new Headers({ Authorization: `Bearer ${accessToken}` });
  const response = await fetch(
    `${API_BASE_URL}/api/datasets/${encode(datasetName)}/categories/${encode(categoryName)}/images`,
    { method: 'POST', headers, body: formData },
  );
  if (!response.ok) {
    const body = await response.json().catch(() => ({})) as { detail?: unknown };
    const detail = body.detail;
    const message = typeof detail === 'string'
      ? detail
      : Array.isArray(detail) && typeof detail[0]?.message === 'string'
        ? detail[0].message
        : 'The upload could not be completed.';
    throw new Error(message);
  }
  const data = await response.json() as ImageListResponse;
  return data.images;
}

export function getImageUrl(datasetName: string, categoryName: string, filename: string): string {
  return `${API_BASE_URL}/api/datasets/${encode(datasetName)}/categories/${encode(categoryName)}/images/${encode(filename)}`;
}

export function deleteImage(
  accessToken: string,
  datasetName: string,
  categoryName: string,
  filename: string,
): Promise<void> {
  return apiRequest<void>(
    `/api/datasets/${encode(datasetName)}/categories/${encode(categoryName)}/images/${encode(filename)}`,
    { method: 'DELETE' },
    accessToken,
  );
}

export function renameImage(
  accessToken: string,
  datasetName: string,
  categoryName: string,
  oldName: string,
  newName: string,
): Promise<ImageInfo> {
  return apiRequest<ImageInfo>(
    `/api/datasets/${encode(datasetName)}/categories/${encode(categoryName)}/images/${encode(oldName)}`,
    { method: 'PATCH', body: JSON.stringify({ newFilename: newName }) },
    accessToken,
  );
}

export function moveImage(
  accessToken: string,
  datasetName: string,
  categoryName: string,
  filename: string,
  targetCategory: string,
): Promise<ImageInfo> {
  return apiRequest<ImageInfo>(
    `/api/datasets/${encode(datasetName)}/categories/${encode(categoryName)}/images/${encode(filename)}/move`,
    { method: 'POST', body: JSON.stringify({ targetCategory }) },
    accessToken,
  );
}

export function importCaptures(
  accessToken: string,
  datasetName: string,
  filenames: string[],
  targetCategory: string,
): Promise<ImageInfo[]> {
  return apiRequest<ImageListResponse>(
    `/api/datasets/${encode(datasetName)}/import-captures`,
    { method: 'POST', body: JSON.stringify({ filenames, targetCategory }) },
    accessToken,
  ).then((response) => response.images);
}

export async function exportDataset(accessToken: string, datasetName: string): Promise<Blob> {
  return apiBlobRequest(`/api/datasets/${encode(datasetName)}/export`, accessToken);
}

export function readCaptures(accessToken: string): Promise<CaptureListResponse['files']> {
  return apiRequest<CaptureListResponse>('/api/datasets/captures/available', {}, accessToken)
    .then((response) => response.files);
}
