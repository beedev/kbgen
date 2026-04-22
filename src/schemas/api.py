"""API request/response DTOs."""

from datetime import datetime

from pydantic import BaseModel, Field

from src.schemas.article import ArticleRecord


class HealthResponse(BaseModel):
    status: str
    service: str = "kbgen"
    db: str
    itsm: str
    openai: str


class PollCycleResult(BaseModel):
    processed: int = 0
    drafted: int = 0
    covered: int = 0
    skipped: int = 0
    errors: list[str] = Field(default_factory=list)


class ImportResult(BaseModel):
    imported: int
    indexed_chunks: int


class DraftListResponse(BaseModel):
    items: list[ArticleRecord]
    total: int


class DraftUpdate(BaseModel):
    title: str | None = None
    summary: str | None = None
    problem: str | None = None
    steps_md: str | None = None
    tags: list[str] | None = None
    category: str | None = None
    review_notes: str | None = None


class SearchHit(BaseModel):
    """A single search result. `object_kind` discriminates between KB chunks
    and tickets; the rest of the fields light up conditionally based on kind.
    """

    object_kind: str = "kb"                # "kb" | "ticket"
    # KB-chunk fields
    article_id: str | None = None
    chunk_id: str | None = None
    itsm_kb_id: str | None = None
    # Ticket fields
    itsm_ticket_id: str | None = None
    topic: str | None = None
    decision: str | None = None            # DRAFTED | COVERED | SKIPPED
    # Common
    title: str
    category: str | None = None
    preview: str
    relevance: float
    source_ticket_id: str | None = None    # for KB hits, the ticket that spawned the article


class SearchResponse(BaseModel):
    hits: list[SearchHit]
    query: str
    total: int


class StatsResponse(BaseModel):
    window: str
    tickets_processed: int
    drafts_pending: int
    drafts_approved: int
    drafts_pushed: int
    coverage_percent: float
    index_size: int
    index_freshness: datetime | None = None


class TopicRow(BaseModel):
    topic: str
    ticket_count: int
    kb_status: str
    last_activity: datetime | None = None


class SettingsUpdate(BaseModel):
    poll_interval_s: int | None = None
    openai_model: str | None = None
    embedding_model: str | None = None
    chunk_size_tokens: int | None = None
    chunk_overlap: int | None = None
    confidence_threshold: float | None = None
    score_weights: dict | None = None
    itsm_adapter: str | None = None
    itsm_config: dict | None = None
    dedup_threshold: float | None = None
    min_resolution_chars: int | None = None
    thinness_threshold_chars: int | None = None
