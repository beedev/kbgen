"""DAL for kb.processed_ticket."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.models import ProcessedTicket


async def get(db: AsyncSession, itsm_ticket_id: str) -> ProcessedTicket | None:
    return (
        await db.execute(
            select(ProcessedTicket).where(ProcessedTicket.itsm_ticket_id == itsm_ticket_id)
        )
    ).scalar_one_or_none()


async def exists(db: AsyncSession, itsm_ticket_id: str) -> bool:
    return (await get(db, itsm_ticket_id)) is not None


async def record(
    db: AsyncSession,
    *,
    itsm_ticket_id: str,
    itsm_provider: str,
    title: str,
    description: str | None,
    resolution: str | None,
    topic: str | None,
    resolved_at: datetime | None,
    decision: str,
    decision_reason: str,
    matched_article_id: UUID | None = None,
    matched_score: float | None = None,
    draft_article_id: UUID | None = None,
    embedding: list[float] | None = None,
) -> ProcessedTicket:
    """Upsert — previously SKIPPED tickets retry cleanly on the next cycle.

    `embedding` is optional: when omitted, an existing embedding on the row is
    preserved (supports partial updates from gap-draft etc. without re-embedding);
    when set, it overwrites. New rows without an embedding leave the column NULL
    and `/admin/reindex-tickets` can backfill them.
    """
    row = await get(db, itsm_ticket_id)
    if row is None:
        row = ProcessedTicket(itsm_ticket_id=itsm_ticket_id)
        db.add(row)
    row.itsm_provider = itsm_provider
    row.title = title
    row.description = description
    row.resolution = resolution
    row.topic = topic
    row.resolved_at = resolved_at
    row.observed_at = datetime.now(timezone.utc)
    row.decision = decision
    row.decision_reason = decision_reason
    row.matched_article_id = matched_article_id
    row.matched_score = matched_score
    row.draft_article_id = draft_article_id
    if embedding is not None:
        row.embedding = embedding
    await db.commit()
    return row
