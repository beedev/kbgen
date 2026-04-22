import React from 'react';
import { Badge } from './Badge';
import { Card } from './Card';
import type { KbArticleCoverage } from '../types/kb';

// Master-ticket + covered-tickets summary for a KB article.
// Shows the "N tickets → 1 KB" relationship inline with a draft review.
export function CoverageList({ coverage }: { coverage: KbArticleCoverage }) {
  if (!coverage.primary_ticket && coverage.covered_tickets.length === 0) return null;

  return (
    <Card>
      <div className="p-4 space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-xs uppercase tracking-widest text-[var(--kbgen-text-muted)]">
            Tickets this article serves
          </h3>
          <Badge tone="brand">{coverage.total_tickets}</Badge>
        </div>

        <div className="divide-y divide-[var(--kbgen-border-light)]">
          {coverage.primary_ticket && (
            <Row
              label="Master ticket — spawned this draft"
              ticketId={coverage.primary_ticket.itsm_ticket_id}
              provider={coverage.primary_ticket.itsm_provider}
              title={coverage.primary_ticket.title}
              topic={coverage.primary_ticket.topic}
              primary
            />
          )}
          {coverage.covered_tickets.map((t) => (
            <Row
              key={t.itsm_ticket_id}
              ticketId={t.itsm_ticket_id}
              provider={t.itsm_provider}
              title={t.title}
              topic={t.topic}
              matchScore={t.matched_score ?? undefined}
            />
          ))}
        </div>

        {coverage.covered_tickets.length === 0 && coverage.primary_ticket && (
          <p className="text-xs text-[var(--kbgen-text-muted)] pt-1">
            No other tickets yet — this is the first in its topic.
          </p>
        )}
      </div>
    </Card>
  );
}

function Row({
  label,
  ticketId,
  provider,
  title,
  topic,
  matchScore,
  primary = false,
}: {
  label?: string;
  ticketId: string;
  provider: string;
  title: string;
  topic: string | null;
  matchScore?: number;
  primary?: boolean;
}) {
  return (
    <div className="py-2 flex items-start gap-3">
      <div className="shrink-0 mt-0.5">
        {primary ? (
          <span className="text-[var(--kbgen-warning)] text-sm" title="master ticket">
            ★
          </span>
        ) : (
          <span className="text-[var(--kbgen-text-muted)] text-xs">•</span>
        )}
      </div>
      <div className="flex-1 min-w-0">
        {label && (
          <p className="text-[10px] uppercase tracking-widest text-[var(--kbgen-text-muted)] mb-0.5">
            {label}
          </p>
        )}
        <p className="text-sm text-[var(--kbgen-text)] truncate">{title}</p>
        <p className="text-xs text-[var(--kbgen-text-muted)]">
          {provider}:{ticketId}
          {topic ? ` · ${topic}` : ''}
        </p>
      </div>
      {matchScore !== undefined && (
        <div className="text-right shrink-0">
          <span className="text-xs font-semibold tabular-nums text-[var(--kbgen-text-secondary)]">
            {Math.round(matchScore * 100)}%
          </span>
          <p className="text-[10px] text-[var(--kbgen-text-muted)]">similarity</p>
        </div>
      )}
    </div>
  );
}
