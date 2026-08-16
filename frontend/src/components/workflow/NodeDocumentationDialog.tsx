import { useCallback, useEffect, useId, useRef, useState } from 'react';
import { readAlgorithmDocumentation } from '../../services/workflow-service';
import type { AlgorithmDefinition, DocumentationLanguage } from '../../types/workflow';
import { MarkdownDocument } from './MarkdownDocument';


interface NodeDocumentationDialogProps {
  accessToken: string;
  definition: AlgorithmDefinition | null;
  onClose: () => void;
}

export function NodeDocumentationDialog({ accessToken, definition, onClose }: NodeDocumentationDialogProps) {
  const titleId = useId();
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const [language, setLanguage] = useState<DocumentationLanguage>('vi');
  const [markdown, setMarkdown] = useState('');
  const [resolvedLanguage, setResolvedLanguage] = useState<DocumentationLanguage>('vi');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const close = useCallback(() => onClose(), [onClose]);

  useEffect(() => {
    if (!definition) return undefined;
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
  }, [close, definition]);

  useEffect(() => {
    setLanguage('vi');
  }, [definition?.id]);

  useEffect(() => {
    if (!definition) return undefined;
    let ignore = false;
    setIsLoading(true);
    setError('');
    setMarkdown('');
    void readAlgorithmDocumentation(accessToken, definition.id, language)
      .then((documentation) => {
        if (ignore) return;
        setMarkdown(documentation.content);
        setResolvedLanguage(documentation.language);
      })
      .catch((documentationError) => {
        if (!ignore) setError(documentationError instanceof Error ? documentationError.message : 'Node documentation could not be loaded.');
      })
      .finally(() => {
        if (!ignore) setIsLoading(false);
      });
    return () => { ignore = true; };
  }, [accessToken, definition, language]);

  if (!definition) return null;

  return (
    <div className="node-documentation__overlay" onMouseDown={(event) => { if (event.target === event.currentTarget) close(); }}>
      <section className="node-documentation" role="dialog" aria-modal="true" aria-labelledby={titleId}>
        <header className="node-documentation__header">
          <div>
            <span className="overline">Node README</span>
            <h2 id={titleId}>{definition.name}</h2>
            <code>{definition.id}</code>
          </div>
          <button ref={closeButtonRef} type="button" className="node-documentation__close" onClick={close} aria-label={language === 'vi' ? 'Đóng tài liệu' : 'Close documentation'}>×</button>
        </header>
        <nav className="node-documentation__languages" aria-label={language === 'vi' ? 'Ngôn ngữ tài liệu' : 'Documentation language'}>
          <button type="button" className={language === 'vi' ? 'is-active' : ''} aria-pressed={language === 'vi'} onClick={() => setLanguage('vi')}>Tiếng Việt</button>
          <button type="button" className={language === 'en' ? 'is-active' : ''} aria-pressed={language === 'en'} onClick={() => setLanguage('en')}>English</button>
        </nav>
        <div className="node-documentation__content" aria-live="polite">
          {isLoading && <p className="node-documentation__state">{language === 'vi' ? 'Đang tải tài liệu…' : 'Loading documentation…'}</p>}
          {error && <p className="studio-message studio-message--error" role="alert">{error}</p>}
          {!isLoading && !error && resolvedLanguage !== language && <p className="studio-message">Vietnamese README is unavailable. Showing English documentation.</p>}
          {!isLoading && !error && markdown && <MarkdownDocument markdown={markdown} />}
        </div>
      </section>
    </div>
  );
}