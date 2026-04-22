"""/tickets — processed-ticket inspector."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.db import get_session
from src.storage.models import ProcessedTicket

router = APIRouter()


@router.get("/tickets")
async def list_tickets(
    topic: str | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_session),
) -> list[dict]:
    stmt = select(ProcessedTicket)
    if topic:
        stmt = stmt.where(ProcessedTicket.topic == topic)
    stmt = stmt.order_by(ProcessedTicket.observed_at.desc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return [
        {
            "itsm_ticket_id": r.itsm_ticket_id,
            "itsm_provider": r.itsm_provider,
            "title": r.title,
            "topic": r.topic,
            "decision": r.decision,
            "decision_reason": r.decision_reason,
            "matched_article_id": str(r.matched_article_id) if r.matched_article_id else None,
            "matched_score": float(r.matched_score) if r.matched_score is not None else None,
            "draft_article_id": str(r.draft_article_id) if r.draft_article_id else None,
            "resolved_at": r.resolved_at,
            "observed_at": r.observed_at,
        }
        for r in rows
    ]
