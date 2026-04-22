import React from 'react';
import type { KbHealthScore } from '../types/kb';

function bar(val: number) {
  const pct = Math.max(0, Math.min(100, Math.round(val * 100)));
  const color =
    pct >= 80
      ? 'var(--kbgen-success)'
      : pct >= 60
        ? 'var(--kbgen-brand)'
        : pct >= 40
          ? 'var(--kbgen-warning)'
          : 'var(--kbgen-danger)';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 rounded bg-[var(--kbgen-border-light)] overflow-hidden">
        <div style={{ width: `${pct}%`, background: color }} className="h-full transition-all" />
      </div>
      <span className="text-xs tabular-nums font-semibold w-10 text-right">{pct}%</span>
    </div>
  );
}

export function ConfidenceScorecard({
  score,
  confidence,
}: {
  score: KbHealthScore | null | undefined;
  confidence: number | null | undefined;
}) {
  if (!score) {
    return (
      <div className="rounded-lg border border-[var(--kbgen-border)] p-4 text-sm text-[var(--kbgen-text-muted)]">
        Health score not available.
      </div>
    );
  }
  return (
    <div className="rounded-lg border border-[var(--kbgen-border)] p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-[var(--kbgen-text-muted)]">
            Overall health
          </p>
          <p className="text-2xl font-bold tabular-nums text-[var(--kbgen-text)]">
            {Math.round(score.overall * 100)}%
          </p>
        </div>
        {confidence != null && (
          <div className="text-right">
            <p className="text-xs uppercase tracking-widest text-[var(--kbgen-text-muted)]">
              Model confidence
            </p>
            <p className="text-lg font-semibold tabular-nums text-[var(--kbgen-text-secondary)]">
              {Math.round(confidence * 100)}%
            </p>
          </div>
        )}
      </div>
      <div className="space-y-2">
        <div>
          <p className="text-xs text-[var(--kbgen-text-secondary)] mb-1">Accuracy</p>
          {bar(score.accuracy)}
        </div>
        <div>
          <p className="text-xs text-[var(--kbgen-text-secondary)] mb-1">Recency</p>
          {bar(score.recency)}
        </div>
        <div>
          <p className="text-xs text-[var(--kbgen-text-secondary)] mb-1">Coverage novelty</p>
          {bar(score.coverage)}
        </div>
      </div>

      {/* Inline legend — always visible so reviewers don't have to hunt for
          definitions. Keeps the panel self-explanatory. */}
      <div className="border-t border-[var(--kbgen-border)] pt-3 space-y-2 text-xs text-[var(--kbgen-text-secondary)]">
        <p className="text-[10px] uppercase tracking-widest text-[var(--kbgen-text-muted)] font-bold">
          What these mean
        </p>
        <dl className="space-y-1.5 leading-snug">
          <div>
            <dt className="font-semibold text-[var(--kbgen-text)] inline">Model Confidence</dt>
            <span> — the LLM's self-rated certainty when it drafted this article.</span>
          </div>
          <div>
            <dt className="font-semibold text-[var(--kbgen-text)] inline">Accuracy</dt>
            <span> — model confidence, <em>dampened</em> when the source ticket's resolution notes are thin (&lt; 120 chars).</span>
          </div>
          <div>
            <dt className="font-semibold text-[var(--kbgen-text)] inline">Recency</dt>
            <span> — freshness of the knowledge. 100% = resolved today; decays linearly over 365 days.</span>
          </div>
          <div>
            <dt className="font-semibold text-[var(--kbgen-text)] inline">Coverage novelty</dt>
            <span> — how different this draft is from indexed KB. <strong>Low = near-duplicate</strong> — consider merging instead of publishing.</span>
          </div>
          <div>
            <dt className="font-semibold text-[var(--kbgen-text)] inline">Overall Health</dt>
            <span> — weighted sum: <code>accuracy × 0.5 + recency × 0.2 + coverage × 0.3</code>. Weights tunable in Admin → System Status.</span>
          </div>
        </dl>
        <div className="pt-2 text-[var(--kbgen-text-muted)] border-t border-[var(--kbgen-border-light)] space-y-1">
          <p>
            <strong>Rule of thumb — read the Overall Health number:</strong>
          </p>
          <ul className="space-y-0.5 pl-3">
            <li>
              <strong className="text-[var(--kbgen-success)]">≥ 80%</strong> — safe to approve &amp; push
            </li>
            <li>
              <strong className="text-[var(--kbgen-brand)]">60–80%</strong> — read carefully, usually approvable with minor edits
            </li>
            <li>
              <strong className="text-[var(--kbgen-warning)]">40–60%</strong> — scrutinize; one of the sub-scores is flagging something
            </li>
            <li>
              <strong className="text-[var(--kbgen-danger)]">&lt; 40%</strong> — consider rejecting
            </li>
          </ul>
          <p className="pt-1">
            The sub-scores (Accuracy / Recency / Coverage) tell you <em>why</em> Overall
            landed where it did, not whether to publish on their own.
          </p>
        </div>
      </div>
    </div>
  );
}
