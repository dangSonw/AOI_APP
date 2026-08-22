import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { StudioChrome } from './StudioChrome';

const SESSION = {
  accessToken: 'token',
  tokenType: 'bearer' as const,
  user: {
    id: 1,
    email: 'operator@aoi.local',
    fullName: 'AOI Operator',
    isActive: true,
  },
};

describe('StudioChrome', () => {
  it('keeps the shell focused on real actions and workspace navigation', () => {
    const markup = renderToStaticMarkup(
      <StudioChrome
        session={SESSION}
        activeView="dashboard"
        isMachineReady
        isRunning={false}
        onViewChange={vi.fn()}
        onRunToggle={vi.fn()}
        onRefresh={vi.fn()}
        onSignOut={vi.fn()}
      >
        <p>Dashboard content</p>
      </StudioChrome>,
    );

    expect(markup).toContain('Inspection workspace');
    expect(markup).toContain('Dashboard content');
    expect(markup).toContain('Run');
    expect(markup).toContain('Calibrate');
    expect(markup).toContain('Refresh I/O');
    expect(markup).not.toContain('Single step');
    expect(markup).not.toContain('Capture');
    expect(markup).not.toContain('Yield: 99.1%');
    expect(markup).not.toContain('Reports');
  });
});