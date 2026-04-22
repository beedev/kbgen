import React from 'react';
import { Badge } from '../components/Badge';
import { BarChart } from '../components/BarChart';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { StatsDisplay, type Stat } from '../components/StatsDisplay';
import { useKbDrafts, useKbSettings, useKbStats, useKbTopics } from '../hooks/useKb';

export function Dashboard({ onNavigate }: { onNavigate: (p: string) => void }) {
  const { data: stats } = useKbStats('24h');
  const { data: topics } = useKbTopics('30d');
  const { data: settings } = useKbSettings();
  // No source filter — the review queue should include gap-RAG drafts alongside
  // the normal ticket-driven ones so reviewers see everything awaiting action.
  const { data: drafts } = useKbDrafts({ status: 'DRAFT', limit: 6 });

  const tiles: Stat[] = [
    {
      label: 'Tickets processed',
      value: stats?.tickets_processed,
      format: 'number',
    },
    {
      label: 'Drafts pending review',
      value: stats?.drafts_pending,
      format: 'number',
      onClick: () => onNavigate('/workspace'),
    },
    {
      label: 'Pushed to ITSM',
      value: stats?.drafts_pushed,
      format: 'number',
    },
    {
      label: 'Topic coverage',
      value: stats?.coverage_percent,
      format: 'percent',
    },
  ];

  const topTopics = (topics ?? []).slice(0, 10).map((t) => ({
    topic: t.topic,
    tickets: t.ticket_count,
  }));

  return (
    <div className="space-y-6">
      {/* Hero */}
      <div className="rounded-xl p-6 text-white"
        style={{ background: 'linear-gradient(135deg, var(--kbgen-brand), var(--kbgen-brand-dark))' }}
      >
        <div className="flex items-start justify-between gap-6 flex-wrap">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-white/70 font-semibold mb-1">
              AI-Powered Knowledge
            </p>
            <h1 className="text-3xl font-bold">Always current. Always accurate.</h1>
            <p className="text-sm text-white/80 mt-1 max-w-xl">
              Resolved tickets become reusable KB articles. kbgen drafts; your team reviews and
              publishes. Indexed into pgvector the moment they ship.
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => onNavigate('/workspace')}>
              Review drafts
            </Button>
            <Button variant="secondary" onClick={() => onNavigate('/search')}>
              Search the KB
            </Button>
          </div>
        </div>
      </div>

      <StatsDisplay stats={tiles} columns={4} />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <div className="p-5 space-y-1">
            <p className="text-xs uppercase tracking-widest text-[var(--kbgen-text-muted)]">
              Indexed chunks
            </p>
            <p className="text-3xl font-bold tabular-nums">{stats?.index_size ?? 0}</p>
            <p className="text-xs text-[var(--kbgen-text-muted)] pt-1">
              {stats?.index_freshness
                ? `latest ${new Date(stats.index_freshness).toLocaleString()}`
                : 'no index activity yet'}
            </p>
          </div>
        </Card>
        <Card>
          <div className="p-5 space-y-1">
            <p className="text-xs uppercase tracking-widest text-[var(--kbgen-text-muted)]">
              Generation model
            </p>
            <p className="text-lg font-semibold">{settings?.openai_model ?? '—'}</p>
            <p className="text-xs text-[var(--kbgen-text-muted)]">
              embedding {settings?.embedding_model ?? '—'}
            </p>
          </div>
        </Card>
        <Card>
          <div className="p-5 space-y-1">
            <p className="text-xs uppercase tracking-widest text-[var(--kbgen-text-muted)]">
              ITSM adapter
            </p>
            <p className="text-lg font-semibold capitalize">{settings?.itsm_adapter ?? '—'}</p>
            <p className="text-xs text-[var(--kbgen-text-muted)]">
              polls every {settings?.poll_interval_s ?? '—'}s
            </p>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[1.3fr_1fr] gap-6">
        <Card>
          <div className="p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-[var(--kbgen-text)]">
                Top topics by ticket volume
              </h3>
              <button
                className="text-xs text-[var(--kbgen-brand)] hover:underline"
                onClick={() => onNavigate('/workspace')}
              >
                Open Workspace →
              </button>
            </div>
            {topTopics.length === 0 ? (
              <p className="text-sm text-[var(--kbgen-text-muted)]">No data yet.</p>
            ) : (
              <BarChart data={topTopics} xKey="topic" yKeys={['tickets']} height={260} />
            )}
            <div className="flex flex-wrap gap-1.5 pt-2 border-t border-[var(--kbgen-border)]">
              {(topics ?? []).slice(0, 18).map((t) => (
                <button
                  key={t.topic}
                  onClick={() =>
                    onNavigate(`/workspace?topic=${encodeURIComponent(t.topic)}`)
                  }
                  className={`text-xs font-medium px-2.5 py-1 rounded-full border transition-colors ${toneForStatus(t.kb_status)}`}
                >
                  {t.topic} · {t.ticket_count}
                </button>
              ))}
            </div>
          </div>
        </Card>

        <Card>
          <div className="p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-[var(--kbgen-text)]">Drafts awaiting review</h3>
              <Badge tone="brand">{stats?.drafts_pending ?? 0}</Badge>
            </div>
            {(drafts?.items ?? []).length === 0 ? (
              <p className="text-sm text-[var(--kbgen-text-muted)]">Nothing to review 🎉</p>
            ) : (
              <div className="space-y-2">
                {(drafts?.items ?? []).map((d) => (
                  <button
                    key={d.id}
                    onClick={() => onNavigate('/workspace')}
                    className="w-full text-left p-3 rounded-lg border border-[var(--kbgen-border)] bg-[var(--kbgen-surface)] hover:border-[var(--kbgen-brand)] transition-colors"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-sm font-semibold text-[var(--kbgen-text)] line-clamp-2">
                        {d.title}
                      </p>
                      <span className="text-xs tabular-nums shrink-0 text-[var(--kbgen-text-secondary)]">
                        {d.score
                          ? `${Math.round(d.score.overall * 100)}%`
                          : d.confidence
                            ? `${Math.round(d.confidence * 100)}%`
                            : '—'}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 mt-1 text-xs text-[var(--kbgen-text-muted)]">
                      {d.category && <Badge>{d.category}</Badge>}
                      {d.source === 'gap-rag' && <Badge tone="warning">SYNTHESISED</Badge>}
                      {d.source_ticket_id && <span>ticket {d.source_ticket_id}</span>}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </Card>
      </div>

      <Card>
        <div className="p-5 opacity-60">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-sm font-bold">Gap Fixing, Health Monitor, Staleness Alerts</h3>
            <Badge tone="warning">Coming in MVP2</Badge>
          </div>
          <p className="text-sm text-[var(--kbgen-text-secondary)]">
            Proactive drafts for uncovered topics, continuous KB health scoring, and drift
            detection for published articles.
          </p>
        </div>
      </Card>
    </div>
  );
}

function toneForStatus(status: string): string {
  if (status === 'covered' || status === 'pushed') {
    return 'bg-emerald-50 text-emerald-700 border-emerald-100 hover:border-emerald-400';
  }
  if (status === 'gap') {
    return 'bg-rose-50 text-rose-700 border-rose-100 hover:border-rose-400';
  }
  return 'bg-[var(--kbgen-brand-light)] text-[var(--kbgen-brand)] border-[var(--kbgen-brand-light)] hover:border-[var(--kbgen-brand)]';
}
