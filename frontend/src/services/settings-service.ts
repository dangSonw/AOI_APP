import type { SettingsDocument, SettingsHistory, SettingsIdentity, SettingsVersion } from '../types/settings';
import { apiRequest } from './api-client';

const basePath = ({ scope, subjectId }: SettingsIdentity) => (
  `/api/v1/settings/${scope}/${encodeURIComponent(subjectId)}`
);

export function readSettings<T>(accessToken: string, identity: SettingsIdentity): Promise<SettingsDocument<T>> {
  return apiRequest(`${basePath(identity)}?documentKey=${encodeURIComponent(identity.documentKey)}`, {}, accessToken);
}

export function readSettingsHistory<T>(accessToken: string, identity: SettingsIdentity): Promise<SettingsHistory<T>> {
  return apiRequest(`${basePath(identity)}/history?documentKey=${encodeURIComponent(identity.documentKey)}`, {}, accessToken);
}

export function validateSettings(accessToken: string, identity: SettingsIdentity, payload: unknown): Promise<unknown> {
  return apiRequest(`${basePath(identity)}/validate`, {
    method: 'POST', body: JSON.stringify({ documentKey: identity.documentKey, schemaVersion: 1, payload }),
  }, accessToken);
}

export function createSettingsVersion<T>(
  accessToken: string, identity: SettingsIdentity, expectedRevision: number, payload: T, reason: string,
): Promise<SettingsVersion<T>> {
  return apiRequest(`${basePath(identity)}/versions`, {
    method: 'POST',
    body: JSON.stringify({ documentKey: identity.documentKey, expectedRevision, schemaVersion: 1, payload, reason }),
  }, accessToken);
}

export function activateSettings(
  accessToken: string, identity: SettingsIdentity, revision: number, reason: string, idempotencyKey: string,
): Promise<unknown> {
  return apiRequest(`${basePath(identity)}/activations`, {
    method: 'POST', headers: { 'Idempotency-Key': idempotencyKey },
    body: JSON.stringify({ documentKey: identity.documentKey, revision, reason }),
  }, accessToken);
}

export function rollbackSettings(
  accessToken: string, identity: SettingsIdentity, expectedRevision: number, targetRevision: number, reason: string,
): Promise<SettingsVersion> {
  return apiRequest(`${basePath(identity)}/rollback`, {
    method: 'POST', body: JSON.stringify({ documentKey: identity.documentKey, expectedRevision, targetRevision, reason }),
  }, accessToken);
}
