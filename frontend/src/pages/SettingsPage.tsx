import { useState } from 'react';
import type { WorkstationPreferences } from '../types/workstation-preferences';

const SETTINGS_SECTIONS = [
  'General',
  'Language & region',
  'Performance',
  'Inspection workflow',
  'Hardware & cameras',
  'Notifications',
  'Security & data',
];

interface SettingsPageProps {
  preferences: WorkstationPreferences;
  isDirty: boolean;
  isSaving: boolean;
  error: string;
  onWorkstationIdChange: (workstationId: string) => void;
  onSave: () => Promise<void>;
}

export function SettingsPage({ preferences, isDirty, isSaving, error, onWorkstationIdChange, onSave }: SettingsPageProps) {
  const [language, setLanguage] = useState('English (United States)');
  const [region, setRegion] = useState('Vietnam · GMT+7');
  const [units, setUnits] = useState('Metric (mm, μm)');
  const [clock, setClock] = useState('24-hour clock');
  const [saveMessage, setSaveMessage] = useState('');

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
              <select value={language} onChange={(event) => setLanguage(event.target.value)}>
                <option>English (United States)</option>
                <option>English (United Kingdom)</option>
              </select>
            </label>
            <label>
              <span>Regional format</span>
              <select value={region} onChange={(event) => setRegion(event.target.value)}>
                <option>Vietnam · GMT+7</option>
                <option>Singapore · GMT+8</option>
                <option>Germany · GMT+1</option>
              </select>
            </label>
            <label>
              <span>Measurement units</span>
              <select value={units} onChange={(event) => setUnits(event.target.value)}>
                <option>Metric (mm, μm)</option>
                <option>Imperial (in, mil)</option>
              </select>
            </label>
            <label>
              <span>Date & time</span>
              <select value={clock} onChange={(event) => setClock(event.target.value)}>
                <option>24-hour clock</option>
                <option>12-hour clock</option>
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