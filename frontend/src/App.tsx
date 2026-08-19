import { useEffect, useState } from 'react';
import { AuthPage } from './pages/AuthPage';
import { WorkspacePage } from './pages/WorkspacePage';
import { apiRequest } from './services/api-client';
import type { AuthSession } from './types/auth';

const SESSION_STORAGE_KEY = 'aoi-studio-session';

function loadStoredSession(): AuthSession | null {
  localStorage.removeItem(SESSION_STORAGE_KEY);
  const storedSession = sessionStorage.getItem(SESSION_STORAGE_KEY);

  if (!storedSession) {
    return null;
  }

  try {
    return JSON.parse(storedSession) as AuthSession;
  } catch {
    sessionStorage.removeItem(SESSION_STORAGE_KEY);
    return null;
  }
}

export default function App() {
  const [session, setSession] = useState<AuthSession | null>(loadStoredSession);
  const isDebugAutoLogin = import.meta.env.VITE_AOI_DEBUG_AUTO_LOGIN === '1'
    || import.meta.env.VITE_AOI_SIMULATOR_NO_BROWSER === '1';
  const [isDebugSessionLoading, setIsDebugSessionLoading] = useState(isDebugAutoLogin);
  const [debugSessionError, setDebugSessionError] = useState('');

  useEffect(() => {
    if (session || !isDebugAutoLogin) {
      setIsDebugSessionLoading(false);
      return;
    }
    let isCurrent = true;
    apiRequest<AuthSession>('/api/auth/debug-session', { method: 'POST' })
      .then((nextSession) => {
        if (!isCurrent) return;
        sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(nextSession));
        setSession(nextSession);
      })
      .catch((error: unknown) => {
        if (!isCurrent) return;
        setDebugSessionError(error instanceof Error ? error.message : 'The debug session could not be created.');
        setIsDebugSessionLoading(false);
      });
    return () => { isCurrent = false; };
  }, [isDebugAutoLogin, session]);

  useEffect(() => {
    document.title = session ? 'Inspection Workspace | AOI Studio' : 'Sign in | AOI Studio';
  }, [session]);

  const handleAuthenticated = (nextSession: AuthSession) => {
    sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(nextSession));
    setSession(nextSession);
  };

  const handleSignOut = () => {
    sessionStorage.removeItem(SESSION_STORAGE_KEY);
    setSession(null);
  };

  if (isDebugSessionLoading && !session) {
    return <main className="auth-page" aria-live="polite">Opening debug workspace…</main>;
  }

  if (debugSessionError && !session) {
    return <main className="auth-page"><p className="form-message form-message--error" role="alert">Debug auto-login failed: {debugSessionError}</p></main>;
  }

  return session ? (
    <WorkspacePage session={session} onSignOut={handleSignOut} />
  ) : (
    <AuthPage onAuthenticated={handleAuthenticated} />
  );
}
