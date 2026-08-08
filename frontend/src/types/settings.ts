export type SettingsScope = 'user' | 'workstation' | 'recipe' | 'system';

export interface SettingsIdentity {
  scope: SettingsScope;
  subjectId: string;
  documentKey: string;
}

export interface SettingsVersion<T = Record<string, unknown>> {
  id: number;
  revision: number;
  schemaVersion: number;
  payload: T;
  checksum: string;
  createdBy: number;
  reason: string;
  sourceVersionId: number | null;
  createdAt: string;
}

export interface SettingsDocument<T = Record<string, unknown>> {
  scope: SettingsScope;
  subjectId: string;
  documentKey: string;
  ownerUserId: number | null;
  currentRevision: number;
  current: SettingsVersion<T>;
  activeRevision: number | null;
}

export interface SettingsHistory<T = Record<string, unknown>> {
  versions: SettingsVersion<T>[];
  total: number;
}