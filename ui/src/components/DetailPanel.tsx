import React, { useEffect } from 'react';

export function DetailPanel({
  open,
  onClose,
  title,
  children,
  footer,
  width = 'max-w-3xl',
}: {
  open: boolean;
  onClose: () => void;
  title: React.ReactNode;
  children: React.ReactNode;
  footer?: React.ReactNode;
  width?: string;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <>
      <div
        className="fixed inset-0 bg-black/30 z-40"
        onClick={onClose}
        aria-hidden
      />
      <aside
        className={`fixed right-0 top-0 bottom-0 z-50 w-full ${width} bg-[var(--kbgen-surface)] shadow-xl flex flex-col`}
        role="dialog"
        aria-modal="true"
      >
        <header className="flex items-start justify-between gap-3 border-b border-[var(--kbgen-border)] px-5 py-3">
          <h2 className="text-base font-semibold text-[var(--kbgen-text)] truncate">{title}</h2>
          <button
            onClick={onClose}
            className="text-[var(--kbgen-text-muted)] hover:text-[var(--kbgen-text)] text-lg leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </header>
        <div className="flex-1 overflow-y-auto px-5 py-4">{children}</div>
        {footer && (
          <footer className="border-t border-[var(--kbgen-border)] px-5 py-3">{footer}</footer>
        )}
      </aside>
    </>
  );
}
