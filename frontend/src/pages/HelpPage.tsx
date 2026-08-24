import { useMemo, useState } from 'react';
import type { WorkspaceView } from '../types/workspace';
import { HELP_CONTENT, type HelpIllustration, type HelpLanguage } from './help-content';

const HELP_LANGUAGE_KEY = 'aoi-help-language';

interface HelpPageProps {
  onOpenWorkspace: (view: WorkspaceView) => void;
}

function readInitialLanguage(): HelpLanguage {
  if (typeof window === 'undefined') return 'vi';
  try {
    return window.localStorage.getItem(HELP_LANGUAGE_KEY) === 'en' ? 'en' : 'vi';
  } catch {
    return 'vi';
  }
}

function HelpIllustrationCard({ type, label }: { type: HelpIllustration; label: string }) {
  if (type === 'workflow') {
    return <figure className="help-illustration help-illustration--workflow" aria-label={label}><div className="help-node">Camera<small>image</small></div><span aria-hidden="true">→</span><div className="help-node">Preprocess<small>tensor</small></div><span aria-hidden="true">→</span><div className="help-node help-node--accent">Inspector<small>result</small></div><figcaption>Input → node graph → validated output</figcaption></figure>;
  }
  if (type === 'research') {
    return <figure className="help-illustration" aria-label={label}><div className="help-run"><span>RUN-042</span><b>Completed</b><i style={{ width: '88%' }} /><i style={{ width: '67%' }} /><small>metrics · lineage · artifacts</small></div><div className="help-run help-run--compare"><span>RUN-039</span><b>Compare</b><i style={{ width: '74%' }} /><i style={{ width: '81%' }} /><small>seed · revision · environment</small></div><figcaption>Compare evidence, not only a single metric</figcaption></figure>;
  }
  if (type === 'models') {
    return <figure className="help-illustration help-illustration--lifecycle" aria-label={label}><span className="help-alias help-alias--version">v3</span><span aria-hidden="true">→</span><span className="help-alias help-alias--candidate">Candidate</span><span aria-hidden="true">→</span><span className="help-alias help-alias--champion">Champion</span><span className="help-rollback">↶ Rollback</span><figcaption>Immutable version and governed aliases</figcaption></figure>;
  }
  if (type === 'overview') {
    return <figure className="help-illustration help-illustration--journey" aria-label={label}><div><span>01</span><b>Hardware</b></div><i /><div><span>02</span><b>Workflow</b></div><i /><div><span>03</span><b>Research</b></div><i /><div><span>04</span><b>Models</b></div><i /><div><span>05</span><b>Inspect</b></div><figcaption>Configure → build → evaluate → govern → operate</figcaption></figure>;
  }
  return <figure className="help-illustration help-illustration--workspace" aria-label={label}><div className="help-mini-sidebar"><i /><i /><i /><i /></div><div className="help-mini-canvas"><span /><div><i /><i /><i /></div><b /></div><figcaption>Every workspace keeps navigation, status, and actions visible</figcaption></figure>;
}

export function HelpPage({ onOpenWorkspace }: HelpPageProps) {
  const [language, setLanguage] = useState<HelpLanguage>(readInitialLanguage);
  const [query, setQuery] = useState('');
  const document = HELP_CONTENT[language];
  const visibleSections = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase();
    if (!normalizedQuery) return document.sections;
    return document.sections.filter((section) => [section.title, section.eyebrow, section.summary, ...section.steps, ...section.tips].join(' ').toLocaleLowerCase().includes(normalizedQuery));
  }, [document.sections, query]);

  const changeLanguage = (nextLanguage: HelpLanguage) => {
    setLanguage(nextLanguage);
    try { window.localStorage.setItem(HELP_LANGUAGE_KEY, nextLanguage); } catch { /* Browser storage can be unavailable. */ }
  };

  return (
    <section className="help-page" aria-label={language === 'vi' ? 'Trợ giúp AOI Studio' : 'AOI Studio help'} lang={language}>
      <header className="help-toolbar">
        <div className="help-tools">
          <label htmlFor="help-search">{document.searchLabel}</label>
          <input id="help-search" type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder={document.searchPlaceholder} />
          <div className="help-language" role="group" aria-label="Language / Ngôn ngữ">
            <button type="button" aria-pressed={language === 'vi'} onClick={() => changeLanguage('vi')}>Tiếng Việt</button>
            <button type="button" aria-pressed={language === 'en'} onClick={() => changeLanguage('en')}>English</button>
          </div>
        </div>
      </header>

      <div className="help-layout">
        <nav className="help-toc" aria-label={document.contentsLabel}>
          <strong>{document.contentsLabel}</strong>
          {visibleSections.map((section, index) => <a href={`#help-${section.id}`} key={section.id}><span>{String(index + 1).padStart(2, '0')}</span>{section.title}</a>)}
        </nav>
        <div className="help-content" aria-live="polite">
          {visibleSections.map((section) => (
            <article className="help-section" id={`help-${section.id}`} key={section.id}>
              <div className="help-section__copy">
                <span className="section-kicker">{section.eyebrow}</span>
                <h2>{section.title}</h2>
                <p className="help-section__summary">{section.summary}</p>
                <ol>{section.steps.map((step) => <li key={step}>{step}</li>)}</ol>
                <aside className="help-tip"><strong>{language === 'vi' ? 'Lưu ý vận hành' : 'Operational notes'}</strong><ul>{section.tips.map((tip) => <li key={tip}>{tip}</li>)}</ul></aside>
                {section.view && <button data-workspace-action={section.view} className="help-open-button" type="button" onClick={() => onOpenWorkspace(section.view!)}>{document.openLabel}: {section.viewLabel}</button>}
              </div>
              <HelpIllustrationCard type={section.illustration} label={`${document.diagramLabel}: ${section.title}`} />
            </article>
          ))}
          {visibleSections.length === 0 && <div className="workflow-empty" role="status"><strong>{document.noResults}</strong></div>}
        </div>
      </div>
    </section>
  );
}