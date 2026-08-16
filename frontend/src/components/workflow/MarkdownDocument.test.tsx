import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { MarkdownDocument, parseMarkdown } from './MarkdownDocument';


describe('MarkdownDocument', () => {
  it('parses node README headings, lists, tables, and code without raw HTML injection', () => {
    const markdown = `# Camera capture node

Use **Camera capture** with \`image\` data and [docs](https://example.com/docs).

| Field | Value |
|---|---|
| Node ID | \`camera-capture\` |

1. Add node.
2. Save workflow.

<script>alert('unsafe')</script>`;
    const markup = renderToStaticMarkup(<MarkdownDocument markdown={markdown} />);

    expect(markup).toContain('<h1>Camera capture node</h1>');
    expect(markup).toContain('<strong>Camera capture</strong>');
    expect(markup).toContain('<code>image</code>');
    expect(markup).toContain('<table>');
    expect(markup).toContain('<ol>');
    expect(markup).toContain('target="_blank"');
    expect(markup).toContain('&lt;script&gt;');
    expect(markup).not.toContain('<script>');
  });

  it('parses fenced code and blockquotes', () => {
    const blocks = parseMarkdown('> Safety note\n\n```json\n{"ok": true}\n```');

    expect(blocks).toEqual([
      { type: 'quote', text: 'Safety note' },
      { type: 'code', language: 'json', value: '{"ok": true}' },
    ]);
  });
});