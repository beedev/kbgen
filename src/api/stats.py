"""/stats — dashboard read model. Zeroes in P0; populated in later phases."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.api import StatsResponse
from src.storage.db import get_session
from src.storage.models import Article, Chunk, ProcessedTicket

router = APIRouter()


@router.get("/stats", response_model=StatsResponse)
async def stats(window: str = "24h", db: AsyncSession = Depends(get_session)) -> StatsResponse:
    tickets_processed = (await db.execute(select(func.count()).select_from(ProcessedTicket))).scalar() or 0

    drafts_pending = (
        await db.execute(
            select(func.count()).select_from(Article).where(Article.status.in_(["DRAFT", "EDITED"]))
        )
    ).scalar() or 0
    drafts_approved = (
        await db.execute(
            select(func.count()).select_from(Article).where(Article.status == "APPROVED")
        )
    ).scalar() or 0
    drafts_pushed = (
        await db.execute(select(func.count()).select_from(Article).where(Article.status == "PUSHED"))
    ).scalar() or 0

    index_size = (await db.execute(select(func.count()).select_from(Chunk))).scalar() or 0
    index_freshness = (await db.execute(select(func.max(Chunk.indexed_at)))).scalar()

    # Coverage % = distinct topics with any article ÷ distinct topics seen in tickets.
    topics_seen = (
        await db.execute(select(func.count(func.distinct(ProcessedTicket.topic))))
    ).scalar() or 0
    topics_covered = (
        await db.execute(select(func.count(func.distinct(Article.category))).where(Article.status == "PUSHED"))
    ).scalar() or 0
    coverage = (topics_covered / topics_seen * 100.0) if topics_seen else 0.0

    return StatsResponse(
        window=window,
        tickets_processed=tickets_processed,
        drafts_pending=drafts_pending,
        drafts_approved=drafts_approved,
        drafts_pushed=drafts_pushed,
        coverage_percent=round(coverage, 1),
        index_size=index_size,
        index_freshness=index_freshness,
    )
