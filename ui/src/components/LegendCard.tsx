import React, { useState } from 'react';
import { Badge } from './Badge';
import { Card } from './Card';
import { itsmKbListUrl } from '../lib/itsm';

// LegendCard — an expandable "what do these mean?" panel that explains the
// Status / Role / health vocabulary the Workspace table uses. Collapsed by
// default so it doesn't crowd the dashboard; expands on click.
export function LegendCard() {
  const [open, setOpen] = useState(false);

  return (
    <Card>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between gap-3 px-5 py-3 text-left"
        aria-expanded={open}
      >
        <div>
          <p className="text-sm font-bold text-[var(--kbgen-text)]">
            What do the Status labels mean?
          </p>
          {!open && (
            <p className="text-xs text-[var(--kbgen-text-muted)]">
              Click to expand — quick reference for reviewers.
            </p>
          )}
        </div>
        <span className="text-[var(--kbgen-text-muted)]">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="px-5 pb-5 space-y-6 border-t border-[var(--kbgen-border)] pt-4">
          {/* ── Status column ──────────────────────────────────────────── */}
          <section className="space-y-2">
            <h4 className="text-xs uppercase tracking-widest text-[var(--kbgen-text-muted)]">
              Status — what this ticket + its article need
            </h4>
            <dl className="space-y-2 text-sm">
              <div className="flex items-start gap-3">
                <Badge tone="brand">NEW · needs review</Badge>
                <span className="text-[var(--kbgen-text-secondary)]">
                  This ticket's resolution was novel; kbgen drafted an article for it.
                  Review it right here in the Workspace — click the row to open the
                  editor, then Approve &amp; Push.
                </span>
              </div>
              <div className="flex items-start gap-3">
                <Badge tone="brand">EDITED · awaiting approval</Badge>
                <span className="text-[var(--kbgen-text-secondary)]">
                  You saved edits to this draft. Next step: Approve &amp; Push.
                </span>
              </div>
              <div className="flex items-start gap-3">
                <Badge tone="success">APPROVED</Badge>
                <span className="text-[var(--kbgen-text-secondary)]">
                  Approved but not yet pushed. (Rare — the UI typically pushes
                  immediately after approval.)
                </span>
              </div>
              <div className="flex items-start gap-3">
                <Badge tone="success">LIVE · KB 22 ↗</Badge>
                <span className="text-[var(--kbgen-text-secondary)]">
                  Published to the ITSM. The KB id is a clickable link that opens the
                  published article in GLPI. You can also{' '}
                  <a
                    href={itsmKbListUrl()}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[var(--kbgen-brand)] hover:underline"
                  >
                    browse all KB articles in the ITSM ↗
                  </a>
                  .
                </span>
              </div>
              <div className="flex items-start gap-3">
                <Badge tone="danger">REJECTED</Badge>
                <span className="text-[var(--kbgen-text-secondary)]">
                  Archived — the reviewer declined to publish.
                </span>
              </div>
              <div className="flex items-start gap-3">
                <Badge tone="success">COVERED → KB 19 ↗</Badge>
                <span className="text-[var(--kbgen-text-secondary)]">
                  This ticket was matched to an <strong>existing live</strong> KB
                  article via semantic similarity. No action needed — the ticket is
                  already answered by that article.
                </span>
              </div>
              <div className="flex items-start gap-3">
                <Badge tone="warning">COVERED · master needs review</Badge>
                <span className="text-[var(--kbgen-text-secondary)]">
                  This ticket was matched to a <strong>pending draft</strong>
                  belonging to another (master) ticket. Action lives on the master.
                  Clicking this row opens the master's review panel directly —
                  pushing the master resolves this ticket and every other sibling in
                  the cluster.
                </span>
              </div>
              <div className="flex items-start gap-3">
                <Badge tone="warning">GAP</Badge>
                <span className="text-[var(--kbgen-text-secondary)]">
                  Resolution notes were too thin to draft honestly — no article was
                  generated. Flagged so it can be re-reviewed or covered by a future
                  MVP2 "Generate for gap" workflow.
                </span>
              </div>
            </dl>
          </section>

          {/* ── Role column ───────────────────────────────────────────── */}
          <section className="space-y-2">
            <h4 className="text-xs uppercase tracking-widest text-[var(--kbgen-text-muted)]">
              Role — how this ticket relates to its KB article
            </h4>
            <dl className="space-y-2 text-sm">
              <div className="flex items-start gap-3">
                <Badge tone="success">★ Master · serves N tickets</Badge>
                <span className="text-[var(--kbgen-text-secondary)]">
                  A DRAFTED ticket whose article also covers <em>N−1</em> later
                  similar tickets. <strong>N</strong> counts the master itself plus
                  each covered sibling — total tickets one article answers.
                  Approving a master with high N has disproportionate impact.
                </span>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-xs tabular-nums text-[var(--kbgen-text-muted)] whitespace-nowrap shrink-0">
                  → glpi:NNN
                </span>
                <span className="text-[var(--kbgen-text-secondary)]">
                  Shown on COVERED rows. Points at the master ticket — the one whose
                  resolution notes originally spawned the article that covers this
                  ticket.
                </span>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-xs text-[var(--kbgen-text-muted)] whitespace-nowrap shrink-0">
                  Solo draft
                </span>
                <span className="text-[var(--kbgen-text-secondary)]">
                  A DRAFTED ticket whose article has no covered siblings yet — the
                  first of its kind. Future similar tickets may attach to it as
                  coverage.
                </span>
              </div>
            </dl>
          </section>

          {/* ── Health score ───────────────────────────────────────────── */}
          <section className="space-y-2">
            <h4 className="text-xs uppercase tracking-widest text-[var(--kbgen-text-muted)]">
              Health score (inside the review panel)
            </h4>
            <dl className="space-y-2 text-sm text-[var(--kbgen-text-secondary)]">
              <div>
                <strong className="text-[var(--kbgen-text)]">Model Confidence</strong>{' '}
                — the LLM's self-rated certainty when it drafted the article.
              </div>
              <div>
                <strong className="text-[var(--kbgen-text)]">Accuracy</strong> —
                model confidence dampened when the source ticket's resolution notes
                are shorter than the thinness threshold (default 120 chars, tunable
                in Admin → System Status).
              </div>
              <div>
                <strong className="text-[var(--kbgen-text)]">Recency</strong> — how
                fresh the knowledge is. 100% = resolved today; decays linearly over
                365 days.
              </div>
              <div>
                <strong className="text-[var(--kbgen-text)]">Coverage novelty</strong>{' '}
                — how different this draft is from indexed KB. <em>Low</em> novelty
                (e.g. 18%) means the draft duplicates something we already have.
              </div>
              <div>
                <strong className="text-[var(--kbgen-text)]">Overall Health</strong>{' '}
                — weighted sum (default weights{' '}
                <code>accuracy × 0.5 + recency × 0.2 + coverage × 0.3</code>, tunable
                in Admin → System Status).
              </div>
            </dl>
          </section>

          {/* ── Reviewer guidance ──────────────────────────────────────── */}
          <section className="rounded-md bg-[var(--kbgen-brand-light)] border border-[var(--kbgen-brand)]/20 p-4 space-y-2">
            <p className="text-xs uppercase tracking-widest text-[var(--kbgen-brand)] font-bold">
              Rule of thumb — drive the decision from Overall Health
            </p>
            <ul className="text-sm text-[var(--kbgen-text-secondary)] space-y-1">
              <li>
                <strong className="text-[var(--kbgen-success)]">≥ 80%</strong> — safe
                to approve &amp; push
              </li>
              <li>
                <strong className="text-[var(--kbgen-brand)]">60–80%</strong> — read
                carefully, usually approvable with minor edits
              </li>
              <li>
                <strong className="text-[var(--kbgen-warning)]">40–60%</strong> —
                scrutinize; one of the sub-scores is flagging something (thin
                resolution, near-duplicate)
              </li>
              <li>
                <strong className="text-[var(--kbgen-danger)]">&lt; 40%</strong> —
                consider rejecting
              </li>
              <li>
                <strong>★ Master</strong> rows — prioritize these when scores are
                high; one approval resolves many tickets.
              </li>
            </ul>
          </section>
        </div>
      )}
    </Card>
  );
}
