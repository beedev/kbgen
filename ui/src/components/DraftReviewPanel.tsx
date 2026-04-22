import React, { useEffect, useState } from 'react';
import { Badge } from './Badge';
import { Button } from './Button';
import { Card } from './Card';
import { ConfidenceScorecard } from './ConfidenceScorecard';
import { CoverageList } from './CoverageList';
import { KbLink } from './KbLink';
import { MarkdownEditor } from './MarkdownEditor';
import { useToast } from './Toaster';
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
  const toast = useToast();

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
  const disabledReason =
    draft.status === 'PUSHED'
      ? 'Draft is already published to the ITSM — no further action from here.'
      : draft.status === 'REJECTED'
        ? 'Draft was rejected and archived — no further action from here.'
        : '';

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
        {draft.source === 'gap-rag' && (
          <span title="Synthesised from neighbour KBs — verify steps before pushing">
            <Badge tone="warning">SYNTHESISED</Badge>
          </span>
        )}
        {draft.source_ticket_id && (
          <span className="text-xs text-[var(--kbgen-text-muted)]">
            master ticket {draft.itsm_provider}:{draft.source_ticket_id}
          </span>
        )}
        {coverage && coverage.total_tickets > 1 && (
          <Badge tone="success">serves {coverage.total_tickets} tickets</Badge>
        )}
        {draft.itsm_kb_id && (
          <span className="text-xs text-[var(--kbgen-text-muted)]">
            · <KbLink kbId={draft.itsm_kb_id} />
          </span>
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

      {/* Banner surfaces the terminal status so reviewers aren't confused by
          greyed-out action buttons below. */}
      {!canEdit && (
        <div
          className={`rounded-lg border p-3 text-sm ${
            draft.status === 'PUSHED'
              ? 'bg-emerald-50 border-[var(--kbgen-success)] text-emerald-800'
              : 'bg-rose-50 border-[var(--kbgen-danger)] text-rose-800'
          }`}
        >
          {draft.status === 'PUSHED' ? (
            <>
              <strong>Already published.</strong> This article is live in the ITSM
              {draft.itsm_kb_id ? (
                <>
                  {' '}as <KbLink kbId={draft.itsm_kb_id} className="underline" />
                </>
              ) : null}
              {draft.pushed_at && (
                <>
                  {' '}on{' '}
                  <time>{new Date(draft.pushed_at).toLocaleString()}</time>
                </>
              )}
              . The actions below are disabled because a published article
              can&rsquo;t be re-pushed from here — edit the ITSM record directly, or
              reject this draft to archive it.
            </>
          ) : (
            <>
              <strong>Rejected.</strong> This draft was rejected
              {draft.reviewed_at && (
                <>
                  {' '}on{' '}
                  <time>{new Date(draft.reviewed_at).toLocaleString()}</time>
                </>
              )}{' '}
              and is archived. Actions are disabled.
            </>
          )}
        </div>
      )}

      <div className="flex items-center justify-end gap-2 pt-2 border-t border-[var(--kbgen-border)]">
        <Button
          variant="ghost"
          onClick={async () => {
            try {
              await reject.mutateAsync({ id: draft.id });
              toast.push('info', `Rejected "${draft.title}".`);
              onAction?.('rejected');
            } catch (err) {
              toast.push('error', `Reject failed: ${String(err)}`);
            }
          }}
          disabled={!canEdit || reject.isPending}
          title={!canEdit ? disabledReason : 'Discard this draft'}
        >
          Reject
        </Button>
        <Button
          variant="secondary"
          onClick={async () => {
            try {
              await onSave();
              toast.push('success', `Saved edits to "${title}".`);
            } catch (err) {
              toast.push('error', `Save failed: ${String(err)}`);
            }
          }}
          disabled={!canEdit || !dirty || update.isPending}
          title={
            !canEdit
              ? disabledReason
              : !dirty
                ? 'No unsaved edits'
                : 'Save your edits to the draft'
          }
        >
          {update.isPending ? 'Saving…' : dirty ? 'Save edits' : 'Saved'}
        </Button>
        <Button
          onClick={async () => {
            try {
              await approve.mutateAsync({ id: draft.id });
              const result = await push.mutateAsync({ id: draft.id });
              const linked = result.linked_tickets ?? 0;
              const linkedNote =
                linked > 0
                  ? ` Linked to ${linked} ticket${linked === 1 ? '' : 's'}.`
                  : '';
              toast.push(
                'success',
                `Pushed to ITSM as KB ${result.itsm_kb_id}. Indexed ${result.indexed_chunks} chunks.${linkedNote}`,
                6000,
              );
              onAction?.('pushed');
            } catch (err) {
              toast.push('error', `Push failed: ${String(err)}`);
            }
          }}
          disabled={!canEdit || push.isPending}
          title={
            !canEdit ? disabledReason : 'Approve this draft and push it to the ITSM as a KB article'
          }
        >
          {push.isPending ? 'Pushing…' : 'Approve & Push to ITSM'}
        </Button>
      </div>
    </div>
  );
}
