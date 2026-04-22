"""/topics — computes live topic status from processed_ticket + article joins."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.db import get_session
from src.storage.models import Article, ProcessedTicket

router = APIRouter()

_WINDOW_DAYS = {"24h": 1, "7d": 7, "30d": 30, "all": 10_000}


@router.get("/topics")
async def list_topics(
    window: str = "30d",
    db: AsyncSession = Depends(get_session),
) -> list[dict]:
    days = _WINDOW_DAYS.get(window, 30)
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Count tickets per topic in the window + latest activity.
    ticket_stmt = (
        select(
            ProcessedTicket.topic,
            func.count().label("cnt"),
            func.max(ProcessedTicket.observed_at).label("last_activity"),
        )
        .where(ProcessedTicket.topic.is_not(None))
        .where(ProcessedTicket.observed_at >= since)
        .group_by(ProcessedTicket.topic)
    )
    ticket_rows = (await db.execute(ticket_stmt)).all()

    # For each topic, find its KB status by joining with kb.article.
    article_stmt = select(Article.category, Article.status).where(Article.category.is_not(None))
    article_rows = (await db.execute(article_stmt)).all()

    # Aggregate article statuses per topic.
    topic_has_published: dict[str, bool] = {}
    topic_has_draft: dict[str, bool] = {}
    for cat, status in article_rows:
        if status in ("PUSHED", "IMPORTED", "APPROVED"):
            topic_has_published[cat] = True
        elif status in ("DRAFT", "EDITED"):
            topic_has_draft[cat] = True

    out: list[dict] = []
    for topic, cnt, last in ticket_rows:
        if topic_has_published.get(topic):
            status = "covered"
        elif topic_has_draft.get(topic):
            status = "draft-pending"
        else:
            status = "gap"
        out.append(
            {
                "topic": topic,
                "ticket_count": cnt,
                "kb_status": status,
                "last_activity": last,
            }
        )
    out.sort(key=lambda r: r["ticket_count"], reverse=True)
    return out
