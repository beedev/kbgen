import React, { useState } from 'react';
import { Badge } from '../components/Badge';
import { Card } from '../components/Card';
import { useKbSearch } from '../hooks/useKb';
import type { KbSearchHit } from '../types/kb';

type KindFilter = 'all' | 'kb' | 'ticket';

const FILTERS: { key: KindFilter; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'kb', label: 'KB articles' },
  { key: 'ticket', label: 'Tickets' },
];

export function SearchPage() {
  const [draft, setDraft] = useState('');
  const [query, setQuery] = useState('');
  const [kindFilter, setKindFilter] = useState<KindFilter>('all');

  const { data, isFetching } = useKbSearch(
    query,
    undefined,
    20,
    kindFilter === 'all' ? undefined : kindFilter,
  );

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setQuery(draft.trim());
  };

  const hits = data?.hits ?? [];
  const kbCount = hits.filter((h) => h.object_kind === 'kb').length;
  const ticketCount = hits.filter((h) => h.object_kind === 'ticket').length;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-[var(--kbgen-text)]">Smart Search</h1>
        <p className="text-sm text-[var(--kbgen-text-muted)]">
          Semantic search across both the knowledge base and the processed ticket log —
          finds answers by intent, not just keywords.
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

      {query && (
        <div className="flex items-center gap-2 flex-wrap">
          {FILTERS.map((f) => {
            const active = kindFilter === f.key;
            return (
              <button
                key={f.key}
                type="button"
                onClick={() => setKindFilter(f.key)}
                className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                  active
                    ? 'bg-[var(--kbgen-brand)] text-white border-transparent'
                    : 'bg-[var(--kbgen-surface)] text-[var(--kbgen-text-secondary)] border-[var(--kbgen-border)] hover:border-[var(--kbgen-brand)]'
                }`}
              >
                {f.label}
              </button>
            );
          })}
          {!isFetching && data && (
            <span className="text-xs text-[var(--kbgen-text-muted)] ml-1">
              {hits.length} result{hits.length === 1 ? '' : 's'}
              {kindFilter === 'all' && hits.length > 0 && (
                <>
                  {' '}· {kbCount} KB · {ticketCount} ticket
                  {ticketCount === 1 ? '' : 's'}
                </>
              )}
            </span>
          )}
        </div>
      )}

      {query && isFetching && (
        <p className="text-sm text-[var(--kbgen-text-muted)]">Searching…</p>
      )}

      {query && !isFetching && hits.length === 0 && (
        <Card>
          <div className="p-6 text-sm">
            <p className="text-[var(--kbgen-text)]">
              Nothing found across KB articles or tickets.
            </p>
            <p className="text-[var(--kbgen-text-muted)] mt-1">
              Try a broader phrasing, or switch the filter above.
            </p>
          </div>
        </Card>
      )}

      <div className="space-y-3">
        {hits.map((h) => (
          <SearchResultCard key={resultKey(h)} hit={h} />
        ))}
      </div>
    </div>
  );
}

function resultKey(h: KbSearchHit): string {
  return h.object_kind === 'kb'
    ? `kb:${h.chunk_id ?? h.article_id}`
    : `ticket:${h.itsm_ticket_id}`;
}

function SearchResultCard({ hit }: { hit: KbSearchHit }) {
  const isTicket = hit.object_kind === 'ticket';
  const openTicket = () => {
    if (isTicket && hit.itsm_ticket_id) {
      // Send the user to Workspace — today it has no deep-link, but the topic
      // query param already narrows the list, and the user can filter further.
      const target = hit.topic
        ? `/workspace?topic=${encodeURIComponent(hit.topic)}`
        : '/workspace';
      window.location.assign(target);
    }
  };

  return (
    <Card>
      <div
        className={`p-4 space-y-1 ${isTicket ? 'cursor-pointer hover:bg-[var(--kbgen-border-light)]/30 transition-colors' : ''}`}
        onClick={isTicket ? openTicket : undefined}
      >
        <div className="flex items-center justify-between gap-3">
          <p className="font-semibold text-[var(--kbgen-text)]">{hit.title}</p>
          <div className="flex items-center gap-2 text-xs shrink-0">
            {isTicket ? (
              <Badge tone="neutral">TICKET</Badge>
            ) : (
              <Badge tone="success">KB</Badge>
            )}
            {hit.category && <Badge tone="brand">{hit.category}</Badge>}
            {hit.object_kind === 'kb' && hit.itsm_kb_id && (
              <span className="text-[var(--kbgen-text-muted)]">KB {hit.itsm_kb_id}</span>
            )}
            {isTicket && hit.decision && (
              <Badge tone={hit.decision === 'SKIPPED' ? 'warning' : 'neutral'}>
                {hit.decision}
              </Badge>
            )}
            <span className="tabular-nums text-[var(--kbgen-text-secondary)]">
              {Math.round(hit.relevance * 100)}%
            </span>
          </div>
        </div>
        <p className="text-sm text-[var(--kbgen-text-secondary)] line-clamp-3">
          {hit.preview}
        </p>
        {isTicket && hit.itsm_ticket_id && (
          <p className="text-xs text-[var(--kbgen-text-muted)]">
            ticket {hit.itsm_ticket_id}
          </p>
        )}
        {!isTicket && hit.source_ticket_id && (
          <p className="text-xs text-[var(--kbgen-text-muted)]">
            derived from ticket {hit.source_ticket_id}
          </p>
        )}
      </div>
    </Card>
  );
}
