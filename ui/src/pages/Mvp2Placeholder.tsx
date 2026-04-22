import React from 'react';
import { Badge } from '../components/Badge';
import { Card } from '../components/Card';

const META: Record<string, { title: string; body: string }> = {
  '/mvp2/gap': {
    title: 'Gap Fixing',
    body: 'Proactively draft KB articles for topics that have tickets but no existing article. Cluster unresolved questions and generate authoritative answers for SME review.',
  },
  '/mvp2/health': {
    title: 'KB Health Monitor',
    body: 'Continuous health scoring across the entire published KB — accuracy, freshness, coverage — not just newly generated drafts.',
  },
  '/mvp2/staleness': {
    title: 'Staleness Alerts',
    body: 'Detect drift: KB articles whose answers no longer match the latest resolutions, policies, or product versions. Flag candidates for review.',
  },
};

export function Mvp2Placeholder({ path }: { path: string }) {
  const meta = META[path] ?? { title: 'MVP2', body: 'This feature ships in the next release.' };
  return (
    <div className="max-w-3xl mx-auto py-12">
      <Card>
        <div className="p-8 space-y-4">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-[var(--kbgen-text)]">{meta.title}</h1>
            <Badge tone="warning">Coming in MVP2</Badge>
          </div>
          <p className="text-[var(--kbgen-text-secondary)] leading-relaxed">{meta.body}</p>
          <div className="pt-4 border-t border-[var(--kbgen-border)]">
            <p className="text-xs uppercase tracking-widest text-[var(--kbgen-text-muted)] mb-2">
              Status
            </p>
            <p className="text-sm text-[var(--kbgen-text-secondary)]">
              Not yet implemented. MVP1 ships Article Generation, Smart Search, and the HITL
              review loop. This page is a placeholder so the roadmap is visible.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}
