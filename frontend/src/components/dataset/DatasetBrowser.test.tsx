import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { DatasetBrowser } from './DatasetBrowser';

const dataset = {
  name: 'board-samples',
  description: 'Board images',
  totalImages: 3,
  totalSizeBytes: 300,
  categoryCount: 2,
  createdAt: '2026-08-21T00:00:00Z',
  updatedAt: '2026-08-21T00:00:00Z',
};

describe('DatasetBrowser', () => {
  it('renders the selected dataset and category actions', () => {
    const markup = renderToStaticMarkup(
      <DatasetBrowser
        datasets={[dataset]}
        datasetDetail={{ ...dataset, categories: [{ name: 'pass', imageCount: 2, totalSizeBytes: 200 }, { name: 'fail', imageCount: 1, totalSizeBytes: 100 }] }}
        selectedDataset="board-samples"
        selectedCategory="fail"
        isLoading={false}
        onCreateDataset={vi.fn()}
        onSelectDataset={vi.fn()}
        onSelectCategory={vi.fn()}
        onRenameDataset={vi.fn()}
        onDeleteDataset={vi.fn()}
        onExport={vi.fn()}
        onCreateCategory={vi.fn()}
        onRenameCategory={vi.fn()}
        onDeleteCategory={vi.fn()}
      />,
    );

    expect(markup).toContain('board-samples');
    expect(markup).toContain('pass (2)');
    expect(markup).toContain('fail (1)');
    expect(markup).toContain('New dataset');
    expect(markup).toContain('Rename');
    expect(markup).toContain('Delete');
    expect(markup).toContain('Export');
  });

  it('renders a clear empty state', () => {
    const markup = renderToStaticMarkup(
      <DatasetBrowser
        datasets={[]}
        datasetDetail={null}
        selectedDataset={null}
        selectedCategory={null}
        isLoading={false}
        onCreateDataset={vi.fn()}
        onSelectDataset={vi.fn()}
        onSelectCategory={vi.fn()}
        onRenameDataset={vi.fn()}
        onDeleteDataset={vi.fn()}
        onExport={vi.fn()}
        onCreateCategory={vi.fn()}
        onRenameCategory={vi.fn()}
        onDeleteCategory={vi.fn()}
      />,
    );

    expect(markup).toContain('No datasets yet.');
  });
});