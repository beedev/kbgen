// React Query hooks for every KB endpoint. Thin bindings over api().
// Mutation invalidation is intentionally broad — kbgen endpoints are cheap
// and the portal refetches on visibility.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import type {
  KbArticle,
  KbArticleCoverage,
  KbConnectionTest,
  KbDashboardStats,
  KbDraftList,
  KbDraftUpdate,
  KbImportResult,
  KbPollResult,
  KbProcessedTicket,
  KbPushResult,
  KbSearchResponse,
  KbSettings,
  KbSettingsUpdate,
  KbTopicRow,
} from '../types/kb';

// ── Dashboard / read ─────────────────────────────────────────────────────
export function useKbStats(window: string = '24h') {
  return useQuery({
    queryKey: ['kb', 'stats', window],
    queryFn: () => api<KbDashboardStats>('/stats', { params: { window } }),
    staleTime: 30_000,
  });
}

export function useKbTopics(window: string = '30d') {
  return useQuery({
    queryKey: ['kb', 'topics', window],
    queryFn: () => api<KbTopicRow[]>('/topics', { params: { window } }),
    staleTime: 60_000,
  });
}

export function useKbTickets(topic?: string, limit = 200) {
  return useQuery({
    queryKey: ['kb', 'tickets', topic, limit],
    queryFn: () => api<KbProcessedTicket[]>('/tickets', { params: { topic, limit } }),
    staleTime: 30_000,
  });
}

export function useKbSearch(
  query: string,
  category?: string,
  limit = 10,
  kind?: 'kb' | 'ticket',
) {
  return useQuery({
    queryKey: ['kb', 'search', query, category, limit, kind ?? 'all'],
    queryFn: () =>
      api<KbSearchResponse>('/search', {
        params: { q: query, category, kind, limit },
      }),
    enabled: query.trim().length > 1,
  });
}

// ── Drafts ───────────────────────────────────────────────────────────────
export function useKbDrafts(params: {
  status?: string;
  source?: string;
  limit?: number;
  offset?: number;
} = {}) {
  return useQuery({
    queryKey: ['kb', 'drafts', params],
    queryFn: () => api<KbDraftList>('/drafts', { params }),
    staleTime: 10_000,
  });
}

export function useKbDraft(id: string | null) {
  return useQuery({
    queryKey: ['kb', 'draft', id],
    queryFn: () => api<KbArticle>(`/drafts/${id}`),
    enabled: !!id,
  });
}

export function useKbDraftCoverage(id: string | null) {
  return useQuery({
    queryKey: ['kb', 'draft', id, 'coverage'],
    queryFn: () => api<KbArticleCoverage>(`/drafts/${id}/coverage`),
    enabled: !!id,
    staleTime: 30_000,
  });
}

export function useUpdateKbDraft() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: KbDraftUpdate }) =>
      api<KbArticle>(`/drafts/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
    onSuccess: (a) => {
      qc.invalidateQueries({ queryKey: ['kb', 'drafts'] });
      qc.invalidateQueries({ queryKey: ['kb', 'draft', a.id] });
    },
  });
}

export function useApproveKbDraft() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reviewer }: { id: string; reviewer?: string }) =>
      api<KbArticle>(`/drafts/${id}/approve`, { method: 'POST', params: { reviewer } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['kb', 'drafts'] }),
  });
}

export function useRejectKbDraft() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reviewer, reason }: { id: string; reviewer?: string; reason?: string }) =>
      api<KbArticle>(`/drafts/${id}/reject`, { method: 'POST', params: { reviewer, reason } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['kb', 'drafts'] }),
  });
}

export function usePushKbDraft() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reviewer }: { id: string; reviewer?: string }) =>
      api<KbPushResult>(`/drafts/${id}/push`, { method: 'POST', params: { reviewer } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['kb'] }),
  });
}

// ── Pipeline ─────────────────────────────────────────────────────────────
export function useTriggerKbPoll() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api<KbPollResult>('/poll/run', { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['kb'] }),
  });
}

export function useTriggerKbImport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api<KbImportResult>('/import/kb', { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['kb'] }),
  });
}

// ── Gap-RAG: draft a KB for a SKIPPED ticket from neighbour KBs ──────────
export interface KbGapDraftResult {
  draft_id: string;
  neighbours: { article_id: string; title: string; relevance: number }[];
  prompt_version: string;
}

export function useDraftGapFromNeighbours() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (itsm_ticket_id: string) =>
      api<KbGapDraftResult>(`/tickets/${encodeURIComponent(itsm_ticket_id)}/gap-draft`, {
        method: 'POST',
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['kb'] }),
  });
}

// ── Demo seeder ──────────────────────────────────────────────────────────
export interface KbSeedDemoResult {
  theme: string;
  narrative: string;
  seeded: number;
  requested: number;
  ticket_ids: string[];
  errors: string[];
}

export function useSeedDemoTickets() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api<KbSeedDemoResult>('/admin/seed-demo', { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['kb'] }),
  });
}

// ── Settings ─────────────────────────────────────────────────────────────
export function useKbSettings() {
  return useQuery({
    queryKey: ['kb', 'settings'],
    queryFn: () => api<KbSettings>('/settings'),
  });
}

export function useUpdateKbSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: KbSettingsUpdate) =>
      api<{ updated: string[] }>('/settings', { method: 'PATCH', body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['kb', 'settings'] }),
  });
}

export function useTestKbConnection() {
  return useMutation({
    mutationFn: (adapter?: string) =>
      api<KbConnectionTest>('/settings/test-connection', { method: 'POST', params: { adapter } }),
  });
}
