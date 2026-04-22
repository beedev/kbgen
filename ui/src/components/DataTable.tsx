import React, { useMemo, useState } from 'react';

export interface Column<T> {
  key: keyof T | string;
  header: string;
  width?: string;
  sortable?: boolean;
  render?: (value: unknown, row: T) => React.ReactNode;
}

export function DataTable<T extends Record<string, any>>({
  columns,
  data,
  onRowClick,
  emptyMessage = 'No rows.',
}: {
  columns: Column<T>[];
  data: T[];
  onRowClick?: (row: T) => void;
  emptyMessage?: string;
}) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');

  const sorted = useMemo(() => {
    if (!sortKey) return data;
    const arr = [...data].sort((a, b) => {
      const av = (a as any)[sortKey];
      const bv = (b as any)[sortKey];
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      if (av < bv) return sortDir === 'asc' ? -1 : 1;
      if (av > bv) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
    return arr;
  }, [data, sortKey, sortDir]);

  const toggleSort = (key: string) => {
    if (sortKey === key) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  return (
    <div className="rounded-lg border border-[var(--kbgen-border)] bg-[var(--kbgen-surface)] overflow-hidden">
      <table className="min-w-full text-sm">
        <thead className="bg-[var(--kbgen-border-light)] text-[var(--kbgen-text-secondary)]">
          <tr>
            {columns.map((c) => (
              <th
                key={String(c.key) + c.header}
                style={{ width: c.width }}
                className="text-left font-semibold px-3 py-2 whitespace-nowrap"
              >
                {c.sortable ? (
                  <button
                    onClick={() => toggleSort(String(c.key))}
                    className="inline-flex items-center gap-1 hover:text-[var(--kbgen-text)]"
                  >
                    {c.header}
                    <span className="text-[10px] opacity-60">
                      {sortKey === c.key ? (sortDir === 'asc' ? '▲' : '▼') : '↕'}
                    </span>
                  </button>
                ) : (
                  c.header
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.length === 0 && (
            <tr>
              <td
                colSpan={columns.length}
                className="px-3 py-8 text-center text-[var(--kbgen-text-muted)]"
              >
                {emptyMessage}
              </td>
            </tr>
          )}
          {sorted.map((row, idx) => (
            <tr
              key={idx}
              onClick={() => onRowClick?.(row)}
              className={`border-t border-[var(--kbgen-border-light)] ${
                onRowClick ? 'cursor-pointer hover:bg-[var(--kbgen-border-light)]' : ''
              }`}
            >
              {columns.map((c) => {
                const raw = (row as any)[c.key];
                return (
                  <td
                    key={String(c.key) + c.header}
                    className="px-3 py-2 align-top text-[var(--kbgen-text)]"
                  >
                    {c.render ? c.render(raw, row) : raw != null ? String(raw) : '—'}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
