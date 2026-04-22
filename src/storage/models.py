"""ORM models for the `kb` schema.

One schema per service — keeps kbgen's tables clearly separable from the
conversational-assistant's `public` tables in the shared agentic_commerce DB.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from src.config import get_settings

_settings = get_settings()
EMBEDDING_DIM = _settings.embedding_dim


class Base(DeclarativeBase):
    metadata_schema = _settings.db_schema


# SQLAlchemy 2.0 doesn't have metadata_schema; apply via table_args below instead.
_SCHEMA = _settings.db_schema


class Article(Base):
    __tablename__ = "article"
    __table_args__ = {"schema": _SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_ticket_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    itsm_provider: Mapped[str | None] = mapped_column(String, nullable=True)
    itsm_kb_id: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)

    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    problem: Mapped[str | None] = mapped_column(Text)
    steps_md: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    category: Mapped[str | None] = mapped_column(String, index=True)

    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String, nullable=False)

    model: Mapped[str | None] = mapped_column(String)
    prompt_version: Mapped[str | None] = mapped_column(String)
    confidence: Mapped[float | None] = mapped_column(Numeric)
    score_accuracy: Mapped[float | None] = mapped_column(Numeric)
    score_recency: Mapped[float | None] = mapped_column(Numeric)
    score_coverage: Mapped[float | None] = mapped_column(Numeric)
    score_overall: Mapped[float | None] = mapped_column(Numeric)

    reviewer: Mapped[str | None] = mapped_column(String)
    review_notes: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pushed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    chunks: Mapped[list[Chunk]] = relationship(
        "Chunk", back_populates="article", cascade="all, delete-orphan", lazy="selectin"
    )


class Chunk(Base):
    __tablename__ = "chunk"
    __table_args__ = (
        UniqueConstraint("article_id", "chunk_index", name="uq_chunk_article_idx"),
        {"schema": _SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{_SCHEMA}.article.id", ondelete="CASCADE"), index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))
    content_hash: Mapped[str] = mapped_column(String, index=True)
    indexed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    article: Mapped[Article] = relationship("Article", back_populates="chunks")


class ProcessedTicket(Base):
    __tablename__ = "processed_ticket"
    __table_args__ = {"schema": _SCHEMA}

    itsm_ticket_id: Mapped[str] = mapped_column(String, primary_key=True)
    itsm_provider: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    resolution: Mapped[str | None] = mapped_column(Text)
    topic: Mapped[str | None] = mapped_column(String, index=True)

    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    decision: Mapped[str] = mapped_column(String, nullable=False, index=True)
    decision_reason: Mapped[str | None] = mapped_column(Text)
    matched_article_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{_SCHEMA}.article.id"), nullable=True
    )
    matched_score: Mapped[float | None] = mapped_column(Numeric)
    draft_article_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{_SCHEMA}.article.id"), nullable=True
    )


class PushLog(Base):
    __tablename__ = "push_log"
    __table_args__ = {"schema": _SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{_SCHEMA}.article.id"), index=True
    )
    itsm_provider: Mapped[str] = mapped_column(String, nullable=False)
    request_payload: Mapped[dict | None] = mapped_column(JSONB)
    response_payload: Mapped[dict | None] = mapped_column(JSONB)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class TopicSnapshot(Base):
    __tablename__ = "topic_snapshot"
    __table_args__ = {"schema": _SCHEMA}

    topic: Mapped[str] = mapped_column(String, primary_key=True)
    window: Mapped[str] = mapped_column(String, primary_key=True)
    ticket_count: Mapped[int] = mapped_column(Integer, default=0)
    kb_status: Mapped[str] = mapped_column(String, nullable=False)
    last_activity: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class KbSettings(Base):
    __tablename__ = "settings"
    __table_args__ = {"schema": _SCHEMA}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    poll_interval_s: Mapped[int] = mapped_column(Integer, default=60)
    openai_model: Mapped[str] = mapped_column(String, default="gpt-4.1")
    embedding_model: Mapped[str] = mapped_column(String, default="text-embedding-3-small")
    chunk_size_tokens: Mapped[int] = mapped_column(Integer, default=500)
    chunk_overlap: Mapped[int] = mapped_column(Integer, default=60)
    confidence_threshold: Mapped[float] = mapped_column(Numeric, default=0.6)
    score_weights: Mapped[dict] = mapped_column(
        JSONB, default=lambda: {"accuracy": 0.5, "recency": 0.2, "coverage": 0.3}
    )
    itsm_adapter: Mapped[str] = mapped_column(String, default="mock")
    itsm_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    dedup_threshold: Mapped[float] = mapped_column(Numeric, default=0.82)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
