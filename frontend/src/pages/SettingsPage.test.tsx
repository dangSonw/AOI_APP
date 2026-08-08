import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { createDefaultPreferences } from '../utils/workstation-preferences';
import {
  canLoadWorkstationProfile,
  createLocaleChangeHandlers,
  loadWorkstationProfile,
  SettingsPage,
} from './SettingsPage';

describe('SettingsPage', () => {
  it('renders persisted locale preferences', () => {
    const preferences = createDefaultPreferences(1, 'station-01');
    preferences.locale = {
      language: 'en-GB',
      region: 'de-DE',
      timezone: 'Europe/Berlin',
      measurementSystem: 'imperial',
      clockFormat: '12-hour',
    };

    const markup = renderToStaticMarkup(
      <SettingsPage
        preferences={preferences}
        isDirty={false}
        isSaving={false}
        error=""
        onWorkstationSelect={vi.fn()}
        onPreferencesChange={vi.fn()}
        onSave={async () => undefined}
      />,
    );

    expect(markup).toContain('<option value="en-GB" selected="">English (United Kingdom)</option>');
    expect(markup).toContain('<option value="de-DE" selected="">Germany</option>');
    expect(markup).toContain('<option value="imperial" selected="">Imperial (in, mil)</option>');
    expect(markup).toContain('<option value="12-hour" selected="">12-hour clock</option>');
  });

  it('keeps workstation selector text separate from persisted preferences', () => {
    const preferences = createDefaultPreferences(1, 'station-01');
    const markup = renderToStaticMarkup(
      <SettingsPage
        preferences={preferences}
        isDirty={false}
        isSaving={false}
        error=""
        onWorkstationSelect={vi.fn()}
        onPreferencesChange={vi.fn()}
        onSave={async () => undefined}
      />,
    );

    expect(preferences.workstationId).toBe('station-01');
    expect(markup).toContain('value="station-01"');
    expect(markup).toContain('Load station profile');
    expect(markup).not.toContain('onWorkstationIdChange');
  });

  it('exposes every approved settings section without milestone-disabled navigation', () => {
    const markup = renderToStaticMarkup(
      <SettingsPage
        accessToken="token"
        preferences={createDefaultPreferences(1, 'station-01')}
        isDirty={false}
        isSaving={false}
        error=""
        onWorkstationSelect={vi.fn()}
        onPreferencesChange={vi.fn()}
        onSave={async () => undefined}
      />,
    );

    for (const label of [
      'Overview &amp; station', 'Appearance &amp; locale', 'Acquisition &amp; calibration',
      'Motion &amp; I/O', 'Inspection defaults', 'Compute &amp; performance',
      'Research &amp; models', 'Data &amp; retention', 'Integrations', 'Notifications',
      'Security, audit &amp; updates',
    ]) expect(markup).toContain(label);
    expect(markup).not.toContain('not available in this milestone');
    expect(markup).toContain('Scope');
    expect(markup).toContain('Revision');
    expect(markup).toContain('Draft');
    expect(markup).not.toContain('>Home<');
    expect(markup).not.toContain('>Move absolute<');
    expect(markup).not.toContain('>Clear fault<');
  });

  it('loads only a different valid workstation profile', async () => {
    const onWorkstationSelect = vi.fn(async () => undefined);

    expect(canLoadWorkstationProfile('station-01', 'station-02')).toBe(true);
    expect(canLoadWorkstationProfile('station-01', 'station-01')).toBe(false);
    expect(canLoadWorkstationProfile('station-01', 'Station_02')).toBe(false);
    expect(canLoadWorkstationProfile('station-01', '../station-02')).toBe(false);

    await loadWorkstationProfile('station-01', 'station-02', onWorkstationSelect);
    await loadWorkstationProfile('station-01', 'Station_02', onWorkstationSelect);

    expect(onWorkstationSelect).toHaveBeenCalledOnce();
    expect(onWorkstationSelect).toHaveBeenCalledWith('station-02');
  });

  it('publishes each locale selection as an updated preference document', () => {
    const preferences = createDefaultPreferences(1, 'station-01');
    const onPreferencesChange = vi.fn();
    const handlers = createLocaleChangeHandlers(preferences, onPreferencesChange);

    handlers.language('en-GB');
    handlers.region('de-DE');
    handlers.measurementSystem('imperial');
    handlers.clockFormat('12-hour');

    expect(onPreferencesChange).toHaveBeenNthCalledWith(1, expect.objectContaining({
      workstationId: 'station-01',
      locale: expect.objectContaining({ language: 'en-GB' }),
    }));
    expect(onPreferencesChange).toHaveBeenNthCalledWith(2, expect.objectContaining({
      locale: expect.objectContaining({ region: 'de-DE', timezone: 'Europe/Berlin' }),
    }));
    expect(onPreferencesChange).toHaveBeenNthCalledWith(3, expect.objectContaining({
      locale: expect.objectContaining({ measurementSystem: 'imperial' }),
    }));
    expect(onPreferencesChange).toHaveBeenNthCalledWith(4, expect.objectContaining({
      locale: expect.objectContaining({ clockFormat: '12-hour' }),
    }));
  });
});