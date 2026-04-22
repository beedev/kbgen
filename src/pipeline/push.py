"""Push an approved draft to the ITSM, then re-index the published article."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.indexing.indexer import index_article
from src.itsm import get_adapter
from src.storage import articles as articles_dal
from src.storage.models import PushLog

log = logging.getLogger(__name__)


async def push_draft(db: AsyncSession, draft_id: UUID, *, reviewer: str | None = None) -> dict:
    article = await articles_dal.get(db, draft_id)
    if not article:
        raise ValueError(f"draft {draft_id} not found")
    if article.status not in ("DRAFT", "EDITED", "APPROVED"):
        raise ValueError(f"draft {draft_id} has status {article.status}; cannot push")

    adapter = get_adapter()
    body = article.steps_md or ""
    tags = list(article.tags or [])

    try:
        itsm_kb_id = await adapter.create_kb_draft(
            title=article.title,
            body=body,
            category=article.category,
            tags=tags,
        )
    except Exception as exc:
        db.add(
            PushLog(
                article_id=article.id,
                itsm_provider=adapter.name,
                request_payload={"title": article.title, "body": body, "tags": tags},
                response_payload=None,
                success=False,
                error=f"{exc.__class__.__name__}: {exc}",
            )
        )
        await db.commit()
        raise

    db.add(
        PushLog(
            article_id=article.id,
            itsm_provider=adapter.name,
            request_payload={"title": article.title, "body": body, "tags": tags},
            response_payload={"itsm_kb_id": itsm_kb_id},
            success=True,
            error=None,
        )
    )
    article.itsm_kb_id = itsm_kb_id
    article.itsm_provider = adapter.name
    article.status = "PUSHED"
    article.pushed_at = datetime.now(timezone.utc)
    if reviewer:
        article.reviewer = reviewer
        article.reviewed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(article)

    # Re-index so the freshly pushed article appears in /search + assistant immediately.
    n_chunks = await index_article(
        db, article_id=article.id, title=article.title, body=article.steps_md or ""
    )
    return {
        "article_id": str(article.id),
        "itsm_kb_id": itsm_kb_id,
        "indexed_chunks": n_chunks,
    }
