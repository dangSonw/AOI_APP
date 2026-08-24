import { useCallback, useEffect, useId, useRef, useState } from 'react';
import { readReproducibilityManifest } from '../../services/research-service';

interface ReproducibilityManifestDialogProps {
  accessToken: string;
  runId: string | null;
  onClose: () => void;
}

interface ManifestLoadResult {
  manifest: Record<string, unknown> | null;
  error: string;
}

interface ManifestDownloadDependencies {
  createObjectUrl: (blob: Blob) => string;
  revokeObjectUrl: (url: string) => void;
}

interface ManifestDownload {
  filename: string;
  url: string;
  dispose: () => void;
}

type ManifestReader = (
  accessToken: string,
  runId: string,
) => Promise<Record<string, unknown>>;

function sanitizeRunId(runId: string): string {
  return runId
    .toLocaleLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '') || 'research-run';
}

export async function loadReproducibilityManifest(
  accessToken: string,
  runId: string,
  reader: ManifestReader = readReproducibilityManifest,
): Promise<ManifestLoadResult> {
  try {
    return { manifest: await reader(accessToken, runId), error: '' };
  } catch (loadError) {
    return {
      manifest: null,
      error: loadError instanceof Error ? loadError.message : 'Reproducibility manifest could not be loaded.',
    };
  }
}

export function createReproducibilityManifestDownload(
  runId: string,
  manifest: Record<string, unknown>,
  dependencies: ManifestDownloadDependencies = {
    createObjectUrl: (blob) => URL.createObjectURL(blob),
    revokeObjectUrl: (url) => URL.revokeObjectURL(url),
  },
): ManifestDownload {
  const blob = new Blob([`${JSON.stringify(manifest, null, 2)}\n`], { type: 'application/json' });
  const url = dependencies.createObjectUrl(blob);
  return {
    filename: `${sanitizeRunId(runId)}-reproducibility.json`,
    url,
    dispose: () => dependencies.revokeObjectUrl(url),
  };
}

export function ReproducibilityManifestDialog({
  accessToken,
  runId,
  onClose,
}: ReproducibilityManifestDialogProps) {
  const titleId = useId();
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const [manifest, setManifest] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(Boolean(runId));
  const close = useCallback(() => onClose(), [onClose]);

  useEffect(() => {
    if (!runId) return undefined;
    const previouslyFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') close();
    };
    document.addEventListener('keydown', closeOnEscape);
    closeButtonRef.current?.focus();
    return () => {
      document.removeEventListener('keydown', closeOnEscape);
      previouslyFocused?.focus();
    };
  }, [close, runId]);

  useEffect(() => {
    if (!runId) return undefined;
    let isCancelled = false;
    setManifest(null);
    setError('');
    setIsLoading(true);
    void loadReproducibilityManifest(accessToken, runId).then((result) => {
      if (isCancelled) return;
      setManifest(result.manifest);
      setError(result.error);
      setIsLoading(false);
    });
    return () => { isCancelled = true; };
  }, [accessToken, runId]);

  if (!runId) return null;

  const download = () => {
    if (!manifest) return;
    const resource = createReproducibilityManifestDownload(runId, manifest);
    const anchor = document.createElement('a');
    anchor.href = resource.url;
    anchor.download = resource.filename;
    anchor.click();
    resource.dispose();
  };

  return (
    <div className="node-documentation__overlay" onMouseDown={(event) => { if (event.target === event.currentTarget) close(); }}>
      <section className="node-documentation research-manifest" role="dialog" aria-modal="true" aria-labelledby={titleId}>
        <header className="node-documentation__header">
          <div><span className="overline">Research run</span><h2 id={titleId}>Reproducibility manifest</h2><code>{runId}</code></div>
          <button ref={closeButtonRef} type="button" className="node-documentation__close" onClick={close} aria-label="Close manifest">×</button>
        </header>
        <div className="node-documentation__content" aria-live="polite">
          {isLoading && <p className="node-documentation__state">Loading manifest…</p>}
          {error && <p className="studio-message studio-message--error" role="alert">{error}</p>}
          {!isLoading && !error && manifest && <>
            <button type="button" className="primary-button" onClick={download}>Download JSON</button>
            <details><summary>Advanced raw manifest</summary><pre>{JSON.stringify(manifest, null, 2)}</pre></details>
          </>}
        </div>
      </section>
    </div>
  );
}