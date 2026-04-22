import React, { useEffect, useMemo, useState } from 'react';
import { Badge } from '../components/Badge';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { DataTable, type Column } from '../components/DataTable';
import { DetailPanel } from '../components/DetailPanel';
import { DraftReviewPanel } from '../components/DraftReviewPanel';
import { FilterBar } from '../components/FilterBar';
import { StatsDisplay } from '../components/StatsDisplay';
import { StatusBadge } from '../components/StatusBadge';
import { useKbDraft, useKbDrafts, useKbTickets, useKbTopics } from '../hooks/useKb';
import type { KbArticle, KbProcessedTicket } from '../types/kb';

type EnrichedTicket = KbProcessedTicket & {
  confidence?: number | null;
  overall?: number | null;
  draft_status?: string | null;
};

const DECISION_FILTERS = [
  { key: 'DRAFTED', label: 'Drafted', value: 'DRAFTED' },
  { key: 'COVERED', label: 'Covered', value: 'COVERED' },
  { key: 'SKIPPED', label: 'Gap (skipped)', value: 'SKIPPED' },
];

export function Workspace() {
  const urlTopic =
    typeof window !== 'undefined'
      ? new URLSearchParams(window.location.search).get('topic') ?? undefined
      : undefined;

  const [topic, setTopic] = useState<string | undefined>(urlTopic);
  const [decisions, setDecisions] = useState<string[]>(['DRAFTED', 'COVERED', 'SKIPPED']);
  const [selected, setSelected] = useState<EnrichedTicket | null>(null);

  const { data: topics } = useKbTopics('30d');
  const { data: tickets, isLoading: loadingTickets, refetch: refetchTickets } = useKbTickets(
    topic,
    500,
  );
  const { data: draftsPage, refetch: refetchDrafts } = useKbDrafts({ limit: 500 });

  const draftById = useMemo(() => {
    const m = new Map<string, KbArticle>();
    (draftsPage?.items ?? []).forEach((a) => m.set(a.id, a));
    return m;
  }, [draftsPage?.items]);

  const enriched: EnrichedTicket[] = useMemo(
    () =>
      (tickets ?? []).map((t) => {
        const art = t.draft_article_id ? draftById.get(t.draft_article_id) : undefined;
        return {
          ...t,
          confidence: art?.confidence ?? null,
          overall: art?.score?.overall ?? null,
          draft_status: art?.status ?? null,
        };
      }),
    [tickets, draftById],
  );

  const visible = enriched.filter(
    (t) => decisions.length === 0 || decisions.includes(t.decision),
  );

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const url = new URL(window.location.href);
    if (topic) url.searchParams.set('topic', topic);
    else url.searchParams.delete('topic');
    window.history.replaceState({}, '', url.toString());
  }, [topic]);

  const counters = useMemo(() => {
    return {
      total: enriched.length,
      drafted: enriched.filter((t) => t.decision === 'DRAFTED').length,
      covered: enriched.filter((t) => t.decision === 'COVERED').length,
      skipped: enriched.filter((t) => t.decision === 'SKIPPED').length,
    };
  }, [enriched]);

  const columns: Column<EnrichedTicket>[] = [
    {
      key: 'itsm_ticket_id',
      header: 'Ticket',
      width: '120px',
      sortable: true,
      render: (_v, row) => (
        <span className="tabular-nums text-[var(--kbgen-text-secondary)]">
          {row.itsm_provider}:{row.itsm_ticket_id}
        </span>
      ),
    },
    { key: 'title', header: 'Title' },
    {
      key: 'topic',
      header: 'Topic',
      width: '160px',
      sortable: true,
      render: (v) => (v ? <Badge tone="brand">{v as string}</Badge> : '—'),
    },
    {
      key: 'decision',
      header: 'Decision',
      width: '120px',
      render: (v) => <StatusBadge status={v as string} />,
    },
    {
      key: 'confidence',
      header: 'Conf',
      width: '70px',
      render: (v) => (v != null ? `${Math.round((v as number) * 100)}%` : '—'),
    },
    {
      key: 'overall',
      header: 'Health',
      width: '70px',
      render: (v) => (v != null ? `${Math.round((v as number) * 100)}%` : '—'),
    },
    {
      key: 'resolved_at',
      header: 'Resolved',
      width: '110px',
      render: (v) => (v ? new Date(v as string).toLocaleDateString() : '—'),
    },
  ];

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-[var(--kbgen-text)]">Workspace</h1>
        <p className="text-sm text-[var(--kbgen-text-muted)]">
          Every resolved ticket kbgen has seen, with the decision it made. Click any row to
          review or act on it.
        </p>
      </div>

      <StatsDisplay
        stats={[
          { label: 'Tickets', value: counters.total },
          { label: 'Drafted', value: counters.drafted },
          { label: 'Covered', value: counters.covered },
          { label: 'Gap (skipped)', value: counters.skipped },
        ]}
        columns={4}
      />

      {/* Topic chips */}
      <Card>
        <div className="p-3 space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase tracking-widest text-[var(--kbgen-text-muted)]">
              Filter by topic
            </p>
            {topic && (
              <button
                className="text-xs text-[var(--kbgen-brand)] hover:underline"
                onClick={() => setTopic(undefined)}
              >
                Clear
              </button>
            )}
          </div>
          <div className="flex flex-wrap gap-1.5">
            <TopicChip
              label={`All (${(topics ?? []).reduce((s, t) => s + t.ticket_count, 0)})`}
              active={!topic}
              onClick={() => setTopic(undefined)}
              tone="neutral"
            />
            {(topics ?? []).map((t) => (
              <TopicChip
                key={t.topic}
                label={`${t.topic} · ${t.ticket_count}`}
                active={topic === t.topic}
                onClick={() => setTopic(t.topic)}
                tone={
                  t.kb_status === 'covered'
                    ? 'success'
                    : t.kb_status === 'gap'
                      ? 'danger'
                      : 'brand'
                }
              />
            ))}
          </div>
        </div>
      </Card>

      {/* Decision filter */}
      <FilterBar
        filters={DECISION_FILTERS}
        activeFilters={decisions}
        onToggle={(key) =>
          setDecisions((prev) =>
            prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key],
          )
        }
        onClear={() => setDecisions([])}
      />

      {loadingTickets ? (
        <p className="text-sm text-[var(--kbgen-text-muted)]">Loading…</p>
      ) : (
        <DataTable<EnrichedTicket>
          columns={columns}
          data={visible}
          onRowClick={setSelected}
          emptyMessage="No tickets match the current filters."
        />
      )}

      <DetailPanel
        open={!!selected}
        onClose={() => setSelected(null)}
        title={selected?.title ?? ''}
      >
        {selected && (
          <TicketDetail
            ticket={selected}
            onAction={() => {
              refetchTickets();
              refetchDrafts();
            }}
            onClose={() => setSelected(null)}
          />
        )}
      </DetailPanel>
    </div>
  );
}

function TicketDetail({
  ticket,
  onAction,
  onClose,
}: {
  ticket: EnrichedTicket;
  onAction: () => void;
  onClose: () => void;
}) {
  if (ticket.decision === 'DRAFTED' && ticket.draft_article_id) {
    return (
      <DraftReviewPanel
        draftId={ticket.draft_article_id}
        onAction={(a) => {
          onAction();
          if (a === 'pushed' || a === 'rejected') onClose();
        }}
      />
    );
  }
  if (ticket.decision === 'COVERED' && ticket.matched_article_id) {
    return <CoveredView ticket={ticket} articleId={ticket.matched_article_id} />;
  }
  return <SkippedView ticket={ticket} />;
}

function CoveredView({
  ticket,
  articleId,
}: {
  ticket: EnrichedTicket;
  articleId: string;
}) {
  const { data: article, isLoading } = useKbDraft(articleId);
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Badge tone="success">COVERED</Badge>
        <span className="text-xs text-[var(--kbgen-text-muted)]">
          matched at {Math.round((ticket.matched_score ?? 0) * 100)}% similarity
        </span>
      </div>
      <div className="text-sm text-[var(--kbgen-text-secondary)]">
        <p className="font-semibold text-[var(--kbgen-text)]">Source ticket</p>
        <p>{ticket.title}</p>
      </div>
      <div className="border-t border-[var(--kbgen-border)] pt-4">
        <p className="text-xs uppercase tracking-widest text-[var(--kbgen-text-muted)] mb-2">
          Matched KB article
        </p>
        {isLoading || !article ? (
          <p className="text-sm text-[var(--kbgen-text-muted)]">Loading…</p>
        ) : (
          <Card>
            <div className="p-4 space-y-2">
              <div className="flex items-center gap-2">
                <p className="font-semibold text-[var(--kbgen-text)]">{article.title}</p>
                {article.category && <Badge tone="brand">{article.category}</Badge>}
                {article.itsm_kb_id && (
                  <span className="text-xs text-[var(--kbgen-text-muted)]">
                    KB {article.itsm_kb_id}
                  </span>
                )}
              </div>
              {article.summary && (
                <p className="text-sm text-[var(--kbgen-text-secondary)]">{article.summary}</p>
              )}
              {article.steps_md && (
                <pre className="mt-2 whitespace-pre-wrap text-xs font-mono text-[var(--kbgen-text)] bg-[var(--kbgen-border-light)] rounded p-3 max-h-96 overflow-y-auto">
                  {article.steps_md}
                </pre>
              )}
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}

function SkippedView({ ticket }: { ticket: EnrichedTicket }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Badge tone="warning">GAP</Badge>
        <span className="text-xs text-[var(--kbgen-text-muted)]">{ticket.decision_reason}</span>
      </div>
      <Card>
        <div className="p-4 space-y-2 text-sm">
          <p className="font-semibold text-[var(--kbgen-text)]">{ticket.title}</p>
          {ticket.topic && (
            <p className="text-[var(--kbgen-text-secondary)]">
              Topic: <Badge tone="brand">{ticket.topic}</Badge>
            </p>
          )}
          <p className="text-[var(--kbgen-text-muted)]">
            No article was drafted — the ticket didn't carry enough resolution signal.
          </p>
        </div>
      </Card>
      <Card>
        <div className="p-4 space-y-2 opacity-60">
          <div className="flex items-center gap-2">
            <p className="text-sm font-semibold">Generate for this gap</p>
            <Badge tone="warning">Coming in MVP2</Badge>
          </div>
          <p className="text-xs text-[var(--kbgen-text-secondary)]">
            MVP2 will let you proactively draft an article for this gap using clustered
            context from related tickets.
          </p>
          <Button variant="secondary" disabled>
            Flag as gap (MVP2)
          </Button>
        </div>
      </Card>
    </div>
  );
}

function TopicChip({
  label,
  active,
  onClick,
  tone,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
  tone: 'neutral' | 'brand' | 'success' | 'danger';
}) {
  const toneClasses: Record<typeof tone, string> = {
    neutral: active
      ? 'bg-[var(--kbgen-text)] text-white border-transparent'
      : 'bg-[var(--kbgen-surface)] text-[var(--kbgen-text-secondary)] border-[var(--kbgen-border)] hover:border-[var(--kbgen-text-muted)]',
    brand: active
      ? 'bg-[var(--kbgen-brand)] text-white border-transparent'
      : 'bg-[var(--kbgen-brand-light)] text-[var(--kbgen-brand)] border-[var(--kbgen-brand-light)] hover:border-[var(--kbgen-brand)]',
    success: active
      ? 'bg-[var(--kbgen-success)] text-white border-transparent'
      : 'bg-emerald-50 text-emerald-700 border-emerald-100 hover:border-emerald-400',
    danger: active
      ? 'bg-[var(--kbgen-danger)] text-white border-transparent'
      : 'bg-rose-50 text-rose-700 border-rose-100 hover:border-rose-400',
  };
  return (
    <button
      type="button"
      onClick={onClick}
      className={`text-xs font-medium px-2.5 py-1 rounded-full border transition-colors ${toneClasses[tone]}`}
    >
      {label}
    </button>
  );
}
