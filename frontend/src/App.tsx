import { useEffect, useState } from 'react';
import { AuthPage } from './pages/AuthPage';
import { WorkspacePage } from './pages/WorkspacePage';
import type { AuthSession } from './types/auth';

const SESSION_STORAGE_KEY = 'aoi-studio-session';

function loadStoredSession(): AuthSession | null {
  const storedSession = localStorage.getItem(SESSION_STORAGE_KEY)
    ?? sessionStorage.getItem(SESSION_STORAGE_KEY);

  if (!storedSession) {
    return null;
  }

  try {
    return JSON.parse(storedSession) as AuthSession;
  } catch {
    localStorage.removeItem(SESSION_STORAGE_KEY);
    sessionStorage.removeItem(SESSION_STORAGE_KEY);
    return null;
  }
}

export default function App() {
  const [session, setSession] = useState<AuthSession | null>(loadStoredSession);

  useEffect(() => {
    document.title = session ? 'Inspection Workspace | AOI Studio' : 'Sign in | AOI Studio';
  }, [session]);

  const handleAuthenticated = (nextSession: AuthSession, shouldPersist: boolean) => {
    const storage = shouldPersist ? localStorage : sessionStorage;
    const alternateStorage = shouldPersist ? sessionStorage : localStorage;

    alternateStorage.removeItem(SESSION_STORAGE_KEY);
    storage.setItem(SESSION_STORAGE_KEY, JSON.stringify(nextSession));
    setSession(nextSession);
  };

  const handleSignOut = () => {
    localStorage.removeItem(SESSION_STORAGE_KEY);
    sessionStorage.removeItem(SESSION_STORAGE_KEY);
    setSession(null);
  };

  return session ? (
    <WorkspacePage session={session} onSignOut={handleSignOut} />
  ) : (
    <AuthPage onAuthenticated={handleAuthenticated} />
  );
}
