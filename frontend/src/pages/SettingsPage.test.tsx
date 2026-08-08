import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { createDefaultPreferences } from '../utils/workstation-preferences';
import { createLocaleChangeHandlers, SettingsPage } from './SettingsPage';

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
        onWorkstationIdChange={vi.fn()}
        onPreferencesChange={vi.fn()}
        onSave={async () => undefined}
      />,
    );

    expect(markup).toContain('<option value="en-GB" selected="">English (United Kingdom)</option>');
    expect(markup).toContain('<option value="de-DE" selected="">Germany</option>');
    expect(markup).toContain('<option value="imperial" selected="">Imperial (in, mil)</option>');
    expect(markup).toContain('<option value="12-hour" selected="">12-hour clock</option>');
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