import { useEffect, useState } from 'react';
import { AuthPage } from './pages/AuthPage';
import { WorkspacePage } from './pages/WorkspacePage';
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

  return session ? (
    <WorkspacePage session={session} onSignOut={handleSignOut} />
  ) : (
    <AuthPage onAuthenticated={handleAuthenticated} />
  );
}
