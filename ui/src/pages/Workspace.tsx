import React, { useEffect, useMemo, useState } from 'react';
import { Badge } from '../components/Badge';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { DataTable, type Column } from '../components/DataTable';
import { DetailPanel } from '../components/DetailPanel';
import { DraftReviewPanel } from '../components/DraftReviewPanel';
import { FilterBar } from '../components/FilterBar';
import { KbLink } from '../components/KbLink';
import { LegendCard } from '../components/LegendCard';
import { StatsDisplay } from '../components/StatsDisplay';
import { useKbDraft, useKbDrafts, useKbTickets, useKbTopics } from '../hooks/useKb';
import { itsmKbListUrl } from '../lib/itsm';
import type { KbArticle, KbProcessedTicket } from '../types/kb';

type EnrichedTicket = KbProcessedTicket & {
  confidence?: number | null;
  overall?: number | null;
  draft_status?: string | null;
  served_count?: number;
  master_ticket?: {
    id: string;
    provider: string;
    status: string;
    itsm_kb_id: string | null;
  } | null;
  // Unified lifecycle status — a single label collapsing the ticket's
  // pipeline decision (DRAFTED/COVERED/SKIPPED) and the linked article's
  // review state (DRAFT/EDITED/APPROVED/PUSHED/REJECTED/IMPORTED) into
  // one value that reviewers actually act on.
  ui_status?: UiStatus;
  ui_status_label?: string;
  ui_status_tone?: 'brand' | 'success' | 'warning' | 'danger' | 'neutral';
};

type UiStatus =
  | 'PENDING'          // DRAFTED, article DRAFT — needs reviewer
  | 'EDITED'           // DRAFTED, article EDITED — needs approval
  | 'APPROVED'         // DRAFTED, article APPROVED — ready to push (rare; we auto-push)
  | 'LIVE'             // DRAFTED, article PUSHED — live in ITSM
  | 'REJECTED'         // article REJECTED
  | 'COVERED_LIVE'     // COVERED, matched article already PUSHED/IMPORTED
  | 'COVERED_PENDING'  // COVERED, matched article still in kbgen (draft)
  | 'GAP';             // SKIPPED — thin resolution, no article

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
  const [mastersOnly, setMastersOnly] = useState(false);
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

  // How many OTHER tickets are COVERED by each article? Keyed by article id.
  // A DRAFTED ticket whose draft_article_id has entries here is a "master"
  // serving that many covered tickets.
  const coveragePerArticle = useMemo(() => {
    const m = new Map<string, number>();
    (tickets ?? []).forEach((t) => {
      if (t.decision === 'COVERED' && t.matched_article_id) {
        m.set(t.matched_article_id, (m.get(t.matched_article_id) ?? 0) + 1);
      }
    });
    return m;
  }, [tickets]);

  // For COVERED rows, the master ticket is whichever ticket authored the
  // article (article.source_ticket_id). We also carry the article's status
  // + itsm_kb_id so the row can show whether the referenced KB is LIVE in
  // the ITSM or still PENDING review in kbgen.
  const masterByArticle = useMemo(() => {
    const m = new Map<
      string,
      { id: string; provider: string; status: string; itsm_kb_id: string | null }
    >();
    (draftsPage?.items ?? []).forEach((a) => {
      if (a.source_ticket_id) {
        m.set(a.id, {
          id: a.source_ticket_id,
          provider: a.itsm_provider ?? 'itsm',
          status: a.status,
          itsm_kb_id: a.itsm_kb_id,
        });
      }
    });
    return m;
  }, [draftsPage?.items]);

  const enriched: EnrichedTicket[] = useMemo(
    () =>
      (tickets ?? []).map((t) => {
        const art = t.draft_article_id ? draftById.get(t.draft_article_id) : undefined;
        const matchedArt = t.matched_article_id ? draftById.get(t.matched_article_id) : undefined;
        const servedCount = t.draft_article_id
          ? 1 + (coveragePerArticle.get(t.draft_article_id) ?? 0)
          : 0;
        const master = t.matched_article_id ? masterByArticle.get(t.matched_article_id) : null;

        // ── Unified UI status ───────────────────────────────────────────
        let uiStatus: UiStatus;
        let label: string;
        let tone: EnrichedTicket['ui_status_tone'];
        if (t.decision === 'SKIPPED') {
          uiStatus = 'GAP';
          label = 'GAP';
          tone = 'warning';
        } else if (t.decision === 'COVERED') {
          const live =
            matchedArt?.status === 'PUSHED' || matchedArt?.status === 'IMPORTED';
          if (live) {
            uiStatus = 'COVERED_LIVE';
            label = `COVERED → KB ${matchedArt?.itsm_kb_id ?? '?'}`;
            tone = 'success';
          } else {
            uiStatus = 'COVERED_PENDING';
            // "Master needs review" is clearer than the previous "pending KB"
            // which collided with PENDING REVIEW below.
            label = 'COVERED · master needs review';
            tone = 'warning';
          }
        } else {
          // decision === 'DRAFTED' — the article's review lifecycle wins.
          switch (art?.status) {
            case 'PUSHED':
              uiStatus = 'LIVE';
              label = `LIVE · KB ${art.itsm_kb_id ?? '?'}`;
              tone = 'success';
              break;
            case 'APPROVED':
              uiStatus = 'APPROVED';
              label = 'APPROVED';
              tone = 'success';
              break;
            case 'REJECTED':
              uiStatus = 'REJECTED';
              label = 'REJECTED';
              tone = 'danger';
              break;
            case 'EDITED':
              uiStatus = 'EDITED';
              label = 'EDITED · awaiting approval';
              tone = 'brand';
              break;
            case 'DRAFT':
            default:
              uiStatus = 'PENDING';
              label = 'NEW · needs review';
              tone = 'brand';
              break;
          }
        }

        return {
          ...t,
          confidence: art?.confidence ?? null,
          overall: art?.score?.overall ?? null,
          draft_status: art?.status ?? null,
          served_count: servedCount,
          master_ticket: master ?? null,
          ui_status: uiStatus,
          ui_status_label: label,
          ui_status_tone: tone,
        };
      }),
    [tickets, draftById, coveragePerArticle, masterByArticle],
  );

  const visible = enriched.filter((t) => {
    if (decisions.length > 0 && !decisions.includes(t.decision)) return false;
    if (mastersOnly && !(t.decision === 'DRAFTED' && (t.served_count ?? 0) >= 2)) return false;
    return true;
  });

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
      masters: enriched.filter(
        (t) => t.decision === 'DRAFTED' && (t.served_count ?? 0) >= 2,
      ).length,
    };
  }, [enriched]);

  const columns: Column<EnrichedTicket>[] = [
    {
      key: 'itsm_ticket_id',
      header: 'Ticket',
      width: '150px',
      sortable: true,
      render: (_v, row) => {
        const isMaster = row.decision === 'DRAFTED' && (row.served_count ?? 0) >= 2;
        return (
          <div className="flex items-center gap-1.5">
            {isMaster ? (
              <span
                className="text-[var(--kbgen-warning)]"
                title={`Master ticket — this KB serves ${row.served_count} tickets in total`}
              >
                ★
              </span>
            ) : (
              <span className="w-[12px] inline-block" />
            )}
            <span className="tabular-nums text-[var(--kbgen-text-secondary)]">
              {row.itsm_provider}:{row.itsm_ticket_id}
            </span>
          </div>
        );
      },
    },
    {
      key: 'role',
      header: 'Role',
      width: '150px',
      render: (_v, row) => {
        if (row.decision === 'DRAFTED' && (row.served_count ?? 0) >= 2) {
          // served_count already counts the master itself; display total.
          return (
            <Badge tone="success">Master · serves {row.served_count} tickets</Badge>
          );
        }
        if (row.decision === 'COVERED' && row.master_ticket) {
          const m = row.master_ticket;
          return (
            <span
              className="text-xs tabular-nums text-[var(--kbgen-text-muted)]"
              title="This ticket was matched to the master article below. Live/pending state is in the Status column."
            >
              → {m.provider}:{m.id}
            </span>
          );
        }
        if (row.decision === 'DRAFTED') {
          return (
            <span className="text-xs text-[var(--kbgen-text-muted)]">Solo draft</span>
          );
        }
        return null;
      },
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
      key: 'ui_status',
      header: 'Status',
      width: '220px',
      sortable: true,
      render: (_v, row) => {
        // LIVE and COVERED_LIVE rows carry a concrete ITSM KB id that we
        // surface as a clickable link into GLPI.
        const matchedKbId =
          row.ui_status === 'LIVE'
            ? row.draft_article_id &&
              (row as { itsm_kb_id?: string | null }).itsm_kb_id // fallthrough
            : null;
        // For LIVE rows we need the kb_id from the draft map; for
        // COVERED_LIVE we need it from the matched article. Simpler: dig
        // them out of the raw label which was built with the id already.
        const kbMatch = row.ui_status_label?.match(/KB (\S+)/);
        const kbId = kbMatch ? kbMatch[1] : null;

        return (
          <Badge tone={row.ui_status_tone ?? 'neutral'} className="whitespace-normal">
            {kbId && (row.ui_status === 'LIVE' || row.ui_status === 'COVERED_LIVE') ? (
              <>
                {row.ui_status === 'LIVE' ? 'LIVE · ' : 'COVERED → '}
                <KbLink kbId={kbId} className="text-inherit" />
              </>
            ) : (
              row.ui_status_label ?? row.decision
            )}
          </Badge>
        );
        void matchedKbId;
      },
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
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-[var(--kbgen-text)]">Workspace</h1>
          <p className="text-sm text-[var(--kbgen-text-muted)]">
            Every resolved ticket kbgen has seen, with the decision it made. Click any row to
            review or act on it.
          </p>
        </div>
        <a
          href={itsmKbListUrl()}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs font-semibold px-3 py-2 rounded-md border border-[var(--kbgen-border)] text-[var(--kbgen-text-secondary)] hover:border-[var(--kbgen-brand)] hover:text-[var(--kbgen-brand)]"
          title="Open the ITSM's full knowledge-base list in a new tab"
        >
          Browse KB in ITSM ↗
        </a>
      </div>

      <StatsDisplay
        stats={[
          { label: 'Tickets', value: counters.total },
          { label: 'Drafted', value: counters.drafted },
          { label: '★ Masters', value: counters.masters },
          { label: 'Covered', value: counters.covered },
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
      <div className="flex flex-wrap items-center gap-3">
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
        <button
          type="button"
          onClick={() => setMastersOnly((v) => !v)}
          disabled={counters.masters === 0}
          className={`px-2.5 py-1 rounded-full text-xs font-medium border transition-colors ${
            mastersOnly
              ? 'bg-[var(--kbgen-warning)] text-white border-transparent'
              : counters.masters === 0
                ? 'bg-[var(--kbgen-surface)] text-[var(--kbgen-text-muted)] border-[var(--kbgen-border)] opacity-60 cursor-not-allowed'
                : 'bg-[var(--kbgen-surface)] text-[var(--kbgen-text-secondary)] border-[var(--kbgen-border)] hover:border-[var(--kbgen-warning)]'
          }`}
          title={
            counters.masters === 0
              ? 'No master tickets yet — dedup fires only with semantic similarity. Set OPENAI_API_KEY and re-poll to see master/covered rollups.'
              : 'Show only DRAFTED tickets whose article covers 1+ other tickets'
          }
        >
          ★ Masters only
        </button>
      </div>

      {loadingTickets ? (
        <p className="text-sm text-[var(--kbgen-text-muted)]">Loading…</p>
      ) : visible.length === 0 && mastersOnly && counters.masters === 0 ? (
        <Card>
          <div className="p-6 space-y-2 text-sm">
            <p className="text-[var(--kbgen-text)] font-semibold">
              No master tickets yet.
            </p>
            <p className="text-[var(--kbgen-text-secondary)]">
              A master ticket is a <strong>DRAFTED</strong> ticket whose article has
              matched 1+ subsequent tickets via semantic dedup. Rollup only happens when
              kbgen can actually measure similarity — which requires real OpenAI embeddings.
            </p>
            <p className="text-[var(--kbgen-text-muted)] text-xs pt-2">
              Set <code>OPENAI_API_KEY</code> in <code>.env</code>, reset the pipeline
              (<code>POST /api/kb/admin/reset?confirm=yes</code>), and re-run a poll cycle.
              Similar tickets within the same topic will collapse into a master + N covered.
            </p>
            <Button variant="secondary" onClick={() => setMastersOnly(false)}>
              Turn off filter
            </Button>
          </div>
        </Card>
      ) : (
        <DataTable<EnrichedTicket>
          columns={columns}
          data={visible}
          onRowClick={setSelected}
          emptyMessage="No tickets match the current filters."
        />
      )}

      <LegendCard />

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
    return (
      <CoveredView
        ticket={ticket}
        articleId={ticket.matched_article_id}
        onAction={onAction}
        onClose={onClose}
      />
    );
  }
  return <SkippedView ticket={ticket} />;
}

function CoveredView({
  ticket,
  articleId,
  onAction,
  onClose,
}: {
  ticket: EnrichedTicket;
  articleId: string;
  onAction?: () => void;
  onClose?: () => void;
}) {
  const { data: article, isLoading } = useKbDraft(articleId);
  const live = article && (article.status === 'PUSHED' || article.status === 'IMPORTED');

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="success">COVERED</Badge>
        <span className="text-xs text-[var(--kbgen-text-muted)]">
          matched at {Math.round((ticket.matched_score ?? 0) * 100)}% similarity
        </span>
        {live ? (
          <Badge tone="success">
            <KbLink kbId={article.itsm_kb_id} className="text-inherit" /> · live in ITSM
          </Badge>
        ) : article ? (
          <Badge tone="warning">matched article pending · push to publish</Badge>
        ) : null}
      </div>

      <Card>
        <div className="p-4 space-y-1 text-sm">
          <p className="text-xs uppercase tracking-widest text-[var(--kbgen-text-muted)]">
            This ticket
          </p>
          <p className="font-semibold text-[var(--kbgen-text)]">{ticket.title}</p>
          {ticket.master_ticket && (
            <p className="text-xs text-[var(--kbgen-text-muted)] pt-1">
              kbgen matched this to the KB article drafted from the master ticket{' '}
              <code>
                {ticket.master_ticket.provider}:{ticket.master_ticket.id}
              </code>
              . Any push action lives on the master draft below.
            </p>
          )}
        </div>
      </Card>

      {isLoading || !article ? (
        <p className="text-sm text-[var(--kbgen-text-muted)]">Loading master article…</p>
      ) : live ? (
        // Already live — show read-only article content.
        <Card>
          <div className="p-4 space-y-2">
            <div className="flex items-center gap-2">
              <p className="font-semibold text-[var(--kbgen-text)]">{article.title}</p>
              {article.category && <Badge tone="brand">{article.category}</Badge>}
              {article.itsm_kb_id && (
                <span className="text-xs text-[var(--kbgen-text-muted)]">
                  <KbLink kbId={article.itsm_kb_id} />
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
      ) : (
        // Not live yet — mount the full review panel for the master article so
        // the reviewer can approve + push without navigating away. Approving
        // here publishes the KB for this covered ticket AND every other
        // ticket the article matched against.
        <div>
          <div className="pb-2 flex items-center gap-2 text-xs text-[var(--kbgen-text-muted)]">
            <span className="uppercase tracking-widest font-bold text-[var(--kbgen-warning)]">
              Master draft
            </span>
            <span>review + push here to publish the KB for this topic</span>
          </div>
          <DraftReviewPanel
            draftId={articleId}
            onAction={(a) => {
              onAction?.();
              if (a === 'pushed' || a === 'rejected') onClose?.();
            }}
          />
        </div>
      )}
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
