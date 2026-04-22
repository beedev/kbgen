import React from 'react';

/**
 * Minimal markdown editor — a `<textarea>` for edit + an optional preview
 * placeholder. Deliberately zero-dependency; upgrade to @uiw/react-md-editor
 * later if preview fidelity becomes important.
 */
export function MarkdownEditor({
  value,
  onChange,
  rows = 16,
  readOnly = false,
  placeholder,
}: {
  value: string;
  onChange?: (v: string) => void;
  rows?: number;
  readOnly?: boolean;
  placeholder?: string;
}) {
  return (
    <textarea
      className="w-full rounded-md border border-[var(--kbgen-border)] bg-[var(--kbgen-surface)] p-3 text-sm font-mono leading-relaxed focus:outline-none focus:ring-2 focus:ring-[var(--kbgen-brand)]/40 disabled:opacity-60"
      rows={rows}
      readOnly={readOnly}
      placeholder={placeholder}
      value={value}
      onChange={(e) => onChange?.(e.target.value)}
    />
  );
}
