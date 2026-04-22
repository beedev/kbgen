import React, { useEffect, useMemo, useState } from 'react';

export interface Column<T> {
  key: keyof T | string;
  header: string;
  width?: string;
  sortable?: boolean;
  render?: (value: unknown, row: T) => React.ReactNode;
}

const PAGE_SIZE_OPTIONS: (number | 'all')[] = [10, 25, 50, 100, 'all'];
const DEFAULT_PAGE_SIZE = 25;

function smartCompare(av: unknown, bv: unknown): number {
  if (av == null && bv == null) return 0;
  if (av == null) return 1;
  if (bv == null) return -1;
  // Strings with numeric content ("541" vs "740", "case #04" vs "case #10")
  // should compare numerically — browser's localeCompare with numeric:true
  // handles both pure and mixed cases.
  if (typeof av === 'string' && typeof bv === 'string') {
    return av.localeCompare(bv, undefined, { numeric: true, sensitivity: 'base' });
  }
  if (av < bv) return -1;
  if (av > bv) return 1;
  return 0;
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
  const [pageSize, setPageSize] = useState<number | 'all'>(DEFAULT_PAGE_SIZE);
  const [page, setPage] = useState(0);

  const sorted = useMemo(() => {
    if (!sortKey) return data;
    const arr = [...data].sort((a, b) => {
      const c = smartCompare((a as any)[sortKey], (b as any)[sortKey]);
      return sortDir === 'asc' ? c : -c;
    });
    return arr;
  }, [data, sortKey, sortDir]);

  const total = sorted.length;
  const effectivePageSize = pageSize === 'all' ? Math.max(total, 1) : pageSize;
  const pageCount = Math.max(1, Math.ceil(total / effectivePageSize));

  // Reset to page 0 when the underlying data shrinks or page-size changes
  // would leave us past the last page.
  useEffect(() => {
    if (page >= pageCount) setPage(0);
  }, [page, pageCount]);

  const pageRows = useMemo(() => {
    if (pageSize === 'all') return sorted;
    const start = page * effectivePageSize;
    return sorted.slice(start, start + effectivePageSize);
  }, [sorted, page, effectivePageSize, pageSize]);

  const toggleSort = (key: string) => {
    if (sortKey === key) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    else {
      setSortKey(key);
      setSortDir('asc');
    }
    setPage(0);
  };

  const firstRow = total === 0 ? 0 : page * effectivePageSize + 1;
  const lastRow = pageSize === 'all' ? total : Math.min(total, (page + 1) * effectivePageSize);

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
          {pageRows.length === 0 && (
            <tr>
              <td
                colSpan={columns.length}
                className="px-3 py-8 text-center text-[var(--kbgen-text-muted)]"
              >
                {emptyMessage}
              </td>
            </tr>
          )}
          {pageRows.map((row, idx) => (
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

      {total > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[var(--kbgen-border-light)] bg-[var(--kbgen-border-light)]/40 px-3 py-2 text-xs text-[var(--kbgen-text-secondary)]">
          <div className="flex items-center gap-2">
            <label htmlFor="kbgen-page-size">Rows per page</label>
            <select
              id="kbgen-page-size"
              value={String(pageSize)}
              onChange={(e) => {
                const v = e.target.value;
                setPageSize(v === 'all' ? 'all' : Number(v));
                setPage(0);
              }}
              className="rounded border border-[var(--kbgen-border)] bg-[var(--kbgen-surface)] px-2 py-1 text-[var(--kbgen-text)]"
            >
              {PAGE_SIZE_OPTIONS.map((opt) => (
                <option key={String(opt)} value={String(opt)}>
                  {opt === 'all' ? 'All' : opt}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-3">
            <span>
              {firstRow}–{lastRow} of {total}
            </span>
            {pageSize !== 'all' && (
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                  disabled={page === 0}
                  className="rounded border border-[var(--kbgen-border)] px-2 py-0.5 hover:bg-[var(--kbgen-surface)] disabled:cursor-not-allowed disabled:opacity-40"
                  aria-label="Previous page"
                >
                  ‹
                </button>
                <span className="px-1">
                  {page + 1} / {pageCount}
                </span>
                <button
                  type="button"
                  onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))}
                  disabled={page >= pageCount - 1}
                  className="rounded border border-[var(--kbgen-border)] px-2 py-0.5 hover:bg-[var(--kbgen-surface)] disabled:cursor-not-allowed disabled:opacity-40"
                  aria-label="Next page"
                >
                  ›
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
