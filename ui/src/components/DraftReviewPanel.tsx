import React, { useEffect, useState } from 'react';
import { Badge } from './Badge';
import { Button } from './Button';
import { Card } from './Card';
import { ConfidenceScorecard } from './ConfidenceScorecard';
import { CoverageList } from './CoverageList';
import { MarkdownEditor } from './MarkdownEditor';
import {
  useApproveKbDraft,
  useKbDraft,
  useKbDraftCoverage,
  usePushKbDraft,
  useRejectKbDraft,
  useUpdateKbDraft,
} from '../hooks/useKb';

export function DraftReviewPanel({
  draftId,
  onAction,
}: {
  draftId: string;
  onAction?: (action: 'edited' | 'approved' | 'rejected' | 'pushed') => void;
}) {
  const { data: draft, isLoading } = useKbDraft(draftId);
  const { data: coverage } = useKbDraftCoverage(draftId);
  const update = useUpdateKbDraft();
  const approve = useApproveKbDraft();
  const reject = useRejectKbDraft();
  const push = usePushKbDraft();

  const [title, setTitle] = useState('');
  const [summary, setSummary] = useState('');
  const [stepsMd, setStepsMd] = useState('');
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (draft) {
      setTitle(draft.title);
      setSummary(draft.summary ?? '');
      setStepsMd(draft.steps_md ?? '');
      setDirty(false);
    }
  }, [draft?.id]);

  if (isLoading || !draft) {
    return <p className="text-sm text-[var(--kbgen-text-muted)]">Loading draft…</p>;
  }

  const canEdit = draft.status !== 'PUSHED' && draft.status !== 'REJECTED';

  const onSave = async () => {
    await update.mutateAsync({
      id: draft.id,
      body: { title, summary, steps_md: stepsMd },
    });
    setDirty(false);
    onAction?.('edited');
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 flex-wrap">
        <Badge tone="brand">{draft.status}</Badge>
        {draft.source_ticket_id && (
          <span className="text-xs text-[var(--kbgen-text-muted)]">
            master ticket {draft.itsm_provider}:{draft.source_ticket_id}
          </span>
        )}
        {coverage && coverage.total_tickets > 1 && (
          <Badge tone="success">serves {coverage.total_tickets} tickets</Badge>
        )}
        {draft.itsm_kb_id && (
          <span className="text-xs text-[var(--kbgen-text-muted)]">· KB {draft.itsm_kb_id}</span>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1.1fr_1fr] gap-4">
        {/* Source ticket */}
        <Card>
          <div className="p-4 space-y-3">
            <h3 className="text-xs uppercase tracking-widest text-[var(--kbgen-text-muted)]">
              Source ticket
            </h3>
            <div className="text-sm">
              <p className="font-semibold text-[var(--kbgen-text)]">{draft.title}</p>
              {draft.problem && (
                <p className="mt-2 text-[var(--kbgen-text-secondary)] whitespace-pre-wrap">
                  {draft.problem}
                </p>
              )}
            </div>
            <ConfidenceScorecard score={draft.score} confidence={draft.confidence} />
          </div>
        </Card>

        {/* Draft editor */}
        <Card>
          <div className="p-4 space-y-3">
            <h3 className="text-xs uppercase tracking-widest text-[var(--kbgen-text-muted)]">
              Generated article
            </h3>
            <div>
              <label className="text-xs font-semibold text-[var(--kbgen-text-secondary)]">
                Title
              </label>
              <input
                className="mt-1 w-full rounded-md border border-[var(--kbgen-border)] p-2 text-sm"
                value={title}
                disabled={!canEdit}
                onChange={(e) => {
                  setTitle(e.target.value);
                  setDirty(true);
                }}
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-[var(--kbgen-text-secondary)]">
                Summary
              </label>
              <textarea
                className="mt-1 w-full rounded-md border border-[var(--kbgen-border)] p-2 text-sm"
                rows={2}
                value={summary}
                disabled={!canEdit}
                onChange={(e) => {
                  setSummary(e.target.value);
                  setDirty(true);
                }}
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-[var(--kbgen-text-secondary)]">
                Resolution steps (Markdown)
              </label>
              <MarkdownEditor
                value={stepsMd}
                readOnly={!canEdit}
                onChange={(v) => {
                  setStepsMd(v);
                  setDirty(true);
                }}
              />
            </div>
          </div>
        </Card>
      </div>

      {coverage && <CoverageList coverage={coverage} />}

      <div className="flex items-center justify-end gap-2 pt-2 border-t border-[var(--kbgen-border)]">
        <Button
          variant="ghost"
          onClick={async () => {
            await reject.mutateAsync({ id: draft.id });
            onAction?.('rejected');
          }}
          disabled={!canEdit || reject.isPending}
        >
          Reject
        </Button>
        <Button
          variant="secondary"
          onClick={onSave}
          disabled={!canEdit || !dirty || update.isPending}
        >
          {update.isPending ? 'Saving…' : dirty ? 'Save edits' : 'Saved'}
        </Button>
        <Button
          onClick={async () => {
            await approve.mutateAsync({ id: draft.id });
            await push.mutateAsync({ id: draft.id });
            onAction?.('pushed');
          }}
          disabled={!canEdit || push.isPending}
        >
          {push.isPending ? 'Pushing…' : 'Approve & Push to ITSM'}
        </Button>
      </div>
    </div>
  );
}
