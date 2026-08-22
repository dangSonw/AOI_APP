import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { ProjectExplorer } from './ProjectExplorer';

describe('ProjectExplorer', () => {
  it('groups real workspace destinations without placeholder shortcuts', () => {
    const markup = renderToStaticMarkup(
      <ProjectExplorer
        activeView="database"
        isCollapsed={false}
        onViewChange={vi.fn()}
        onCollapseToggle={vi.fn()}
      />,
    );

    expect(markup).toContain('Database');
    expect(markup).toContain('Operate');
    expect(markup).toContain('Build');
    expect(markup).toContain('Review');
    expect(markup).toContain('System');
    expect(markup).toContain('Research');
    expect(markup).toContain('Models');
    expect(markup).not.toContain('Plugins');
    expect(markup).not.toContain('Logs');
  });
});