import { useEffect, useState } from 'react';
import type { ImageInfo } from '../../types/dataset';

function AuthorizedThumb({ accessToken, url, filename }: { accessToken: string; url: string; filename: string }) {
  const [objectUrl, setObjectUrl] = useState('');

  useEffect(() => {
    let cancelled = false;
    fetch(url, { headers: { Authorization: `Bearer ${accessToken}` } })
      .then((response) => (response.ok ? response.blob() : Promise.reject(new Error('Failed to load image'))))
      .then((blob) => {
        if (!cancelled) setObjectUrl(URL.createObjectURL(blob));
      })
      .catch(() => { /* leave placeholder */ });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [accessToken, url, objectUrl]);

  return objectUrl
    ? <img className="image-grid__thumb" src={objectUrl} alt={filename} draggable={false} />
    : <span className="image-grid__thumb image-grid__thumb--placeholder">{filename}</span>;
}

interface DatasetImageGridProps {
  accessToken: string;
  datasetName: string | null;
  categoryName: string | null;
  getImageUrl: (datasetName: string, categoryName: string, filename: string) => string;
  images: ImageInfo[];
  isLoading: boolean;
  onSelectImage: (image: ImageInfo) => void;
  onRenameImage: (filename: string) => void;
  onDeleteImage: (filename: string) => void;
}

export function DatasetImageGrid({
  accessToken,
  datasetName,
  categoryName,
  getImageUrl,
  images,
  isLoading,
  onSelectImage,
  onRenameImage,
  onDeleteImage,
}: DatasetImageGridProps) {
  return (
    <div className="image-grid" aria-live="polite">
      {isLoading && images.length === 0 && <p className="image-grid__empty" role="status">Loading images…</p>}
      {!isLoading && !categoryName && <p className="image-grid__empty">Select a category to view its images.</p>}
      {!isLoading && categoryName && images.length === 0 && <p className="image-grid__empty">No images in this category. Upload or import some.</p>}
      {images.map((image) => (
        <div className="image-grid__item" key={image.filename}>
          <button
            type="button"
            className="image-grid__thumb-button"
            onClick={() => onSelectImage(image)}
            aria-label={`View ${image.filename}`}
          >
            {datasetName && categoryName && (
              <AuthorizedThumb
                accessToken={accessToken}
                url={getImageUrl(datasetName, categoryName, image.filename)}
                filename={image.filename}
              />
            )}
          </button>
          <span className="image-grid__label" title={image.filename}>{image.filename}</span>
          <div className="image-grid__actions">
            <button type="button" onClick={() => onRenameImage(image.filename)}>Rename</button>
            <button type="button" onClick={() => onDeleteImage(image.filename)}>Delete</button>
          </div>
        </div>
      ))}
    </div>
  );
}