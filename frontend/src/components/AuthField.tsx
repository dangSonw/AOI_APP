interface AuthFieldProps {
  id: string;
  label: string;
  type?: 'email' | 'password' | 'text';
  value: string;
  autoComplete: string;
  placeholder?: string;
  error?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  onChange: (value: string) => void;
}

export function AuthField({
  id,
  label,
  type = 'text',
  value,
  autoComplete,
  placeholder,
  error,
  action,
  onChange,
}: AuthFieldProps) {
  const errorId = `${id}-error`;

  return (
    <div className="auth-field">
      <div className="auth-field__heading">
        <label htmlFor={id}>{label}</label>
        {action && (
          <button className="auth-field__action" type="button" onClick={action.onClick}>
            {action.label}
          </button>
        )}
      </div>
      <input
        id={id}
        type={type}
        value={value}
        autoComplete={autoComplete}
        placeholder={placeholder}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? errorId : undefined}
        onChange={(event) => onChange(event.target.value)}
      />
      {error && <p id={errorId} className="auth-field__error">{error}</p>}
    </div>
  );
}