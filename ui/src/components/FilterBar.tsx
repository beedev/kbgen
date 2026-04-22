import React from 'react';

export interface Filter {
  key: string;
  label: string;
  value: string;
}

export function FilterBar({
  filters,
  activeFilters,
  onToggle,
  onClear,
}: {
  filters: Filter[];
  activeFilters: string[];
  onToggle: (key: string) => void;
  onClear?: () => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {filters.map((f) => {
        const active = activeFilters.includes(f.key);
        return (
          <button
            key={f.key}
            onClick={() => onToggle(f.key)}
            className={`px-2.5 py-1 rounded-full text-xs font-medium border transition-colors ${
              active
                ? 'bg-[var(--kbgen-brand)] text-white border-transparent'
                : 'bg-[var(--kbgen-surface)] text-[var(--kbgen-text-secondary)] border-[var(--kbgen-border)] hover:border-[var(--kbgen-text-muted)]'
            }`}
          >
            {f.label}
          </button>
        );
      })}
      {onClear && activeFilters.length > 0 && (
        <button
          onClick={onClear}
          className="text-xs text-[var(--kbgen-text-muted)] hover:text-[var(--kbgen-text)] underline underline-offset-2"
        >
          Clear
        </button>
      )}
    </div>
  );
}
