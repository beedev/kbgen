import React from 'react';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';

const variants: Record<Variant, string> = {
  primary:
    'bg-[var(--kbgen-brand)] text-white hover:bg-[var(--kbgen-brand-dark)] disabled:opacity-50',
  secondary:
    'bg-[var(--kbgen-surface)] text-[var(--kbgen-text)] border border-[var(--kbgen-border)] hover:border-[var(--kbgen-text-muted)] disabled:opacity-50',
  ghost:
    'bg-transparent text-[var(--kbgen-text-secondary)] hover:bg-[var(--kbgen-border-light)] disabled:opacity-50',
  danger:
    'bg-[var(--kbgen-danger)] text-white hover:brightness-95 disabled:opacity-50',
};

export function Button({
  variant = 'primary',
  className = '',
  children,
  ...rest
}: {
  variant?: Variant;
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...rest}
      className={`inline-flex items-center justify-center rounded-md px-3 py-1.5 text-sm font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-[var(--kbgen-brand)]/40 ${variants[variant]} ${className}`}
    >
      {children}
    </button>
  );
}
