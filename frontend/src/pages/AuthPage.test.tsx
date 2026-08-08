import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { AuthPage } from './AuthPage';

describe('sign-in credential form', () => {
  it('exposes standard credential metadata to browser password managers', () => {
    const markup = renderToStaticMarkup(<AuthPage onAuthenticated={vi.fn()} />);

    expect(markup).toContain('name="username"');
    expect(markup).toContain('autoComplete="username"');
    expect(markup).toContain('name="password"');
    expect(markup).toContain('autoComplete="current-password"');
  });

  it('does not offer persistent sign-in', () => {
    const markup = renderToStaticMarkup(<AuthPage onAuthenticated={vi.fn()} />);

    expect(markup).not.toContain('Keep me signed in');
  });

  it('does not expose public account registration', () => {
    const markup = renderToStaticMarkup(<AuthPage onAuthenticated={vi.fn()} />);

    expect(markup).not.toContain('Create account');
    expect(markup).not.toContain('Create an account');
  });
});