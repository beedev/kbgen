import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';

type ToastKind = 'success' | 'error' | 'info';

interface Toast {
  id: number;
  kind: ToastKind;
  text: string;
  ttl: number;
}

interface ToastCtx {
  push: (kind: ToastKind, text: string, ttl?: number) => void;
}

const ToasterContext = createContext<ToastCtx | null>(null);

export function useToast() {
  const ctx = useContext(ToasterContext);
  if (!ctx) {
    // Graceful no-op if used outside the provider. Avoids crashing pages
    // that render without the Toaster mounted (e.g. tests).
    return {
      push: (_k: ToastKind, _t: string) => {
        /* no-op */
      },
    };
  }
  return ctx;
}

export function Toaster({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  let nextId = 1;

  const push = useCallback<ToastCtx['push']>((kind, text, ttl = 4500) => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, kind, text, ttl }]);
  }, []);

  // auto-remove after ttl
  useEffect(() => {
    if (toasts.length === 0) return;
    const timers = toasts.map((t) =>
      setTimeout(() => setToasts((prev) => prev.filter((x) => x.id !== t.id)), t.ttl),
    );
    return () => timers.forEach(clearTimeout);
  }, [toasts]);

  return (
    <ToasterContext.Provider value={{ push }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 space-y-2 max-w-sm">
        {toasts.map((t) => (
          <ToastCard key={t.id} toast={t} onDismiss={() => setToasts((p) => p.filter((x) => x.id !== t.id))} />
        ))}
      </div>
    </ToasterContext.Provider>
  );
}

function ToastCard({ toast, onDismiss }: { toast: Toast; onDismiss: () => void }) {
  const tone: Record<ToastKind, { bg: string; border: string; dot: string; label: string }> = {
    success: {
      bg: 'bg-emerald-50',
      border: 'border-[var(--kbgen-success)]',
      dot: 'bg-[var(--kbgen-success)]',
      label: '✓',
    },
    error: {
      bg: 'bg-rose-50',
      border: 'border-[var(--kbgen-danger)]',
      dot: 'bg-[var(--kbgen-danger)]',
      label: '✕',
    },
    info: {
      bg: 'bg-[var(--kbgen-brand-light)]',
      border: 'border-[var(--kbgen-brand)]',
      dot: 'bg-[var(--kbgen-brand)]',
      label: 'i',
    },
  };
  const t = tone[toast.kind];
  return (
    <div
      className={`flex items-start gap-3 rounded-lg border ${t.border} ${t.bg} p-3 shadow-lg`}
      role="status"
    >
      <span
        className={`${t.dot} text-white rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold shrink-0`}
      >
        {t.label}
      </span>
      <p className="text-sm text-[var(--kbgen-text)] flex-1">{toast.text}</p>
      <button
        onClick={onDismiss}
        className="text-[var(--kbgen-text-muted)] hover:text-[var(--kbgen-text)] text-lg leading-none"
        aria-label="Dismiss"
      >
        ×
      </button>
    </div>
  );
}
