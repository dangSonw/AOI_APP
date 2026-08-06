import type { WorkstationPreferences } from '../types/workstation-preferences';
import { apiRequest } from './api-client';


export function readWorkstationPreferences(
  accessToken: string,
  workstationId: string,
): Promise<WorkstationPreferences> {
  return apiRequest<WorkstationPreferences>(
    `/api/workstation-preferences/${encodeURIComponent(workstationId)}`,
    {},
    accessToken,
  );
}

export function saveWorkstationPreferences(
  accessToken: string,
  preferences: WorkstationPreferences,
): Promise<WorkstationPreferences> {
  return apiRequest<WorkstationPreferences>(
    `/api/workstation-preferences/${encodeURIComponent(preferences.workstationId)}`,
    { method: 'PUT', body: JSON.stringify(preferences) },
    accessToken,
  );
}