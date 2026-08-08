import { useEffect, useState } from 'react';
import { SettingsDocumentSection, type VersionedSectionId } from '../components/settings/SettingsDocumentSection';
import type { DeviceSnapshot } from '../types/devices';
import type { LocalePreferences, WorkstationPreferences } from '../types/workstation-preferences';
import { updateLocalePreference } from '../utils/workstation-preferences';

const SETTINGS_SECTIONS = [
  { id: 'overview', label: 'Overview & station', scope: 'Workstation' },
  { id: 'appearance', label: 'Appearance & locale', scope: 'User + workstation' },
  { id: 'acquisition', label: 'Acquisition & calibration', scope: 'Workstation' },
  { id: 'motion', label: 'Motion & I/O', scope: 'Workstation' },
  { id: 'inspection', label: 'Inspection defaults', scope: 'Recipe' },
  { id: 'compute', label: 'Compute & performance', scope: 'System' },
  { id: 'research', label: 'Research & models', scope: 'System' },
  { id: 'data', label: 'Data & retention', scope: 'System' },
  { id: 'integrations', label: 'Integrations', scope: 'System' },
  { id: 'notifications', label: 'Notifications', scope: 'System' },
  { id: 'security', label: 'Security, audit & updates', scope: 'System' },
] as const;

type SettingsSectionId = typeof SETTINGS_SECTIONS[number]['id'];

const REGION_TIMEZONES: Record<LocalePreferences['region'], LocalePreferences['timezone']> = {
  'vi-VN': 'Asia/Ho_Chi_Minh',
  'en-SG': 'Asia/Singapore',
  'de-DE': 'Europe/Berlin',
};

const WORKSTATION_ID_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

interface SettingsPageProps {
  accessToken?: string;
  deviceSnapshot?: DeviceSnapshot | null;
  preferences: WorkstationPreferences;
  isDirty: boolean;
  isSaving: boolean;
  error: string;
  onWorkstationSelect: (workstationId: string) => Promise<void>;
  onPreferencesChange: (preferences: WorkstationPreferences) => void;
  onSave: () => Promise<void>;
  onOpenHardware?: () => void;
}

export function canLoadWorkstationProfile(currentWorkstationId: string, requestedWorkstationId: string): boolean {
  return requestedWorkstationId !== currentWorkstationId && WORKSTATION_ID_PATTERN.test(requestedWorkstationId);
}

export async function loadWorkstationProfile(
  currentWorkstationId: string,
  requestedWorkstationId: string,
  onWorkstationSelect: (workstationId: string) => Promise<void>,
): Promise<void> {
  if (canLoadWorkstationProfile(currentWorkstationId, requestedWorkstationId)) {
    await onWorkstationSelect(requestedWorkstationId);
  }
}

export function createLocaleChangeHandlers(
  preferences: WorkstationPreferences,
  onPreferencesChange: (preferences: WorkstationPreferences) => void,
) {
  const updateLocale = (patch: Partial<LocalePreferences>) => {
    onPreferencesChange(updateLocalePreference(preferences, patch));
  };

  return {
    language: (language: LocalePreferences['language']) => updateLocale({ language }),
    region: (region: LocalePreferences['region']) => updateLocale({ region, timezone: REGION_TIMEZONES[region] }),
    measurementSystem: (measurementSystem: LocalePreferences['measurementSystem']) => updateLocale({ measurementSystem }),
    clockFormat: (clockFormat: LocalePreferences['clockFormat']) => updateLocale({ clockFormat }),
  };
}

export function SettingsPage({ accessToken, deviceSnapshot, preferences, isDirty, isSaving, error, onWorkstationSelect, onPreferencesChange, onSave, onOpenHardware }: SettingsPageProps) {
  const [activeSection, setActiveSection] = useState<SettingsSectionId>('appearance');
  const [workstationIdDraft, setWorkstationIdDraft] = useState(preferences.workstationId);
  const [isLoadingProfile, setIsLoadingProfile] = useState(false);
  const [saveMessage, setSaveMessage] = useState('');
  const localeChangeHandlers = createLocaleChangeHandlers(preferences, onPreferencesChange);

  useEffect(() => {
    setWorkstationIdDraft(preferences.workstationId);
  }, [preferences.workstationId]);

  const handleSave = async () => {
    setSaveMessage('');
    await onSave();
    setSaveMessage('Workspace state saved.');
  };

  const handleWorkstationLoad = async () => {
    setIsLoadingProfile(true);
    setSaveMessage('');
    try {
      await loadWorkstationProfile(preferences.workstationId, workstationIdDraft, onWorkstationSelect);
    } finally {
      setIsLoadingProfile(false);
    }
  };

  return (
    <div className="settings-page">
      <header className="workspace-title-row">
        <div>
          <span className="overline">Settings</span>
          <h1>Configuration control</h1>
          <p>Version desired state, validate changes, apply safely, and preserve lineage.</p>
        </div>
      </header>

      <div className="settings-layout">
        <nav className="settings-nav" aria-label="Settings sections">
          <span className="overline">Configuration scopes</span>
          {SETTINGS_SECTIONS.map((section) => (
            <button
              type="button"
              key={section.id}
              className={section.id === activeSection ? 'settings-nav__active' : ''}
              aria-current={section.id === activeSection ? 'page' : undefined}
              onClick={() => {
                if (!isDirty || activeSection !== 'appearance' || window.confirm('Discard unsaved locale changes and change section?')) {
                  setActiveSection(section.id);
                }
              }}
            >
              <span aria-hidden="true">{section.label.slice(0, 1)}</span><b>{section.label}</b><small>{section.scope}</small>
            </button>
          ))}
        </nav>

        <section className="settings-form" aria-labelledby="settings-form-title">
          <header>
            <span className="overline">{SETTINGS_SECTIONS.find((section) => section.id === activeSection)?.scope}</span>
            <h2 id="settings-form-title">{SETTINGS_SECTIONS.find((section) => section.id === activeSection)?.label}</h2>
            <p>Persistent desired state. Live diagnostics and machine commands stay in Hardware.</p>
          </header>
          {activeSection === 'appearance' ? <><div className="settings-ledger"><span><small>Scope</small><strong>User + workstation</strong></span><span><small>Revision</small><strong>R{preferences.revision}</strong></span><span><small>Active</small><strong>R{preferences.revision}</strong></span><span><small>Draft</small><strong>{isDirty ? 'Changed' : 'Clean'}</strong></span></div><div className="settings-group">
            <h3>Saved workspace state</h3>
            <label>
              <span>Workstation ID</span>
              <input value={workstationIdDraft} pattern="[a-z0-9]+(?:-[a-z0-9]+)*" onChange={(event) => setWorkstationIdDraft(event.target.value)} />
              <small>Dashboard layout and Photometric configuration are stored for this user and workstation.</small>
            </label>
            <button
              className="studio-secondary-button"
              type="button"
              disabled={isLoadingProfile || !canLoadWorkstationProfile(preferences.workstationId, workstationIdDraft)}
              onClick={() => void handleWorkstationLoad().catch(() => undefined)}
            >
              {isLoadingProfile ? 'Loading profile…' : 'Load station profile'}
            </button>
            <div className="settings-summary">
              <span>Photometric rig</span><strong>{preferences.photometric.lightCount} lights · {preferences.photometric.lightCount} images</strong>
              <span>Preference revision</span><strong>R{preferences.revision}</strong>
            </div>
            <h3>Regional preferences</h3>
            <label>
              <span>Display language</span>
              <select value={preferences.locale.language} onChange={(event) => localeChangeHandlers.language(event.target.value as LocalePreferences['language'])}>
                <option value="en-US">English (United States)</option>
                <option value="en-GB">English (United Kingdom)</option>
              </select>
            </label>
            <label>
              <span>Regional format</span>
              <select value={preferences.locale.region} onChange={(event) => localeChangeHandlers.region(event.target.value as LocalePreferences['region'])}>
                <option value="vi-VN">Vietnam</option>
                <option value="en-SG">Singapore</option>
                <option value="de-DE">Germany</option>
              </select>
            </label>
            <label>
              <span>Measurement units</span>
              <select value={preferences.locale.measurementSystem} onChange={(event) => localeChangeHandlers.measurementSystem(event.target.value as LocalePreferences['measurementSystem'])}>
                <option value="metric">Metric (mm, μm)</option>
                <option value="imperial">Imperial (in, mil)</option>
              </select>
            </label>
            <label>
              <span>Date & time</span>
              <select value={preferences.locale.clockFormat} onChange={(event) => localeChangeHandlers.clockFormat(event.target.value as LocalePreferences['clockFormat'])}>
                <option value="24-hour">24-hour clock</option>
                <option value="12-hour">12-hour clock</option>
              </select>
            </label>
          </div>
          <div className="settings-form__actions">
            {error && <span className="settings-error" role="alert">{error}</span>}
            {saveMessage && <span role="status">{saveMessage}</span>}
            <button className="studio-primary-button" type="button" disabled={!isDirty || isSaving} onClick={() => void handleSave().catch(() => undefined)}>{isSaving ? 'Saving…' : 'Save workspace state'}</button>
          </div>
          </> : <SettingsDocumentSection accessToken={accessToken} sectionId={activeSection as VersionedSectionId} workstationId={preferences.workstationId} deviceSnapshot={deviceSnapshot} onOpenHardware={onOpenHardware} />}
        </section>
      </div>
    </div>
  );
}