import { useEffect, useState } from 'react';
import type { ImageInfo } from '../../types/dataset';

function AuthorizedViewerImage({ accessToken, url, alt }: { accessToken: string; url: string; alt: string }) {
  const [objectUrl, setObjectUrl] = useState('');

  useEffect(() => {
    let cancelled = false;
    fetch(url, { headers: { Authorization: `Bearer ${accessToken}` } })
      .then((response) => (response.ok ? response.blob() : Promise.reject(new Error('Failed to load image'))))
      .then((blob) => { if (!cancelled) setObjectUrl(URL.createObjectURL(blob)); })
      .catch(() => { /* leave loading state */ });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [accessToken, url, objectUrl]);

  return objectUrl
    ? <img className="image-viewer__canvas" src={objectUrl} alt={alt} />
    : <span className="image-viewer__canvas" role="status">Loading…</span>;
}

interface DatasetImageViewerProps {
  accessToken: string;
  image: ImageInfo;
  imageIndex: number;
  imageCount: number;
  imageUrl: string;
  formatBytes: (bytes: number) => string;
  onClose: () => void;
  onPrevious: () => void;
  onNext: () => void;
  onDelete: () => void;
}

export function DatasetImageViewer({
  accessToken,
  image,
  imageIndex,
  imageCount,
  imageUrl,
  formatBytes,
  onClose,
  onPrevious,
  onNext,
  onDelete,
}: DatasetImageViewerProps) {
  return (
    <div className="image-viewer-overlay" role="dialog" aria-modal="true" aria-label="Image viewer">
      <div className="image-viewer">
        <div className="image-viewer__header">
          <span className="image-viewer__name">{image.filename}</span>
          <span className="image-viewer__meta">
            {image.widthPx && image.heightPx ? `${image.widthPx} × ${image.heightPx}` : ''} · {formatBytes(image.sizeBytes)}
          </span>
          <button type="button" className="image-viewer__close" aria-label="Close image viewer" onClick={onClose}>✕</button>
        </div>
        <AuthorizedViewerImage accessToken={accessToken} url={imageUrl} alt={image.filename} />
        <div className="image-viewer__footer">
          <button type="button" onClick={onPrevious} disabled={imageCount <= 1}>← Prev</button>
          <span>{imageIndex + 1} / {imageCount}</span>
          <button type="button" onClick={onNext} disabled={imageCount <= 1}>Next →</button>
          <button type="button" onClick={onDelete}>Delete</button>
        </div>
      </div>
    </div>
  );
}