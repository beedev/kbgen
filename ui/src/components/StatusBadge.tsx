import React from 'react';
import { Badge } from './Badge';

// Maps kbgen status strings to coloured chips. Unknowns fall back to neutral.
const toneFor = (status: string): 'neutral' | 'brand' | 'success' | 'warning' | 'danger' => {
  const s = (status || '').toLowerCase();
  if (['pushed', 'approved', 'covered', 'published', 'ok', 'green'].includes(s)) return 'success';
  if (['draft', 'edited', 'drafted', 'draft-pending', 'processing'].includes(s)) return 'brand';
  if (['skipped', 'pending', 'waiting', 'imported'].includes(s)) return 'neutral';
  if (['gap', 'low_confidence', 'stale'].includes(s)) return 'warning';
  if (['rejected', 'failed', 'error'].includes(s)) return 'danger';
  return 'neutral';
};

export function StatusBadge({ status }: { status: string }) {
  return <Badge tone={toneFor(status)}>{status}</Badge>;
}
