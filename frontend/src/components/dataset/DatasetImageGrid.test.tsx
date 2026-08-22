import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { DatasetImageGrid } from './DatasetImageGrid';

const image = {
  filename: 'board-001.png',
  sizeBytes: 1200,
  mediaType: 'image/png',
  widthPx: 100,
  heightPx: 80,
  createdAt: '2026-08-21T00:00:00Z',
};

const props = {
  accessToken: 'token',
  datasetName: 'board-samples',
  categoryName: 'pass',
  getImageUrl: (datasetName: string, categoryName: string, filename: string) => `${datasetName}/${categoryName}/${filename}`,
  onSelectImage: vi.fn(),
  onRenameImage: vi.fn(),
  onDeleteImage: vi.fn(),
};

describe('DatasetImageGrid', () => {
  it('renders the empty category guidance', () => {
    const markup = renderToStaticMarkup(
      <DatasetImageGrid {...props} images={[]} isLoading={false} />,
    );

    expect(markup).toContain('No images in this category. Upload or import some.');
  });

  it('renders image actions and accessible preview control', () => {
    const markup = renderToStaticMarkup(
      <DatasetImageGrid {...props} images={[image]} isLoading={false} />,
    );

    expect(markup).toContain('View board-001.png');
    expect(markup).toContain('Rename');
    expect(markup).toContain('Delete');
  });
});