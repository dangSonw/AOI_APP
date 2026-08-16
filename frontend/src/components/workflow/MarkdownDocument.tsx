import type { ReactNode } from 'react';


interface MarkdownDocumentProps {
  markdown: string;
}

type MarkdownBlock =
  | { type: 'heading'; level: number; text: string }
  | { type: 'paragraph'; text: string }
  | { type: 'list'; ordered: boolean; items: string[] }
  | { type: 'table'; rows: string[][] }
  | { type: 'code'; language: string; value: string }
  | { type: 'quote'; text: string }
  | { type: 'rule' };

const HEADING_PATTERN = /^(#{1,6})\s+(.+)$/;
const UNORDERED_ITEM_PATTERN = /^\s*[-*+]\s+(.+)$/;
const ORDERED_ITEM_PATTERN = /^\s*\d+\.\s+(.+)$/;
const TABLE_DIVIDER_PATTERN = /^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$/;

function splitTableRow(line: string): string[] {
  return line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((cell) => cell.trim());
}

function startsBlock(lines: string[], index: number): boolean {
  const line = lines[index] ?? '';
  return !line.trim()
    || line.startsWith('```')
    || HEADING_PATTERN.test(line)
    || UNORDERED_ITEM_PATTERN.test(line)
    || ORDERED_ITEM_PATTERN.test(line)
    || /^>\s?/.test(line)
    || /^\s*(?:---+|___+|\*\*\*+)\s*$/.test(line)
    || Boolean(lines[index + 1] && TABLE_DIVIDER_PATTERN.test(lines[index + 1]));
}

export function parseMarkdown(markdown: string): MarkdownBlock[] {
  const lines = markdown.replace(/\r\n?/g, '\n').split('\n');
  const blocks: MarkdownBlock[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) {
      index += 1;
      continue;
    }

    if (line.startsWith('```')) {
      const language = line.slice(3).trim();
      const codeLines: string[] = [];
      index += 1;
      while (index < lines.length && !lines[index].startsWith('```')) {
        codeLines.push(lines[index]);
        index += 1;
      }
      if (index < lines.length) index += 1;
      blocks.push({ type: 'code', language, value: codeLines.join('\n') });
      continue;
    }

    const heading = line.match(HEADING_PATTERN);
    if (heading) {
      blocks.push({ type: 'heading', level: heading[1].length, text: heading[2] });
      index += 1;
      continue;
    }

    if (lines[index + 1] && TABLE_DIVIDER_PATTERN.test(lines[index + 1])) {
      const rows = [splitTableRow(line)];
      index += 2;
      while (index < lines.length && lines[index].includes('|') && lines[index].trim()) {
        rows.push(splitTableRow(lines[index]));
        index += 1;
      }
      blocks.push({ type: 'table', rows });
      continue;
    }

    const unorderedItem = line.match(UNORDERED_ITEM_PATTERN);
    const orderedItem = line.match(ORDERED_ITEM_PATTERN);
    if (unorderedItem || orderedItem) {
      const ordered = Boolean(orderedItem);
      const pattern = ordered ? ORDERED_ITEM_PATTERN : UNORDERED_ITEM_PATTERN;
      const items: string[] = [];
      while (index < lines.length) {
        const item = lines[index].match(pattern);
        if (!item) break;
        items.push(item[1]);
        index += 1;
      }
      blocks.push({ type: 'list', ordered, items });
      continue;
    }

    if (/^>\s?/.test(line)) {
      const quoteLines: string[] = [];
      while (index < lines.length && /^>\s?/.test(lines[index])) {
        quoteLines.push(lines[index].replace(/^>\s?/, ''));
        index += 1;
      }
      blocks.push({ type: 'quote', text: quoteLines.join(' ') });
      continue;
    }

    if (/^\s*(?:---+|___+|\*\*\*+)\s*$/.test(line)) {
      blocks.push({ type: 'rule' });
      index += 1;
      continue;
    }

    const paragraphLines = [line.trim()];
    index += 1;
    while (index < lines.length && !startsBlock(lines, index)) {
      paragraphLines.push(lines[index].trim());
      index += 1;
    }
    blocks.push({ type: 'paragraph', text: paragraphLines.join(' ') });
  }

  return blocks;
}

function safeHref(href: string): string | null {
  if (href.startsWith('#') || href.startsWith('/') || href.startsWith('./') || href.startsWith('../')) return href;
  try {
    const url = new URL(href);
    return ['http:', 'https:', 'mailto:'].includes(url.protocol) ? href : null;
  } catch {
    return null;
  }
}

function renderInline(text: string): ReactNode[] {
  const tokenPattern = /(`[^`]+`|\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\))/g;
  return text.split(tokenPattern).filter(Boolean).map((part, index) => {
    if (part.startsWith('`') && part.endsWith('`')) return <code key={index}>{part.slice(1, -1)}</code>;
    if (part.startsWith('**') && part.endsWith('**')) return <strong key={index}>{part.slice(2, -2)}</strong>;
    const link = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (link) {
      const href = safeHref(link[2]);
      return href
        ? <a key={index} href={href} target={href.startsWith('http') ? '_blank' : undefined} rel={href.startsWith('http') ? 'noreferrer' : undefined}>{link[1]}</a>
        : <span key={index}>{link[1]}</span>;
    }
    return part;
  });
}

export function MarkdownDocument({ markdown }: MarkdownDocumentProps) {
  const blocks = parseMarkdown(markdown);
  return (
    <article className="markdown-body">
      {blocks.map((block, index) => {
        if (block.type === 'heading') {
          const Heading = `h${block.level}` as keyof JSX.IntrinsicElements;
          return <Heading key={index}>{renderInline(block.text)}</Heading>;
        }
        if (block.type === 'paragraph') return <p key={index}>{renderInline(block.text)}</p>;
        if (block.type === 'list') {
          const List = block.ordered ? 'ol' : 'ul';
          return <List key={index}>{block.items.map((item, itemIndex) => <li key={itemIndex}>{renderInline(item)}</li>)}</List>;
        }
        if (block.type === 'table') return (
          <div className="markdown-body__table" key={index}>
            <table>
              <thead><tr>{block.rows[0].map((cell, cellIndex) => <th key={cellIndex}>{renderInline(cell)}</th>)}</tr></thead>
              <tbody>{block.rows.slice(1).map((row, rowIndex) => <tr key={rowIndex}>{row.map((cell, cellIndex) => <td key={cellIndex}>{renderInline(cell)}</td>)}</tr>)}</tbody>
            </table>
          </div>
        );
        if (block.type === 'code') return <pre key={index} data-language={block.language || undefined}><code>{block.value}</code></pre>;
        if (block.type === 'quote') return <blockquote key={index}>{renderInline(block.text)}</blockquote>;
        return <hr key={index} />;
      })}
    </article>
  );
}