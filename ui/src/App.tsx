import React, { useEffect, useState } from 'react';
import { PageLayout, type NavItem } from './components/PageLayout';
import { Dashboard } from './pages/Dashboard';
import { Workspace } from './pages/Workspace';
import { SearchPage } from './pages/Search';
import { SystemStatus } from './pages/admin/SystemStatus';

type Persona = 'operator' | 'admin';

// BASE — when kbgen is reverse-proxied at a non-root path, Vite bakes this
// prefix into the bundle at build time. We strip it from `location.pathname`
// before routing (so routes stay root-relative in code) and re-add it when
// pushing state so the browser URL stays under the proxied path.
const RAW_BASE = import.meta.env.BASE_URL || '/';
const BASE = RAW_BASE === '/' ? '' : RAW_BASE.replace(/\/+$/, '');

function stripBase(p: string): string {
  if (!BASE) return p || '/';
  if (p === BASE) return '/';
  if (p.startsWith(`${BASE}/`)) return p.slice(BASE.length) || '/';
  return p || '/';
}

function withBase(p: string): string {
  if (!BASE) return p;
  if (p.startsWith(BASE)) return p;
  return `${BASE}${p.startsWith('/') ? p : `/${p}`}`;
}

const operatorNav: NavItem[] = [
  { label: 'Dashboard', href: '/' },
  { label: 'Workspace', href: '/workspace' },
  { label: 'Search', href: '/search' },
];

const adminNav: NavItem[] = [{ label: 'System Status', href: '/admin' }];

function renderPage(path: string, navigate: (p: string) => void): React.ReactNode {
  if (path === '/') return <Dashboard onNavigate={navigate} />;
  if (path === '/workspace') return <Workspace />;
  if (path === '/search') return <SearchPage />;
  if (path === '/admin') return <SystemStatus />;
  return (
    <div className="p-8 text-[var(--kbgen-text-secondary)]">Page not found: {path}</div>
  );
}

function PersonaSwitcher({
  persona,
  onChange,
}: {
  persona: Persona;
  onChange: (p: Persona) => void;
}) {
  return (
    <div>
      <p className="text-[9px] font-bold uppercase tracking-widest text-[var(--kbgen-text-muted)] mb-2">
        Persona
      </p>
      <div className="flex rounded-md overflow-hidden border border-[var(--kbgen-border)]">
        {(['operator', 'admin'] as Persona[]).map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => onChange(p)}
            aria-pressed={persona === p}
            className={`flex-1 py-1.5 text-xs font-bold capitalize transition-colors ${
              persona === p
                ? 'bg-[var(--kbgen-brand)] text-white'
                : 'bg-[var(--kbgen-surface)] text-[var(--kbgen-text-secondary)] hover:bg-[var(--kbgen-border-light)]'
            }`}
          >
            {p}
          </button>
        ))}
      </div>
      <p className="text-[10px] text-[var(--kbgen-text-muted)] mt-1.5 leading-tight">
        {persona === 'operator'
          ? 'Reviewers & knowledge managers'
          : 'Config + ops + pipeline tuning'}
      </p>
    </div>
  );
}

export function App() {
  const [currentPath, setCurrentPathState] = useState<string>(
    typeof window !== 'undefined' ? stripBase(window.location.pathname || '/') : '/',
  );
  const [persona, setPersona] = useState<Persona>(
    typeof window !== 'undefined'
      ? ((localStorage.getItem('kbgen.persona') as Persona) ?? 'operator')
      : 'operator',
  );

  const setCurrentPath = (p: string) => {
    if (typeof window !== 'undefined') {
      window.history.pushState({}, '', withBase(p));
      setCurrentPathState(stripBase(window.location.pathname || '/'));
    } else {
      setCurrentPathState(p.split('?')[0] || '/');
    }
  };

  const setPersonaPersistent = (p: Persona) => {
    setPersona(p);
    if (typeof window !== 'undefined') localStorage.setItem('kbgen.persona', p);
    setCurrentPath(p === 'admin' ? '/admin' : '/');
  };

  useEffect(() => {
    const onPop = () => setCurrentPathState(stripBase(window.location.pathname || '/'));
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  const primary = persona === 'admin' ? adminNav : operatorNav;
  const nav: NavItem[] = primary.map((item) => ({
    ...item,
    active: item.href === currentPath,
  }));

  const appName = persona === 'admin' ? 'KB Portal · Admin' : 'KB Portal';
  const subtitle =
    persona === 'admin' ? 'AI config · data · readiness' : 'Always Current, Always Accurate';

  return (
    <PageLayout
      appName={appName}
      subtitle={subtitle}
      navItems={nav}
      userMenu={<PersonaSwitcher persona={persona} onChange={setPersonaPersistent} />}
      onNavigate={(href) => {
        if (href.startsWith('#')) return;
        setCurrentPath(href);
      }}
    >
      {renderPage(currentPath, setCurrentPath)}
    </PageLayout>
  );
}
