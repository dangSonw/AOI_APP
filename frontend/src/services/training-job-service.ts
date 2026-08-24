import type { TrainingJob, TrainingJobCreate } from '../types/training-job';
import { apiRequest } from './api-client';

const TRAINING_JOBS_PATH = '/api/v1/research/training-jobs';

export function createTrainingJob(accessToken: string, request: TrainingJobCreate): Promise<TrainingJob> {
  return apiRequest<TrainingJob>(TRAINING_JOBS_PATH, {
    method: 'POST',
    body: JSON.stringify(request),
  }, accessToken);
}

export function readTrainingJob(accessToken: string, runId: string): Promise<TrainingJob> {
  return apiRequest<TrainingJob>(`${TRAINING_JOBS_PATH}/${encodeURIComponent(runId)}`, {}, accessToken);
}

export function cancelTrainingJob(accessToken: string, runId: string): Promise<TrainingJob> {
  return apiRequest<TrainingJob>(`${TRAINING_JOBS_PATH}/${encodeURIComponent(runId)}/cancellations`, {
    method: 'POST',
  }, accessToken);
}