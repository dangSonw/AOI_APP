import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { HelpPage } from './HelpPage';
import { HELP_CONTENT } from './help-content';

describe('HelpPage', () => {
  it('renders the detailed Vietnamese guide and bilingual controls by default', () => {
    const markup = renderToStaticMarkup(<HelpPage onOpenWorkspace={vi.fn()} />);

    expect(markup).not.toContain('AOI Studio guide');
    expect(markup).not.toContain('Trung tâm trợ giúp');
    expect(markup).not.toContain('Hướng dẫn trực quan để cấu hình, xây dựng, đánh giá và vận hành AOI Studio an toàn.');
    expect(markup).toContain('Tìm trong hướng dẫn');
    expect(markup).toContain('Tiếng Việt');
    expect(markup).toContain('English');
    expect(markup).toContain('Workflow → Research → Models');
    expect(markup).toContain('Candidate');
    expect(markup).toContain('Champion');
    expect(markup).toContain('Rollback');
    expect(markup).toContain('image-set');
    expect(markup).toContain('float32');
  });

  it('contains guidance and workspace actions for every major application area', () => {
    const markup = renderToStaticMarkup(<HelpPage onOpenWorkspace={vi.fn()} />);

    for (const label of ['Dashboard', 'Hardware', 'Camera rig', 'Workflow', 'Dataset', 'Database', 'Research', 'Models', 'Settings']) {
      expect(markup).toContain(label);
    }
    expect(markup.match(/data-workspace-action=/g)?.length).toBeGreaterThanOrEqual(9);
    expect(markup).toContain('aria-label="Minh họa quy trình AOI Studio:');
  });

  it('keeps every bilingual topic procedural and the model workflow especially detailed', () => {
    for (const document of Object.values(HELP_CONTENT)) {
      for (const section of document.sections) expect(section.steps.length).toBeGreaterThanOrEqual(5);
      for (const id of ['workflow', 'research', 'models']) {
        expect(document.sections.find((section) => section.id === id)?.steps.length).toBeGreaterThanOrEqual(13);
      }
    }
  });
});