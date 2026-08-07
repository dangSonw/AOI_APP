import { useEffect, useRef, useState } from 'react';

export type NameDialogKind = 'name' | 'filename';

interface NameDialogProps {
  title: string;
  label: string;
  kind?: NameDialogKind;
  initialValue?: string;
  placeholder?: string;
  helper?: string;
  showDescription?: boolean;
  descriptionLabel?: string;
  descriptionPlaceholder?: string;
  initialDescription?: string;
  confirmLabel?: string;
  onCancel: () => void;
  onSubmit: (value: string, description?: string) => void;
}

const NAME_RE = /^[a-z0-9]([a-z0-9-]*[a-z0-9])?$/;
const FILENAME_RE = /^[a-zA-Z0-9_-]+\.(png|jpg|jpeg|bmp|tiff|tif)$/;

export function NameDialog({
  title,
  label,
  kind = 'name',
  initialValue = '',
  placeholder,
  helper,
  showDescription = false,
  descriptionLabel = 'Description (optional)',
  descriptionPlaceholder = 'Describe this item…',
  initialDescription = '',
  confirmLabel = 'Create',
  onCancel,
  onSubmit,
}: NameDialogProps) {
  const [value, setValue] = useState(initialValue);
  const [description, setDescription] = useState(initialDescription);
  const [touched, setTouched] = useState(false);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    inputRef.current?.focus();
    inputRef.current?.select();
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onCancel();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onCancel]);

  const trimmed = value.trim();

  let validationMessage = '';
  if (touched && trimmed) {
    if (kind === 'name' && !NAME_RE.test(trimmed)) {
      validationMessage = 'Use lowercase letters, numbers and hyphens only (kebab-case).';
    } else if (kind === 'filename' && !FILENAME_RE.test(trimmed)) {
      validationMessage = 'Use letters, numbers, "-" or "_" with an image extension (.png, .jpg, .jpeg, .bmp, .tiff).';
    }
  }

  const isValid = trimmed.length > 0 && validationMessage === '';

  const handleSubmit = () => {
    setTouched(true);
    if (!isValid) return;
    onSubmit(trimmed, showDescription ? description.trim() : undefined);
  };

  return (
    <div className="dialog-overlay" role="dialog" aria-modal="true" aria-label={title}>
      <form
        className="dialog-card"
        onSubmit={(event) => { event.preventDefault(); handleSubmit(); }}
      >
        <h3 className="dialog-card__title">{title}</h3>

        <label className="dialog-card__field">
          <span>{label}</span>
          <input
            ref={inputRef}
            type="text"
            value={value}
            placeholder={placeholder ?? label}
            onChange={(event) => { setValue(event.target.value); setTouched(true); }}
          />
        </label>

        {helper && <p className="dialog-card__helper">{helper}</p>}

        {showDescription && (
          <label className="dialog-card__field">
            <span>{descriptionLabel}</span>
            <input
              type="text"
              value={description}
              placeholder={descriptionPlaceholder}
              onChange={(event) => setDescription(event.target.value)}
            />
          </label>
        )}

        {validationMessage && <p className="dialog-card__error">{validationMessage}</p>}

        <div className="dialog-card__actions">
          <button type="button" className="studio-secondary-button" onClick={onCancel}>
            Cancel
          </button>
          <button type="submit" className="studio-primary-button" disabled={!isValid}>
            {confirmLabel}
          </button>
        </div>
      </form>
    </div>
  );
}
