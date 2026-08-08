import { type FormEvent, useEffect, useState } from 'react';
import { AuthField } from '../components/AuthField';
import { requestPasswordReset, signIn } from '../services/auth-service';
import type { AuthSession } from '../types/auth';
import {
  type AuthFieldErrors,
  hasValidationErrors,
  validateEmail,
  validateLogin,
} from '../utils/auth-validation';

type AuthMode = 'sign-in' | 'forgot-password';

interface AuthPageProps {
  onAuthenticated: (session: AuthSession) => void;
}

export function AuthPage({ onAuthenticated }: AuthPageProps) {
  const [mode, setMode] = useState<AuthMode>('sign-in');
  const [email, setEmail] = useState('admin@aoi.local');
  const [password, setPassword] = useState('');
  const [isPasswordVisible, setIsPasswordVisible] = useState(false);
  const [errors, setErrors] = useState<AuthFieldErrors>({});
  const [formError, setFormError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const modeTitles: Record<AuthMode, string> = {
      'sign-in': 'Sign in',
      'forgot-password': 'Reset password',
    };
    document.title = `${modeTitles[mode]} | AOI Studio`;
  }, [mode]);

  const switchMode = (nextMode: AuthMode) => {
    setMode(nextMode);
    setErrors({});
    setFormError('');
    setSuccessMessage('');
    setPassword('');
  };

  const submitSignIn = async () => {
    const nextErrors = validateLogin(email, password);
    setErrors(nextErrors);
    if (hasValidationErrors(nextErrors)) {
      return;
    }

    const session = await signIn({ email: email.trim(), password });
    onAuthenticated(session);
  };

  const submitPasswordReset = async () => {
    const emailError = validateEmail(email);
    setErrors({ email: emailError });
    if (emailError) {
      return;
    }

    const response = await requestPasswordReset(email.trim());
    setSuccessMessage(response.message);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError('');
    setSuccessMessage('');
    setIsSubmitting(true);

    try {
      if (mode === 'sign-in') {
        await submitSignIn();
      } else {
        await submitPasswordReset();
      }
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'The request could not be completed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="auth-page">
      <section className={`auth-card auth-card--${mode}`} aria-labelledby="auth-title">
        <header className="auth-card__header">
          <p className="auth-card__brand">AOI STUDIO</p>
          <h1 id="auth-title">
            {mode === 'sign-in' && 'Welcome back'}
            {mode === 'forgot-password' && 'Forgot password?'}
          </h1>
          <p className="auth-card__subtitle">
            {mode === 'sign-in' && 'Sign in to continue to your inspection workspace.'}
            {mode === 'forgot-password' && 'Enter your work email to receive a password reset link.'}
          </p>
        </header>

        <form className="auth-form" noValidate onSubmit={handleSubmit}>
          <AuthField
            id="work-email"
            name={mode === 'sign-in' ? 'username' : 'email'}
            label="Work email"
            type="email"
            value={email}
            autoComplete={mode === 'sign-in' ? 'username' : 'email'}
            placeholder="admin@aoi.local"
            error={errors.email}
            onChange={setEmail}
          />

          {mode !== 'forgot-password' && (
            <AuthField
              id="password"
              name="password"
              label="Password"
              type={isPasswordVisible ? 'text' : 'password'}
              value={password}
              autoComplete={mode === 'sign-in' ? 'current-password' : 'new-password'}
              placeholder="Enter your password"
              error={errors.password}
              action={{
                label: isPasswordVisible ? 'Hide' : 'Show',
                onClick: () => setIsPasswordVisible((isVisible) => !isVisible),
              }}
              onChange={setPassword}
            />
          )}

          {mode === 'sign-in' && (
            <div className="auth-form__options">
              <button className="text-button" type="button" onClick={() => switchMode('forgot-password')}>
                Forgot password?
              </button>
            </div>
          )}

          {formError && <p className="form-message form-message--error" role="alert">{formError}</p>}
          {successMessage && <p className="form-message form-message--success" role="status">{successMessage}</p>}

          <button className="primary-button" type="submit" disabled={isSubmitting}>
            {isSubmitting && <span className="button-spinner" aria-hidden="true" />}
            {mode === 'sign-in' && (isSubmitting ? 'Signing in…' : 'Sign in')}
            {mode === 'forgot-password' && (isSubmitting ? 'Sending link…' : 'Send reset link')}
          </button>

          {mode === 'forgot-password' && (
            <button className="back-button" type="button" onClick={() => switchMode('sign-in')}>
              <span aria-hidden="true">←</span> Back to sign in
            </button>
          )}
        </form>
      </section>
    </main>
  );
}