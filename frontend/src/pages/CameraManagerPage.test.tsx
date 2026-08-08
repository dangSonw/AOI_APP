import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { createDefaultPreferences } from '../utils/workstation-preferences';
import { CameraManagerPage } from './CameraManagerPage';


describe('CameraManagerPage', () => {
  it('shows workstation identity without allowing profile mutation', () => {
    const markup = renderToStaticMarkup(
      <CameraManagerPage
        preferences={createDefaultPreferences(1, 'station-01')}
        onChange={vi.fn()}
      />,
    );

    expect(markup).toContain('<input readonly="" value="station-01"/>');
  });
});