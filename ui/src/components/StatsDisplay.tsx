import React from 'react';

export interface Stat {
  label: string;
  value: number | string | undefined;
  format?: 'number' | 'percent' | 'currency';
  delta?: { value: number; label?: string };
  onClick?: () => void;
}

function fmt(v: Stat['value'], f: Stat['format']): string {
  if (v == null) return '—';
  if (typeof v === 'string') return v;
  if (f === 'percent') return `${v.toFixed(1)}%`;
  return v.toLocaleString();
}

export function StatsDisplay({
  stats,
  columns = 4,
}: {
  stats: Stat[];
  columns?: 2 | 3 | 4;
}) {
  const grid: Record<2 | 3 | 4, string> = {
    2: 'md:grid-cols-2',
    3: 'md:grid-cols-3',
    4: 'md:grid-cols-4',
  };
  return (
    <div className={`grid grid-cols-1 ${grid[columns]} gap-4`}>
      {stats.map((s, i) => {
        const body = (
          <>
            <p className="text-[10px] uppercase tracking-widest text-[var(--kbgen-text-muted)] font-semibold">
              {s.label}
            </p>
            <p className="text-2xl font-bold tabular-nums text-[var(--kbgen-text)] mt-1">
              {fmt(s.value, s.format)}
            </p>
            {s.delta && (
              <p className="text-xs text-[var(--kbgen-text-secondary)] mt-1">
                <span
                  className={
                    s.delta.value >= 0
                      ? 'text-[var(--kbgen-success)]'
                      : 'text-[var(--kbgen-danger)]'
                  }
                >
                  {s.delta.value >= 0 ? '↑' : '↓'} {Math.abs(s.delta.value)}%
                </span>{' '}
                {s.delta.label ?? ''}
              </p>
            )}
          </>
        );
        return s.onClick ? (
          <button
            key={i}
            onClick={s.onClick}
            className="text-left rounded-lg bg-[var(--kbgen-surface)] border border-[var(--kbgen-border)] p-4 hover:border-[var(--kbgen-brand)] transition-colors"
          >
            {body}
          </button>
        ) : (
          <div
            key={i}
            className="rounded-lg bg-[var(--kbgen-surface)] border border-[var(--kbgen-border)] p-4"
          >
            {body}
          </div>
        );
      })}
    </div>
  );
}
