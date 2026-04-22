import React, { useState } from 'react';

export interface NavItem {
  label: string;
  href: string;
  icon?: string;
  section?: boolean; // header, not clickable
  disabled?: boolean;
  active?: boolean;
}

export function PageLayout({
  appName,
  subtitle,
  navItems,
  onNavigate,
  actions,
  userMenu,
  children,
}: {
  appName: string;
  subtitle?: string;
  navItems: NavItem[];
  onNavigate: (href: string) => void;
  actions?: React.ReactNode;
  userMenu?: React.ReactNode;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(true);

  return (
    <div className="flex h-screen">
      <aside
        className={`${open ? 'w-64' : 'w-14'} flex flex-col border-r border-[var(--kbgen-border)] bg-[var(--kbgen-surface)] transition-[width] duration-150`}
      >
        <div className="h-14 flex items-center gap-2 px-3 border-b border-[var(--kbgen-border)]">
          <button
            onClick={() => setOpen((o) => !o)}
            className="w-8 h-8 rounded hover:bg-[var(--kbgen-border-light)] text-[var(--kbgen-text-secondary)]"
            aria-label="Toggle sidebar"
          >
            ☰
          </button>
          {open && (
            <div className="min-w-0">
              <p className="text-sm font-bold text-[var(--kbgen-text)] truncate">{appName}</p>
              {subtitle && (
                <p className="text-[10px] text-[var(--kbgen-text-muted)] truncate">{subtitle}</p>
              )}
            </div>
          )}
        </div>

        <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-0.5">
          {navItems.map((item, i) => {
            if (item.section) {
              return open ? (
                <p
                  key={i}
                  className="px-2 pt-3 pb-1 text-[9px] font-bold uppercase tracking-widest text-[var(--kbgen-text-muted)]"
                >
                  {item.label}
                </p>
              ) : null;
            }
            return (
              <button
                key={i}
                disabled={item.disabled}
                onClick={() => onNavigate(item.href)}
                title={item.disabled ? 'Coming in MVP2' : item.label}
                className={`w-full flex items-center gap-2 rounded px-3 py-2 text-sm font-medium transition-colors ${
                  item.active
                    ? 'bg-[var(--kbgen-brand-light)] text-[var(--kbgen-brand)]'
                    : item.disabled
                      ? 'text-[var(--kbgen-text-muted)] opacity-60 cursor-not-allowed'
                      : 'text-[var(--kbgen-text-secondary)] hover:bg-[var(--kbgen-border-light)] hover:text-[var(--kbgen-text)]'
                }`}
              >
                {item.icon && <span className="shrink-0">{item.icon}</span>}
                {open && <span className="truncate text-left">{item.label}</span>}
              </button>
            );
          })}
        </nav>

        {userMenu && open && (
          <div className="border-t border-[var(--kbgen-border)] p-3">{userMenu}</div>
        )}
      </aside>

      <main className="flex-1 flex flex-col overflow-hidden">
        {actions && (
          <div className="flex items-center justify-end gap-2 border-b border-[var(--kbgen-border)] bg-[var(--kbgen-surface)] px-6 py-2">
            {actions}
          </div>
        )}
        <div className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-7xl px-6 py-6">{children}</div>
        </div>
      </main>
    </div>
  );
}
