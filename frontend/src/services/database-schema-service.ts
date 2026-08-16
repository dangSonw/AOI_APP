import type { DatabaseSchema } from '../types/database-schema';
import { apiRequest } from './api-client';

export function readDatabaseSchema(accessToken: string): Promise<DatabaseSchema> {
  return apiRequest<DatabaseSchema>('/api/database/schema', {}, accessToken);
}