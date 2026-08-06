import { renderToStaticMarkup } from 'react-dom/server';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import type { AuthSession } from './types/auth';

vi.mock('./pages/AuthPage', () => ({
  AuthPage: () => <div>Sign in screen</div>,
}));

vi.mock('./pages/WorkspacePage', () => ({
  WorkspacePage: () => <div>Workspace screen</div>,
}));

const SESSION_STORAGE_KEY = 'aoi-studio-session';
const STORED_SESSION: AuthSession = {
  accessToken: 'stored-token',
  tokenType: 'bearer',
  user: {
    id: 1,
    email: 'operator@aoi.local',
    fullName: 'AOI Operator',
    isActive: true,
  },
};

function createStorage(initialValues: Record<string, string> = {}): Storage {
  const values = new Map(Object.entries(initialValues));

  return {
    get length() {
      return values.size;
    },
    clear: () => values.clear(),
    getItem: (key) => values.get(key) ?? null,
    key: (index) => [...values.keys()][index] ?? null,
    removeItem: (key) => values.delete(key),
    setItem: (key, value) => values.set(key, value),
  };
}

beforeEach(() => {
  vi.stubGlobal('localStorage', createStorage());
  vi.stubGlobal('sessionStorage', createStorage());
});

describe('authentication session startup', () => {
  it('always starts at sign in when only a persistent session exists', () => {
    vi.stubGlobal('localStorage', createStorage({
      [SESSION_STORAGE_KEY]: JSON.stringify(STORED_SESSION),
    }));

    const markup = renderToStaticMarkup(<App />);

    expect(markup).toContain('Sign in screen');
    expect(localStorage.getItem(SESSION_STORAGE_KEY)).toBeNull();
  });

  it('restores the session after a refresh in the same tab', () => {
    vi.stubGlobal('sessionStorage', createStorage({
      [SESSION_STORAGE_KEY]: JSON.stringify(STORED_SESSION),
    }));

    const markup = renderToStaticMarkup(<App />);

    expect(markup).toContain('Workspace screen');
  });
});