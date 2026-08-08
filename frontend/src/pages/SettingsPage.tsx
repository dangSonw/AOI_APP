import { useState } from 'react';
import type { LocalePreferences, WorkstationPreferences } from '../types/workstation-preferences';
import { updateLocalePreference } from '../utils/workstation-preferences';

const SETTINGS_SECTIONS = [
  'General',
  'Language & region',
  'Performance',
  'Inspection workflow',
  'Hardware & cameras',
  'Notifications',
  'Security & data',
];

const REGION_TIMEZONES: Record<LocalePreferences['region'], LocalePreferences['timezone']> = {
  'vi-VN': 'Asia/Ho_Chi_Minh',
  'en-SG': 'Asia/Singapore',
  'de-DE': 'Europe/Berlin',
};

interface SettingsPageProps {
  preferences: WorkstationPreferences;
  isDirty: boolean;
  isSaving: boolean;
  error: string;
  onWorkstationIdChange: (workstationId: string) => void;
  onPreferencesChange: (preferences: WorkstationPreferences) => void;
  onSave: () => Promise<void>;
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

export function SettingsPage({ preferences, isDirty, isSaving, error, onWorkstationIdChange, onPreferencesChange, onSave }: SettingsPageProps) {
  const [saveMessage, setSaveMessage] = useState('');
  const localeChangeHandlers = createLocaleChangeHandlers(preferences, onPreferencesChange);

  const handleSave = async () => {
    setSaveMessage('');
    await onSave();
    setSaveMessage('Workspace state saved.');
  };

  return (
    <div className="settings-page">
      <header className="workspace-title-row">
        <div>
          <span className="overline">Settings</span>
          <h1>Workstation preferences</h1>
          <p>Configure how AOI Studio behaves for this inspection station.</p>
        </div>
      </header>

      <div className="settings-layout">
        <nav className="settings-nav" aria-label="Settings sections">
          <span className="overline">Workspace</span>
          {SETTINGS_SECTIONS.map((section) => (
            <button
              type="button"
              key={section}
              className={section === 'Language & region' ? 'settings-nav__active' : ''}
              disabled={section !== 'Language & region'}
              title={section !== 'Language & region' ? 'This section is not available in this milestone' : undefined}
            >
              <span aria-hidden="true">{section.slice(0, 1)}</span>{section}
            </button>
          ))}
        </nav>

        <section className="settings-form" aria-labelledby="settings-form-title">
          <header>
            <span className="overline">Language & region</span>
            <h2 id="settings-form-title">Language & region</h2>
            <p>Control localisation, date, time, and measurement preferences for this workstation.</p>
          </header>
          <div className="settings-group">
            <h3>Saved workspace state</h3>
            <label>
              <span>Workstation ID</span>
              <input value={preferences.workstationId} pattern="[a-z0-9]+(?:-[a-z0-9]+)*" onChange={(event) => onWorkstationIdChange(event.target.value)} />
              <small>Dashboard layout and Photometric configuration are stored for this user and workstation.</small>
            </label>
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
        </section>
      </div>
    </div>
  );
}