import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import {
  createReproducibilityManifestDownload,
  loadReproducibilityManifest,
  ReproducibilityManifestDialog,
} from './ReproducibilityManifestDialog';

describe('ReproducibilityManifestDialog', () => {
  it('renders an accessible loading dialog for the selected run', () => {
    const markup = renderToStaticMarkup(
      <ReproducibilityManifestDialog accessToken="token" runId="run-01" onClose={vi.fn()} />,
    );

    expect(markup).toContain('role="dialog"');
    expect(markup).toContain('aria-modal="true"');
    expect(markup).toContain('Reproducibility manifest');
    expect(markup).toContain('run-01');
    expect(markup).toContain('Loading manifest');
    expect(markup).toContain('Close manifest');
  });

  it('returns manifest data or a safe load error', async () => {
    const manifest = { runId: 'run-01', codeRevision: 'abc123' };

    await expect(loadReproducibilityManifest('token', 'run-01', async () => manifest))
      .resolves.toEqual({ manifest, error: '' });
    await expect(loadReproducibilityManifest('token', 'run-01', async () => { throw new Error('Manifest unavailable.'); }))
      .resolves.toEqual({ manifest: null, error: 'Manifest unavailable.' });
  });

  it('creates a sanitized JSON download and revokes its object URL', () => {
    const createObjectUrl = vi.fn().mockReturnValue('blob:manifest');
    const revokeObjectUrl = vi.fn();

    const download = createReproducibilityManifestDownload(
      '../run 01',
      { runId: 'run-01' },
      { createObjectUrl, revokeObjectUrl },
    );

    expect(download.filename).toBe('run-01-reproducibility.json');
    expect(download.url).toBe('blob:manifest');
    expect(createObjectUrl).toHaveBeenCalledOnce();
    download.dispose();
    expect(revokeObjectUrl).toHaveBeenCalledWith('blob:manifest');
  });

  it('renders nothing without a selected run', () => {
    expect(renderToStaticMarkup(
      <ReproducibilityManifestDialog accessToken="token" runId={null} onClose={vi.fn()} />,
    )).toBe('');
  });
});