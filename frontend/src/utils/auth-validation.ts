export interface AuthFieldErrors {
  email?: string;
  password?: string;
  fullName?: string;
  confirmPassword?: string;
}

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validateEmail(email: string): string | undefined {
  const normalizedEmail = email.trim();
  if (!normalizedEmail) {
    return 'Enter your work email.';
  }
  if (!EMAIL_PATTERN.test(normalizedEmail)) {
    return 'Enter a valid work email.';
  }
  return undefined;
}

export function validatePassword(password: string): string | undefined {
  if (!password) {
    return 'Enter your password.';
  }
  if (password.length < 8) {
    return 'Password must contain at least 8 characters.';
  }
  return undefined;
}

export function validateLogin(email: string, password: string): AuthFieldErrors {
  return {
    email: validateEmail(email),
    password: validatePassword(password),
  };
}

export function validateRegistration(
  email: string,
  fullName: string,
  password: string,
  confirmPassword: string,
): AuthFieldErrors {
  return {
    email: validateEmail(email),
    fullName: fullName.trim() ? undefined : 'Enter your full name.',
    password: validatePassword(password),
    confirmPassword: password === confirmPassword ? undefined : 'Passwords do not match.',
  };
}

export function hasValidationErrors(errors: AuthFieldErrors): boolean {
  return Object.values(errors).some(Boolean);
}