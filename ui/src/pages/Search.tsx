import React, { useState } from 'react';
import { Badge } from '../components/Badge';
import { Card } from '../components/Card';
import { useKbSearch } from '../hooks/useKb';

export function SearchPage() {
  const [draft, setDraft] = useState('');
  const [query, setQuery] = useState('');
  const { data, isFetching } = useKbSearch(query, undefined, 10);

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setQuery(draft.trim());
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-[var(--kbgen-text)]">Smart Search</h1>
        <p className="text-sm text-[var(--kbgen-text-muted)]">
          Semantic search over the indexed knowledge base — finds answers by intent, not just
          keywords.
        </p>
      </div>

      <form onSubmit={onSubmit} className="flex gap-2">
        <input
          className="flex-1 rounded-md border border-[var(--kbgen-border)] p-3 text-sm bg-[var(--kbgen-surface)] focus:outline-none focus:ring-2 focus:ring-[var(--kbgen-brand)]/40"
          placeholder="e.g. how do I reset my VPN after password change?"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
        />
        <button
          type="submit"
          className="rounded-md bg-[var(--kbgen-brand)] text-white px-4 py-2 text-sm font-semibold hover:bg-[var(--kbgen-brand-dark)]"
        >
          Search
        </button>
      </form>

      {query && isFetching && (
        <p className="text-sm text-[var(--kbgen-text-muted)]">Searching…</p>
      )}

      {query && !isFetching && (data?.hits?.length ?? 0) === 0 && (
        <Card>
          <div className="p-6 text-sm">
            <p className="text-[var(--kbgen-text)]">No KB articles cover this question.</p>
            <p className="text-[var(--kbgen-text-muted)] mt-1">
              <Badge tone="warning">Coming in MVP2</Badge> — flag as a gap so the system can
              draft an article proactively.
            </p>
          </div>
        </Card>
      )}

      <div className="space-y-3">
        {(data?.hits ?? []).map((h) => (
          <Card key={h.chunk_id}>
            <div className="p-4 space-y-1">
              <div className="flex items-center justify-between gap-3">
                <p className="font-semibold text-[var(--kbgen-text)]">{h.title}</p>
                <div className="flex items-center gap-2 text-xs shrink-0">
                  {h.category && <Badge tone="brand">{h.category}</Badge>}
                  {h.itsm_kb_id && (
                    <span className="text-[var(--kbgen-text-muted)]">KB {h.itsm_kb_id}</span>
                  )}
                  <span className="tabular-nums text-[var(--kbgen-text-secondary)]">
                    {Math.round(h.relevance * 100)}%
                  </span>
                </div>
              </div>
              <p className="text-sm text-[var(--kbgen-text-secondary)]">{h.preview}</p>
              {h.source_ticket_id && (
                <p className="text-xs text-[var(--kbgen-text-muted)]">
                  derived from ticket {h.source_ticket_id}
                </p>
              )}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
