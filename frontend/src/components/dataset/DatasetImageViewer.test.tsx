import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { DatasetImageViewer } from './DatasetImageViewer';

const image = {
  filename: 'board-001.png',
  sizeBytes: 1200,
  mediaType: 'image/png',
  widthPx: 100,
  heightPx: 80,
  createdAt: '2026-08-21T00:00:00Z',
};

describe('DatasetImageViewer', () => {
  it('renders metadata and navigation controls for a collection', () => {
    const markup = renderToStaticMarkup(
      <DatasetImageViewer
        accessToken="token"
        image={image}
        imageIndex={1}
        imageCount={3}
        imageUrl="/image.png"
        formatBytes={(bytes) => `${bytes} bytes`}
        onClose={vi.fn()}
        onPrevious={vi.fn()}
        onNext={vi.fn()}
        onDelete={vi.fn()}
      />,
    );

    expect(markup).toContain('Image viewer');
    expect(markup).toContain('board-001.png');
    expect(markup).toContain('100 × 80');
    expect(markup).toContain('1200 bytes');
    expect(markup).toContain('2 / 3');
    expect(markup).toContain('Close image viewer');
    expect(markup).not.toContain('disabled=""');
  });

  it('disables navigation for a single image', () => {
    const markup = renderToStaticMarkup(
      <DatasetImageViewer
        accessToken="token"
        image={image}
        imageIndex={0}
        imageCount={1}
        imageUrl="/image.png"
        formatBytes={() => '1 KB'}
        onClose={vi.fn()}
        onPrevious={vi.fn()}
        onNext={vi.fn()}
        onDelete={vi.fn()}
      />,
    );

    expect(markup.match(/disabled=""/g)?.length).toBe(2);
  });
});