// KB contract types — one source of truth for the UI. Matches kbgen's
// FastAPI response shapes (src/schemas/api.py + schemas/article.py).

export type KbArticleStatus =
  | 'DRAFT'
  | 'EDITED'
  | 'APPROVED'
  | 'REJECTED'
  | 'PUSHED'
  | 'IMPORTED';

export type KbArticleSource = 'generated' | 'imported_from_itsm';

export type KbDecision = 'DRAFTED' | 'COVERED' | 'SKIPPED';

export type KbTopicStatus = 'covered' | 'draft-pending' | 'pushed' | 'gap';

export interface KbHealthScore {
  accuracy: number;
  recency: number;
  coverage: number;
  overall: number;
}

export interface KbArticle {
  id: string;
  source_ticket_id: string | null;
  itsm_provider: string | null;
  itsm_kb_id: string | null;
  title: string;
  summary: string | null;
  problem: string | null;
  steps_md: string | null;
  tags: string[];
  category: string | null;
  status: KbArticleStatus;
  source: KbArticleSource;
  model: string | null;
  prompt_version: string | null;
  confidence: number | null;
  score: KbHealthScore | null;
  reviewer: string | null;
  review_notes: string | null;
  reviewed_at: string | null;
  pushed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface KbDraftList {
  items: KbArticle[];
  total: number;
}

export interface KbDraftUpdate {
  title?: string;
  summary?: string;
  problem?: string;
  steps_md?: string;
  tags?: string[];
  category?: string;
  review_notes?: string;
}

export interface KbProcessedTicket {
  itsm_ticket_id: string;
  itsm_provider: string;
  title: string;
  topic: string | null;
  decision: KbDecision;
  decision_reason: string | null;
  matched_article_id: string | null;
  matched_score: number | null;
  draft_article_id: string | null;
  resolved_at: string | null;
  observed_at: string;
}

export interface KbTopicRow {
  topic: string;
  ticket_count: number;
  kb_status: KbTopicStatus;
  last_activity: string | null;
}

export interface KbDashboardStats {
  window: string;
  tickets_processed: number;
  drafts_pending: number;
  drafts_approved: number;
  drafts_pushed: number;
  coverage_percent: number;
  index_size: number;
  index_freshness: string | null;
}

export interface KbSearchHit {
  article_id: string;
  chunk_id: string;
  title: string;
  category: string | null;
  preview: string;
  relevance: number;
  source_ticket_id: string | null;
  itsm_kb_id: string | null;
}

export interface KbSearchResponse {
  hits: KbSearchHit[];
  query: string;
  total: number;
}

export interface KbPollResult {
  processed: number;
  drafted: number;
  covered: number;
  skipped: number;
  errors: string[];
}

export interface KbImportResult {
  imported: number;
  indexed_chunks: number;
}

export interface KbPushResult {
  article_id: string;
  itsm_kb_id: string;
  indexed_chunks: number;
  linked_tickets: number;
}

export interface KbSettings {
  poll_interval_s: number;
  openai_model: string;
  embedding_model: string;
  chunk_size_tokens: number;
  chunk_overlap: number;
  confidence_threshold: number;
  score_weights: Record<string, number>;
  itsm_adapter: string;
  itsm_config: Record<string, unknown>;
  dedup_threshold: number;
  min_resolution_chars: number;
  thinness_threshold_chars: number;
  updated_at: string;
}

export type KbSettingsUpdate = Partial<Omit<KbSettings, 'updated_at'>>;

export interface KbConnectionTest {
  adapter: string;
  ok: boolean;
  message: string;
}

export interface KbCoverageTicket {
  itsm_ticket_id: string;
  itsm_provider: string;
  title: string;
  topic: string | null;
  resolved_at: string | null;
  matched_score?: number | null;
  relation: 'primary_source' | 'covered_by';
}

export interface KbArticleCoverage {
  article_id: string;
  title: string;
  status: KbArticleStatus;
  primary_ticket: KbCoverageTicket | null;
  covered_tickets: KbCoverageTicket[];
  total_tickets: number;
}
