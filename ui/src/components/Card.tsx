import React from 'react';

export function Card({
  children,
  className = '',
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-lg border border-[var(--kbgen-border)] bg-[var(--kbgen-surface)] shadow-sm ${className}`}
    >
      {children}
    </div>
  );
}
