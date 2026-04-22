"""Article schemas — the LLM output contract and persistence DTOs."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class ArticleStatus(str, Enum):
    DRAFT = "DRAFT"
    EDITED = "EDITED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PUSHED = "PUSHED"
    IMPORTED = "IMPORTED"


class ArticleSource(str, Enum):
    GENERATED = "generated"
    IMPORTED_FROM_ITSM = "imported_from_itsm"
    GAP_RAG = "gap-rag"


class ArticleDraft(BaseModel):
    """LLM structured-output target. Fields here map 1:1 to the JSON schema sent to OpenAI."""

    title: str = Field(..., description="Short, specific, search-friendly title")
    summary: str = Field(..., description="1–2 sentence abstract")
    problem: str = Field(..., description="Clear statement of the problem this article solves")
    steps_md: str = Field(..., description="Resolution steps in Markdown (numbered or bulleted)")
    tags: list[str] = Field(default_factory=list, description="Keyword tags for retrieval")
    category: str | None = Field(default=None, description="Topical category, matches ITSM taxonomy when possible")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model self-rated confidence 0..1")


class HealthScore(BaseModel):
    accuracy: float = Field(..., ge=0.0, le=1.0)
    recency: float = Field(..., ge=0.0, le=1.0)
    coverage: float = Field(..., ge=0.0, le=1.0)
    overall: float = Field(..., ge=0.0, le=1.0)


class ArticleRecord(BaseModel):
    """Full persisted record returned from API."""

    id: UUID
    source_ticket_id: str | None = None
    itsm_provider: str | None = None
    itsm_kb_id: str | None = None
    title: str
    summary: str | None = None
    problem: str | None = None
    steps_md: str | None = None
    tags: list[str] = Field(default_factory=list)
    category: str | None = None
    status: ArticleStatus
    source: ArticleSource
    model: str | None = None
    prompt_version: str | None = None
    confidence: float | None = None
    score: HealthScore | None = None
    reviewer: str | None = None
    review_notes: str | None = None
    reviewed_at: datetime | None = None
    pushed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
