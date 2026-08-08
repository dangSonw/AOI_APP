import { useCallback, useEffect, useState } from 'react';
import { ApiError } from '../services/api-client';
import {
  activateSettings, createSettingsVersion, readSettings, readSettingsHistory,
  rollbackSettings, validateSettings,
} from '../services/settings-service';
import type { SettingsHistory, SettingsIdentity } from '../types/settings';

interface ConflictDetail {
  code?: string;
  currentRevision?: number;
  differences?: Array<{ path?: string }>;
}

export function useSettingsDocument<T extends object>(
  accessToken: string | undefined,
  identity: SettingsIdentity,
  initialPayload: T,
) {
  const [saved, setSaved] = useState<T>(structuredClone(initialPayload));
  const [draft, setDraft] = useState<T>(structuredClone(initialPayload));
  const [revision, setRevision] = useState(0);
  const [activeRevision, setActiveRevision] = useState<number | null>(null);
  const [history, setHistory] = useState<SettingsHistory<T>>({ versions: [], total: 0 });
  const [status, setStatus] = useState<'Draft' | 'Valid' | 'Applying' | 'Active' | 'Invalid' | 'Failed'>('Draft');
  const [error, setError] = useState('');
  const [conflict, setConflict] = useState<ConflictDetail | null>(null);
  const isDirty = JSON.stringify(saved) !== JSON.stringify(draft);

  const load = useCallback(async () => {
    if (!accessToken) return;
    setError('');
    try {
      const [document, nextHistory] = await Promise.all([
        readSettings<T>(accessToken, identity), readSettingsHistory<T>(accessToken, identity),
      ]);
      setSaved(document.current.payload);
      setDraft(structuredClone(document.current.payload));
      setRevision(document.currentRevision);
      setActiveRevision(document.activeRevision);
      setHistory(nextHistory);
      setStatus(document.activeRevision === document.currentRevision ? 'Active' : 'Draft');
    } catch (loadError) {
      if (!(loadError instanceof ApiError && loadError.status === 404)) {
        setError(loadError instanceof Error ? loadError.message : 'Settings could not be loaded.');
      }
    }
  }, [accessToken, identity.documentKey, identity.scope, identity.subjectId]);

  useEffect(() => { void load(); }, [load]);

  const save = async (reason: string, apply?: (payload: T) => Promise<void>) => {
    if (!accessToken) return;
    setError('');
    setConflict(null);
    try {
      await validateSettings(accessToken, identity, draft);
      setStatus('Valid');
      const version = await createSettingsVersion(accessToken, identity, revision, draft, reason);
      setSaved(structuredClone(version.payload));
      setDraft(structuredClone(version.payload));
      setRevision(version.revision);
      if (apply) {
        setStatus('Applying');
        await apply(version.payload);
      }
      await activateSettings(
        accessToken, identity, version.revision, reason,
        `${identity.documentKey}-${version.revision}-${crypto.randomUUID()}`,
      );
      setActiveRevision(version.revision);
      setStatus('Active');
      setHistory(await readSettingsHistory<T>(accessToken, identity));
    } catch (saveError) {
      if (saveError instanceof ApiError && saveError.status === 409 && typeof saveError.detail === 'object') {
        setConflict(saveError.detail as ConflictDetail);
      }
      setStatus(saveError instanceof ApiError && saveError.status === 422 ? 'Invalid' : 'Failed');
      setError(saveError instanceof Error ? saveError.message : 'Settings could not be saved.');
      throw saveError;
    }
  };

  const rollback = async (targetRevision: number, reason: string) => {
    if (!accessToken) return;
    const version = await rollbackSettings(accessToken, identity, revision, targetRevision, reason);
    setSaved(version.payload as T);
    setDraft(structuredClone(version.payload as T));
    setRevision(version.revision);
    setStatus('Draft');
    setHistory(await readSettingsHistory<T>(accessToken, identity));
  };

  return {
    draft, setDraft, revision, activeRevision, history, status, error, conflict, isDirty,
    save, rollback, discard: () => setDraft(structuredClone(saved)), reload: load,
  };
}
