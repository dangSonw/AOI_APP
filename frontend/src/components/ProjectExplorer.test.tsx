import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { ProjectExplorer } from './ProjectExplorer';

describe('ProjectExplorer', () => {
  it('keeps Database and removes Models shortcut', () => {
    const markup = renderToStaticMarkup(
      <ProjectExplorer
        activeView="database"
        isCollapsed={false}
        onViewChange={vi.fn()}
        onCollapseToggle={vi.fn()}
      />,
    );

    expect(markup).toContain('Database');
    expect(markup).not.toContain('Models');
  });
});