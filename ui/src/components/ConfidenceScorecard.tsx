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
    </div>
  );
}
