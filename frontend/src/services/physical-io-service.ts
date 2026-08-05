import type { PhysicalInputState, PhysicalOutputState } from '../types/physical-io';
import { apiRequest } from './api-client';

export function readPhysicalInputs(accessToken: string): Promise<PhysicalInputState> {
  return apiRequest<PhysicalInputState>('/api/io/inputs', {}, accessToken);
}

export function readPhysicalOutputs(accessToken: string): Promise<PhysicalOutputState> {
  return apiRequest<PhysicalOutputState>('/api/io/outputs', {}, accessToken);
}

export function writePhysicalOutputs(
  accessToken: string,
  signals: PhysicalOutputState['signals'],
): Promise<PhysicalOutputState> {
  return apiRequest<PhysicalOutputState>('/api/io/outputs', {
    method: 'PUT',
    body: JSON.stringify({ signals }),
  }, accessToken);
}