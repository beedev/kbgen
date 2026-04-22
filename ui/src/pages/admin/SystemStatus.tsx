import React, { useState } from 'react';
import { Badge } from '../../components/Badge';
import { Button } from '../../components/Button';
import { Card } from '../../components/Card';
import {
  useKbSettings,
  useKbStats,
  useTestKbConnection,
  useTriggerKbImport,
  useTriggerKbPoll,
  useUpdateKbSettings,
} from '../../hooks/useKb';

export function SystemStatus() {
  const { data: stats } = useKbStats('24h');
  const { data: settings, refetch } = useKbSettings();
  const test = useTestKbConnection();
  const poll = useTriggerKbPoll();
  const importKb = useTriggerKbImport();
  const update = useUpdateKbSettings();
  const [itsmStatus, setItsmStatus] = useState<string | null>(null);
  const [pollInterval, setPollInterval] = useState<number | undefined>();
  const [dedupThreshold, setDedupThreshold] = useState<number | undefined>();
  const [model, setModel] = useState<string | undefined>();
  const [minResolutionChars, setMinResolutionChars] = useState<number | undefined>();
  const [thinnessThresholdChars, setThinnessThresholdChars] = useState<number | undefined>();

  React.useEffect(() => {
    if (settings) {
      setPollInterval(settings.poll_interval_s);
      setDedupThreshold(settings.dedup_threshold);
      setModel(settings.openai_model);
      setMinResolutionChars(settings.min_resolution_chars);
      setThinnessThresholdChars(settings.thinness_threshold_chars);
    }
  }, [settings?.updated_at]);

  const onTest = async () => {
    const r = await test.mutateAsync(undefined);
    setItsmStatus(`${r.adapter}: ${r.ok ? '✓ reachable' : '✗ unreachable'} — ${r.message}`);
  };

  const onSave = async () => {
    await update.mutateAsync({
      poll_interval_s: pollInterval,
      dedup_threshold: dedupThreshold,
      openai_model: model,
      min_resolution_chars: minResolutionChars,
      thinness_threshold_chars: thinnessThresholdChars,
    });
    await refetch();
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--kbgen-text)]">System Status</h1>
        <p className="text-sm text-[var(--kbgen-text-muted)]">
          Real-time health of the kbgen pipeline — ITSM, index, LLM.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <div className="p-4 space-y-1">
            <p className="text-xs uppercase tracking-widest text-[var(--kbgen-text-muted)]">
              ITSM
            </p>
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold capitalize">{settings?.itsm_adapter ?? '—'}</span>
              <Badge tone="success">active</Badge>
            </div>
            <div className="pt-2 flex items-center gap-2">
              <Button variant="secondary" onClick={onTest} disabled={test.isPending}>
                {test.isPending ? 'Testing…' : 'Test connection'}
              </Button>
            </div>
            {itsmStatus && (
              <p className="text-xs text-[var(--kbgen-text-secondary)] mt-2">{itsmStatus}</p>
            )}
          </div>
        </Card>

        <Card>
          <div className="p-4 space-y-1">
            <p className="text-xs uppercase tracking-widest text-[var(--kbgen-text-muted)]">
              Vector index
            </p>
            <p className="text-3xl font-bold tabular-nums">{stats?.index_size ?? 0}</p>
            <p className="text-xs text-[var(--kbgen-text-muted)]">chunks embedded</p>
            <p className="text-xs text-[var(--kbgen-text-muted)] pt-2">
              {stats?.index_freshness
                ? `Latest: ${new Date(stats.index_freshness).toLocaleString()}`
                : 'No index activity yet'}
            </p>
          </div>
        </Card>

        <Card>
          <div className="p-4 space-y-1">
            <p className="text-xs uppercase tracking-widest text-[var(--kbgen-text-muted)]">
              LLM
            </p>
            <p className="text-lg font-bold">{settings?.openai_model ?? '—'}</p>
            <p className="text-xs text-[var(--kbgen-text-muted)]">
              embedding: {settings?.embedding_model ?? '—'}
            </p>
          </div>
        </Card>
      </div>

      <Card>
        <div className="p-5 space-y-3">
          <h3 className="text-sm font-bold text-[var(--kbgen-text)]">Pipeline actions</h3>
          <p className="text-xs text-[var(--kbgen-text-muted)]">
            Manual triggers. The scheduler runs every{' '}
            <span className="font-mono">{settings?.poll_interval_s ?? 60}s</span> automatically.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              onClick={() => importKb.mutate()}
              disabled={importKb.isPending}
            >
              {importKb.isPending ? 'Importing…' : 'Import existing KB from ITSM'}
            </Button>
            <Button onClick={() => poll.mutate()} disabled={poll.isPending}>
              {poll.isPending ? 'Polling…' : 'Run poll cycle now'}
            </Button>
          </div>
        </div>
      </Card>

      <Card>
        <div className="p-5 space-y-4">
          <h3 className="text-sm font-bold text-[var(--kbgen-text)]">Tuning</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="text-xs font-semibold text-[var(--kbgen-text-secondary)]">
                Poll interval (seconds)
              </label>
              <input
                type="number"
                min={30}
                max={600}
                className="mt-1 w-full rounded-md border border-[var(--kbgen-border)] p-2 text-sm"
                value={pollInterval ?? ''}
                onChange={(e) => setPollInterval(Number(e.target.value))}
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-[var(--kbgen-text-secondary)]">
                Dedup threshold (0–1)
              </label>
              <input
                type="number"
                step="0.01"
                min={0}
                max={1}
                className="mt-1 w-full rounded-md border border-[var(--kbgen-border)] p-2 text-sm"
                value={dedupThreshold ?? ''}
                onChange={(e) => setDedupThreshold(Number(e.target.value))}
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-[var(--kbgen-text-secondary)]">
                OpenAI model
              </label>
              <input
                className="mt-1 w-full rounded-md border border-[var(--kbgen-border)] p-2 text-sm"
                value={model ?? ''}
                onChange={(e) => setModel(e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-[var(--kbgen-text-secondary)]">
                Min resolution chars
              </label>
              <input
                type="number"
                min={0}
                max={500}
                className="mt-1 w-full rounded-md border border-[var(--kbgen-border)] p-2 text-sm"
                value={minResolutionChars ?? ''}
                onChange={(e) => setMinResolutionChars(Number(e.target.value))}
              />
              <p className="text-[10px] text-[var(--kbgen-text-muted)] mt-1 leading-snug">
                Below this length, resolution text is considered absent → ticket marked
                SKIPPED (gap). Lower to skip fewer tickets; raise to be stricter.
              </p>
            </div>
            <div>
              <label className="text-xs font-semibold text-[var(--kbgen-text-secondary)]">
                Thinness threshold (chars)
              </label>
              <input
                type="number"
                min={0}
                max={2000}
                className="mt-1 w-full rounded-md border border-[var(--kbgen-border)] p-2 text-sm"
                value={thinnessThresholdChars ?? ''}
                onChange={(e) => setThinnessThresholdChars(Number(e.target.value))}
              />
              <p className="text-[10px] text-[var(--kbgen-text-muted)] mt-1 leading-snug">
                Accuracy dampening band. Resolutions below this length take up to 25%
                Accuracy penalty (linear from 0 → threshold). Set to 0 to disable
                dampening entirely.
              </p>
            </div>
          </div>
          <div>
            <Button onClick={onSave} disabled={update.isPending}>
              {update.isPending ? 'Saving…' : 'Save tuning'}
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
